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

"""MS Teams integration API tests.

Covers the new ms_teams credential type:
  TC_002 — create (HTTP 200)
  TC_003/TC_004 — update, parametrized over project- and user-scope (HTTP 200)
  TC_005 — singleton constraint (HTTP 409)
  TC_006 — cross-project assistant ownership (HTTP 400)
"""

from typing import Optional

import pytest
from hamcrest import assert_that, contains_string, equal_to, is_not, none
from requests import HTTPError

from codemie_sdk.models.integration import (
    CredentialTypes,
    CredentialValues,
    Integration,
    IntegrationType,
)
from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.utils.base_utils import get_random_name


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ms_teams_request(
    project_name: str,
    alias: str,
    assistant_ids: list,
    setting_type: IntegrationType = IntegrationType.PROJECT,
    setting_id: Optional[str] = None,
) -> Integration:
    """Build an Integration model for ms_teams using the SDK enum.

    CredentialTypes.MS_TEAMS = 'MSTeams' is the correct wire value accepted
    by the API.  The normal Integration() constructor is used so Pydantic
    validates and serialises the enum correctly.
    """
    return Integration(
        id=setting_id,
        project_name=project_name,
        alias=alias,
        credential_type=CredentialTypes.MS_TEAMS,
        credential_values=[CredentialValues(key="assistant_ids", value=assistant_ids)],
        setting_type=setting_type,
    )


# ---------------------------------------------------------------------------
# Module-scoped pre-clean: remove any stale MSTeams integration from the
# test project so TC-002, TC-003/TC-004, and TC-005 start from a clean slate.
# Each test that creates an integration already deletes it on exit;
# this fixture only handles leftover rows from a previously interrupted run.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module", autouse=True)
def cleanup_stale_ms_teams_integration(integration_utils):
    """Delete any pre-existing MSTeams project/user integrations before this module runs.

    Needed because the singleton constraint (one ms_teams row per project) causes
    TC-002, TC-003/TC-004, and TC-005 to fail with HTTP 409 if a previous test run
    was interrupted before its per-test cleanup could execute.  Runs once per module,
    before any test in the file.  Covers both scopes since TC-003/TC-004 now creates
    ms_teams integrations for both IntegrationType.PROJECT and IntegrationType.USER.
    """
    integration_utils.delete_integrations_by_type(
        IntegrationType.PROJECT, CredentialTypes.MS_TEAMS
    )
    integration_utils.delete_integrations_by_type(
        IntegrationType.USER, CredentialTypes.MS_TEAMS
    )


# ---------------------------------------------------------------------------
# TC_002 — create ms_teams integration returns HTTP 200
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.project_integration
@pytest.mark.api
def test_create_ms_teams_integration_succeeds(assistant, integration_utils):
    """POST /v1/settings/project with credential_type='MSTeams' returns HTTP 200."""
    assistant_obj = assistant()
    alias = get_random_name()
    request = _ms_teams_request(
        project_name=PROJECT,
        alias=alias,
        assistant_ids=[assistant_obj.id],
    )

    response = integration_utils.send_create_integration_request(request)

    assert_that(
        response["message"],
        equal_to("Specified credentials saved"),
        "Create ms_teams integration: response message mismatch.",
    )

    created = integration_utils.get_integration_by_alias(alias, IntegrationType.PROJECT)
    assert_that(
        created.id,
        is_not(none()),
        "Create ms_teams integration: setting_id must be present after creation.",
    )

    # Cleanup
    integration_utils.delete_integration(created)


# ---------------------------------------------------------------------------
# TC_003/TC_004 — update ms_teams integration returns HTTP 200, for both
# project and user scope (user scope used to be rejected with HTTP 400; it is
# now supported, so the former "returns_400" case is folded into this one as
# the IntegrationType.USER parametrization).
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.project_integration
@pytest.mark.api
@pytest.mark.parametrize(
    "setting_type",
    [IntegrationType.PROJECT, IntegrationType.USER],
    ids=[IntegrationType.PROJECT, IntegrationType.USER],
)
def test_update_ms_teams_integration_succeeds(
    default_llm, assistant_factory, integration_utils, setting_type
):
    """PUT /v1/settings/{project|user}/{setting_id} updates assistant_ids and returns HTTP 200.

    Parametrized over IntegrationType.PROJECT and IntegrationType.USER — ms_teams
    now supports creating and updating the integration at either scope.
    """
    assistant_1 = assistant_factory.create(llm_model_type=default_llm.base_name)
    assistant_2 = assistant_factory.create(llm_model_type=default_llm.base_name)
    alias = get_random_name()

    # Create ms_teams integration with assistant_1
    create_request = _ms_teams_request(
        project_name=PROJECT,
        alias=alias,
        assistant_ids=[assistant_1.id],
        setting_type=setting_type,
    )
    integration_utils.send_create_integration_request(create_request)
    created = integration_utils.get_integration_by_alias(alias, setting_type)

    try:
        # Update with assistant_2
        update_request = _ms_teams_request(
            project_name=PROJECT,
            alias=alias,
            assistant_ids=[assistant_2.id],
            setting_type=setting_type,
            setting_id=created.id,
        )
        update_response = integration_utils.update_integration(update_request)

        assert_that(
            update_response["message"],
            equal_to("Specified credentials updated"),
            "Update ms_teams integration: response message mismatch.",
        )

        # Verify updated assistant_ids are reflected via subsequent GET
        updated = integration_utils.get_integration_by_alias(alias, setting_type)
        cred_values_dict = {cv.key: cv.value for cv in updated.credential_values}
        ids_raw = cred_values_dict.get("assistant_ids")
        assert_that(
            ids_raw,
            is_not(none()),
            "assistant_ids must be present in the updated integration.",
        )
        # Robust string-based check — value may be a list or a serialised JSON string
        assert_that(
            str(ids_raw),
            contains_string(assistant_2.id),
            f"Updated assistant_ids must contain assistant {assistant_2.id}.",
        )
    finally:
        integration_utils.delete_integration(created)


# ---------------------------------------------------------------------------
# TC_005 — duplicate ms_teams integration for same project returns HTTP 409
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.project_integration
@pytest.mark.api
def test_create_ms_teams_integration_duplicate_returns_409(
    assistant, integration_utils
):
    """Second ms_teams creation for same project returns HTTP 409.

    check_ms_teams_singleton enforces one ms_teams row per project.
    """
    assistant_obj = assistant()
    alias_1 = get_random_name()
    first_request = _ms_teams_request(
        project_name=PROJECT,
        alias=alias_1,
        assistant_ids=[assistant_obj.id],
    )
    integration_utils.send_create_integration_request(first_request)
    first_created = integration_utils.get_integration_by_alias(
        alias_1, IntegrationType.PROJECT
    )

    try:
        alias_2 = get_random_name()
        second_request = _ms_teams_request(
            project_name=PROJECT,
            alias=alias_2,
            assistant_ids=[assistant_obj.id],
        )

        with pytest.raises(HTTPError) as exc_info:
            integration_utils.send_create_integration_request(second_request)

        assert_that(
            exc_info.value.response.status_code,
            equal_to(409),
            "Second ms_teams integration for the same project must return HTTP 409.",
        )
    finally:
        integration_utils.delete_integration(first_created)


# ---------------------------------------------------------------------------
# TC_006 — ms_teams integration with cross-project assistant returns HTTP 400
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.project_integration
@pytest.mark.api
def test_create_ms_teams_integration_cross_project_assistant_returns_400(
    default_llm, assistant_factory, project, integration_utils
):
    """POST /v1/settings/project with an assistant from a different project returns HTTP 400.

    validate_ms_teams_request.belongs_to_project rejects assistant_ids that do not
    belong to the target project_name.
    """
    # Create an isolated second project
    project_b = project()

    # Create an assistant scoped to project B
    assistant_in_b = assistant_factory.create(
        llm_model_type=default_llm.base_name,
        project_name=project_b.name,
    )

    # Attempt to create ms_teams for PROJECT using an assistant from project B
    alias = get_random_name()
    request = _ms_teams_request(
        project_name=PROJECT,
        alias=alias,
        assistant_ids=[assistant_in_b.id],
    )

    with pytest.raises(HTTPError) as exc_info:
        integration_utils.send_create_integration_request(request)

    assert_that(
        exc_info.value.response.status_code,
        equal_to(400),
        "ms_teams with a cross-project assistant_id must return HTTP 400.",
    )
