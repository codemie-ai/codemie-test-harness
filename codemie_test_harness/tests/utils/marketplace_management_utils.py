# Copyright 2026 EPAM Systems, Inc. (“EPAM”)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Helpers for the marketplace admin approval gate.

Calls go through the SDK: ``client.marketplace_management`` for the review queue,
``client.assistants`` for the assistant and its publish route. A refused call raises
``requests.HTTPError``; its ``response`` carries the exact status code and error body.
The exceptions are the audit config route (gate thresholds) and bulk-unpublish, which the
SDK does not cover; the first goes through the repo's ``RequestHandler``, the second
returns the raw response.
"""

from dataclasses import dataclass
from typing import Callable, List, Optional

import requests
from codemie_sdk import CodeMieClient
from codemie_sdk.models.assistant import Assistant, AssistantUpdateRequest
from codemie_sdk.models.marketplace_management import (
    MarketplaceAssistantsResponse,
    MarketplaceForcePublishResponse,
    MarketplaceOverview,
    MarketplacePendingResponse,
    MarketplaceReviewActionResponse,
    MarketplaceReviewDetail,
)
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests import API_DOMAIN, VERIFY_SSL
from codemie_test_harness.tests.test_data.marketplace_approval_gate_test_data import (
    PENDING_REVIEW,
    VALID_REASON,
    MarketplaceSubmission,
)
from codemie_test_harness.tests.utils.assistant_utils import AssistantUtils
from codemie_test_harness.tests.utils.base_utils import BaseUtils, poll_until
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.http_utils import RequestHandler

_BASE_PATH = "/v1/marketplace-management/entities"
PAGE_SIZE = 100
CONFIG_PATH = "/v1/marketplace-management/entities/assistants/config"
CORE_GATES_COMPONENT_ID = "marketplaceCoreGates"
# Fields of the gates section of the audit config. The PUT body is not partial: it
# must hold all of them, and any other key is rejected with 422.
GATES_FIELDS = (
    "name_min",
    "name_max",
    "description_min",
    "system_prompt_min",
    "substance_prompt_alt_min",
    "banned_generic_names",
    "credential_patterns",
)


class MarketplaceManagementUtils(BaseUtils):
    """Marketplace-management endpoints, the assistant publish route and the review state of an assistant."""

    def __init__(self, client: CodeMieClient):
        super().__init__(client)
        self._service = client.marketplace_management
        self._api = RequestHandler(API_DOMAIN, client.token, VERIFY_SSL)

    # ---- gate thresholds ---------------------------------------------------
    # The SDK has no method for the audit config route, so these two calls use the
    # repo's request helper directly.

    def get_gates_config(self) -> dict:
        """The gates section of the audit config, as the backend reports it."""
        response = self._api.get(CONFIG_PATH)
        assert_that(
            response.status_code,
            equal_to(200),
            f"GET config failed: {response.text}",
        )
        return response.json()["gates"]

    def ensure_core_gates(
        self,
        description_min: int,
        system_prompt_min: int,
        substance_prompt_alt_min: int,
    ) -> dict:
        """Make the three core gate thresholds hold the given values; returns the gates.

        The whole gates object read from the GET goes back in the PUT with only the
        three thresholds changed. The PUT is idempotent, so parallel workers that race
        here all store the same values.
        """
        wanted = {
            "description_min": description_min,
            "system_prompt_min": system_prompt_min,
            "substance_prompt_alt_min": substance_prompt_alt_min,
        }

        def current_values(gates: dict) -> dict:
            return {field: gates[field] for field in wanted}

        gates = self.get_gates_config()
        if current_values(gates) != wanted:
            body = {"gates": {**{name: gates[name] for name in GATES_FIELDS}, **wanted}}
            response = self._api.put(CONFIG_PATH, json_data=body)
            assert_that(
                response.status_code,
                equal_to(200),
                f"PUT config failed: {response.text}",
            )
            gates = poll_until(
                self.get_gates_config,
                lambda read: current_values(read) == wanted,
                timeout=30,
                interval=2,
            )
        assert_that(
            current_values(gates),
            equal_to(wanted),
            f"the core gates could not be set on this stand; the tests need them at {wanted}",
        )
        return gates

    def get_core_gates_setting(self) -> dict:
        """The Core Gates setting as the admin console lists it: ``overridden`` and ``value``."""
        for declaration in self.client.customer_config.list_declarations():
            if declaration["component_id"] == CORE_GATES_COMPONENT_ID:
                return {
                    "overridden": bool(declaration["overridden"]),
                    "value": declaration["value"],
                }
        raise AssertionError(
            f"the setting {CORE_GATES_COMPONENT_ID!r} is not declared on this stand"
        )

    def restore_core_gates_setting(self, original: dict) -> None:
        """Put the Core Gates setting back as ``get_core_gates_setting`` recorded it.

        An override that did not exist is removed again ("Reset to default"); one that
        did exist is saved with its old value.
        """
        if original["overridden"]:
            self.client.customer_config.save_setting(
                CORE_GATES_COMPONENT_ID, original["value"]
            )
        else:
            self.client.customer_config.reset_setting(CORE_GATES_COMPONENT_ID)

    # ---- reads -------------------------------------------------------------

    def get_overview(self) -> MarketplaceOverview:
        return self._service.get_overview()

    def get_pending(
        self, page: int = 1, page_size: int = PAGE_SIZE, **filters
    ) -> MarketplacePendingResponse:
        return self._service.list_pending(page=page, page_size=page_size, **filters)

    def get_marketplace_assistants(
        self, status: Optional[str] = None, page: int = 1, page_size: int = PAGE_SIZE
    ) -> MarketplaceAssistantsResponse:
        return self._service.list_marketplace_assistants(
            status=status, page=page, page_size=page_size
        )

    def get_detail(self, assistant_id: str) -> MarketplaceReviewDetail:
        return self._service.get_detail(assistant_id)

    def get_assistant(self, assistant_id: str) -> Assistant:
        """The assistant including marketplace_status, is_verified and marketplace_decision_reason."""
        return self.client.assistants.get(assistant_id)

    def _collect_pages(self, fetch_page: Callable[[int], object]) -> list:
        """Every item over all pages. The stop rule uses the SQL ``total``: a gate-result
        filter narrows ``items`` of a page, never ``total``, so an empty page proves nothing."""
        items: list = []
        page = 1
        while True:
            result = fetch_page(page)
            items.extend(result.items)
            if page * PAGE_SIZE >= result.total:
                return items
            page += 1

    def list_all_pending(self, **filters) -> list:
        return self._collect_pages(lambda page: self.get_pending(page=page, **filters))

    def list_all_marketplace_assistants(self, status: Optional[str] = None) -> list:
        return self._collect_pages(
            lambda page: self.get_marketplace_assistants(status=status, page=page)
        )

    # ---- decisions ---------------------------------------------------------

    def approve(
        self,
        assistant_id: str,
        expected_version: Optional[int] = None,
        idempotency_key: Optional[str] = None,
    ) -> MarketplaceReviewActionResponse:
        return self._service.approve(
            assistant_id,
            expected_version=expected_version,
            idempotency_key=idempotency_key,
        )

    def reject(
        self, assistant_id: str, reason: str, expected_version: Optional[int] = None
    ) -> MarketplaceReviewActionResponse:
        return self._service.reject(
            assistant_id, reason, expected_version=expected_version
        )

    def force_publish(
        self,
        assistant_id: str,
        override_notice: str,
        expected_version: Optional[int] = None,
    ) -> MarketplaceForcePublishResponse:
        return self._service.force_publish(
            assistant_id, override_notice, expected_version=expected_version
        )

    def withdraw(self, assistant_id: str) -> MarketplaceReviewActionResponse:
        return self._service.withdraw(assistant_id)

    def bulk_unpublish(
        self, entity_ids: list[str], kind: str = "assistants"
    ) -> requests.Response:
        """POST ``/entities/{kind}/bulk-unpublish`` and return the raw response.

        The response is returned without raising so a test can assert both the
        200 body (``unpublished``, ``failed``) and rejection statuses (422).

        Args:
            entity_ids: Ids to unpublish (the API accepts 1-500).
            kind: Entity kind path segment; only ``assistants`` is implemented.
        """
        api_domain = CredentialsManager.get_parameter("CODEMIE_API_DOMAIN").rstrip("/")
        verify_ssl = (
            CredentialsManager.get_parameter("VERIFY_SSL", "false").lower() == "true"
        )
        return requests.post(
            f"{api_domain}{_BASE_PATH}/{kind}/bulk-unpublish",
            json={"entity_ids": entity_ids},
            headers={"Authorization": f"Bearer {self.client.token}"},
            verify=verify_ssl,
        )

    # ---- publish route of the assistant ------------------------------------

    def publish(
        self,
        assistant_id: str,
        categories: List[str],
        ignore_recommendations: bool = True,
        force_publish: bool = False,
        override_notice: Optional[str] = None,
    ) -> dict:
        return self.client.assistants.publish(
            assistant_id,
            categories=categories,
            ignore_recommendations=ignore_recommendations,
            force_publish=force_publish,
            override_notice=override_notice,
        )

    # ---- dispatch by endpoint name -----------------------------------------

    def call_endpoint(
        self,
        endpoint: str,
        assistant_id: str,
        expected_version: int,
        categories: List[str],
    ) -> object:
        """Call one management endpoint (or the force-publish flag of the publish route) by name."""
        calls = {
            "overview": self.get_overview,
            "pending": self.get_pending,
            "marketplace-assistants": self.get_marketplace_assistants,
            "detail": lambda: self.get_detail(assistant_id),
            "approve": lambda: self.approve(assistant_id, expected_version),
            "reject": lambda: self.reject(assistant_id, VALID_REASON, expected_version),
            "force-publish": lambda: self.force_publish(
                assistant_id, VALID_REASON, expected_version
            ),
            "publish with force_publish=true": lambda: self.publish(
                assistant_id,
                categories,
                force_publish=True,
                override_notice=VALID_REASON,
            ),
        }
        return calls[endpoint]()


@dataclass
class SubmittedAssistant:
    """An assistant created by the submitter, with the content it was created from."""

    id: str
    name: str
    description: str
    system_prompt: str
    categories: List[str]
    project: str
    llm_model_type: str
    decision_reason: Optional[str] = None


def personal_project_of(user) -> Optional[str]:
    """Personal project of a user as `client.users.about_me()` describes it.

    A personal project is named after its owner, so the login name or the e-mail
    (whichever the user is assigned to) wins; otherwise the user's default project.
    None when neither exists.
    """
    for name in (user.username, user.email):
        if name and name in (user.applications or []):
            return name
    return next((p.name for p in user.projects or [] if p.is_default), None)


class MarketplaceSubmitter:
    """A plain (non-admin) user who owns assistants and submits them to the marketplace."""

    def __init__(
        self,
        email: str,
        password: str,
        client: CodeMieClient,
        llm_model: str,
        project: Optional[str] = None,
    ):
        """`email` is the login name; `project` is where the assistants are created and
        defaults to it, because a user made by the harness owns a personal project of that name."""
        self.email = email
        self.password = password
        self.client = client
        self.llm_model_type = llm_model
        self.project = project or email
        me = client.users.about_me()
        self.user_id = me.user_id
        self.display_name = me.name or me.username
        self.assistant_utils = AssistantUtils(client)
        self.management = MarketplaceManagementUtils(client)

    def create_assistant(self, submission: MarketplaceSubmission) -> SubmittedAssistant:
        created = self.assistant_utils.create_assistant(
            llm_model_type=self.llm_model_type,
            system_prompt=submission.system_prompt,
            assistant_name=submission.name,
            description=submission.description,
            categories=submission.categories,
            conversation_starters=submission.conversation_starters,
            project_name=self.project,
        )
        return SubmittedAssistant(
            id=created.id,
            name=submission.name,
            description=submission.description,
            system_prompt=submission.system_prompt,
            categories=submission.categories,
            project=self.project,
            llm_model_type=self.llm_model_type,
        )

    def submit_for_review(self, assistant: SubmittedAssistant) -> None:
        """Publish through the normal route; with the gate armed that queues the assistant."""
        response = self.management.publish(assistant.id, assistant.categories)
        assert_that(
            response["marketplace_status"],
            equal_to(PENDING_REVIEW),
            "a publish by a plain user must queue the assistant; the approval gate "
            "feature flags are off on this stand",
        )

    def edit_description(self, assistant: SubmittedAssistant, description: str) -> None:
        """Change only the description of an owned assistant (everything else is passed through)."""
        self.assistant_utils.update_assistant(
            assistant.id,
            AssistantUpdateRequest(
                name=assistant.name,
                description=description,
                system_prompt=assistant.system_prompt,
                project=assistant.project,
                llm_model_type=assistant.llm_model_type,
                categories=assistant.categories,
            ),
        )
        assistant.description = description


def poll_marketplace_listing(
    assistant_utils: AssistantUtils,
    assistant_id: str,
    listed: bool,
    timeout: float = 30.0,
) -> List[str]:
    """Ids in the marketplace scope, re-read until the assistant is (not) listed or the timeout ends.

    Indexing and de-indexing run in the background after a decision, so the listing can
    lag it. The last read is returned either way; the caller asserts on it.
    """
    return poll_until(
        lambda: [
            assistant.id
            for assistant in assistant_utils.get_all_assistants(scope="marketplace")
        ],
        lambda ids: (assistant_id in ids) == listed,
        timeout=timeout,
        interval=2,
    )
