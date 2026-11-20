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

"""Create hosted applications and their versions through the SDK, wait for validation, and
remove everything afterwards."""

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from codemie_sdk import CodeMieClient
from codemie_sdk.models.hosted_application import (
    HostedApplication,
    HostedApplicationVersion,
    HostedApplicationVersionStart,
)
from hamcrest import assert_that, empty, equal_to, is_not
from requests import HTTPError

from codemie_test_harness.tests.test_data.hosted_application_test_data import (
    MAX_APPLICATIONS,
    MAX_OPEN_UPLOADS,
    HostedArtifact,
    html_artifact,
)
from codemie_test_harness.tests.utils.base_utils import (
    BaseUtils,
    get_random_name,
    poll_until,
)

logger = logging.getLogger(__name__)

VERSION_SETTLED_STATES = (
    "accepted",
    "awaiting_configuration",
    "rejected",
    "failed",
    "canceled",
)
VERSION_WAIT_SECONDS = 240
PURGE_WAIT_SECONDS = 180
BULK_WORKERS = 8
CATALOG_PAGE_SIZE = 100


def error_code(error: HTTPError) -> Optional[str]:
    """The platform's error code carried by a failed hosted-application call."""
    try:
        return error.response.json()["error"]["details"]["code"]
    except (AttributeError, KeyError, TypeError, ValueError):
        return None


def error_status(error: HTTPError) -> int:
    return error.response.status_code


def error_message(error: HTTPError) -> str:
    """The readable message of a failed hosted-application call."""
    try:
        return error.response.json()["error"]["message"]
    except (AttributeError, KeyError, TypeError, ValueError):
        return ""


class HostedApplicationUtils(BaseUtils):
    """Hosted-application calls of one user, and the applications that user created."""

    def __init__(self, client: CodeMieClient):
        super().__init__(client)
        self.service = client.hosted_applications
        self._app_ids: list[str] = []
        self._category_id: Optional[str] = None

    def create_app(
        self,
        project: str,
        shared: bool = False,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> HostedApplication:
        app = self.service.create_application(
            name or get_random_name(),
            description or "Application created by an automated test",
            project,
            shared=shared,
        )
        self._app_ids.append(app.id)
        return app

    def get_app(self, app_id: str) -> HostedApplication:
        return self.service.get_application(app_id)

    def start_upload(
        self, app_id: str, artifact: HostedArtifact, routing_mode: str = "static"
    ) -> HostedApplicationVersionStart:
        """Start a version and leave its upload open."""
        return self.service.start_version(
            app_id,
            artifact.filename,
            artifact.kind,
            len(artifact.content),
            self.get_app(app_id).etag,
            routing_mode=routing_mode,
        )

    def upload_version(
        self,
        app_id: str,
        artifact: HostedArtifact,
        routing_mode: str = "static",
        wait: bool = True,
    ) -> HostedApplicationVersion:
        """Upload an artifact as a new version; with ``wait`` return once validation has settled."""
        start = self.start_upload(app_id, artifact, routing_mode)
        receipt = self.service.upload_artifact(
            app_id,
            start.version_id,
            artifact.content,
            start.upload_etag,
            start.generation,
        )
        assert_that(
            receipt.sha256,
            equal_to(artifact.sha256),
            "the platform stored the bytes that were sent",
        )
        self.service.complete_version(
            app_id,
            start.version_id,
            start.upload_id,
            receipt.sha256,
            start.generation,
            receipt.version_etag,
        )
        if not wait:
            return self.service.get_version(app_id, start.version_id)
        return self.wait_for_version(app_id, start.version_id)

    def wait_for_version(
        self,
        app_id: str,
        version_id: str,
        states: tuple[str, ...] = VERSION_SETTLED_STATES,
        timeout: float = VERSION_WAIT_SECONDS,
    ) -> HostedApplicationVersion:
        """Poll until the version reaches one of ``states``; return its last reading."""
        return poll_until(
            lambda: self.service.get_version(app_id, version_id),
            lambda version: version.validation_state in states,
            timeout=timeout,
            interval=2.0,
        )

    def upload_accepted_version(
        self, app_id: str, artifact: HostedArtifact, routing_mode: str = "static"
    ) -> HostedApplicationVersion:
        version = self.upload_version(app_id, artifact, routing_mode)
        assert_that(
            version.validation_state,
            equal_to("accepted"),
            f"the version of '{artifact.filename}' is accepted",
        )
        return version

    def activate(self, app_id: str, version_id: str) -> HostedApplication:
        return self.service.activate(app_id, version_id, self.get_app(app_id).etag)

    def go_live(
        self, app_id: str, artifact: HostedArtifact, routing_mode: str = "static"
    ) -> HostedApplicationVersion:
        """Upload an artifact and make it the live version; return the version."""
        version = self.upload_accepted_version(app_id, artifact, routing_mode)
        live = self.activate(app_id, version.id)
        assert_that(live.active_version_id, equal_to(version.id), "the version is live")
        return version

    def existing_category_id(self) -> str:
        """The id of a category the platform already has; the tests never delete it."""
        if self._category_id is None:
            categories = self.client.categories.get_categories()
            assert_that(categories, is_not(empty()), "the platform has a category")
            self._category_id = categories[0].id
        return self._category_id

    def publish(self, app_id: str) -> HostedApplication:
        """Publish an application to the marketplace; publishing needs a category, so it sends one."""
        return self.service.marketplace_publish(
            app_id,
            self.get_app(app_id).etag,
            categories=[self.existing_category_id()],
        )

    def unpublish(self, app_id: str) -> HostedApplication:
        return self.service.marketplace_unpublish(app_id, self.get_app(app_id).etag)

    def delete_app(self, app_id: str):
        return self.service.delete_application(app_id, self.get_app(app_id).etag)

    def wait_until_purged(self, app_id: str, timeout: float = PURGE_WAIT_SECONDS):
        """Poll the deletion status until the files are gone; return its last reading."""
        return poll_until(
            lambda: self.service.deletion_status(app_id),
            lambda status: status.state == "purged",
            timeout=timeout,
            interval=2.0,
        )

    def create_many(self, project: str, count: int) -> list[HostedApplication]:
        """Create ``count`` private applications, several requests at a time."""
        with ThreadPoolExecutor(max_workers=BULK_WORKERS) as pool:
            return list(pool.map(lambda _: self.create_app(project), range(count)))

    def all_app_ids(self, scope: str = "mine", q: str = "") -> list[str]:
        """Ids of every application the user lists in a scope, over all pages."""
        ids: list[str] = []
        cursor = None
        while True:
            page = self.service.list_applications(
                scope=scope, q=q, limit=CATALOG_PAGE_SIZE, cursor=cursor
            )
            ids.extend(item.id for item in page.items)
            cursor = page.next_cursor
            if cursor is None:
                return ids

    def reach_application_limit(self, project: str) -> Callable[[], Any]:
        """Create applications up to the per-person limit; return the call that asks for one more."""
        self.create_many(project, MAX_APPLICATIONS)
        return lambda: self.service.create_application(
            get_random_name(), "One more than allowed", project
        )

    def reach_upload_limit(self, project: str) -> Callable[[], Any]:
        """Open uploads up to the per-person limit; return the call that starts one more."""
        app = self.create_app(project)
        for _ in range(MAX_OPEN_UPLOADS):
            self.start_upload(app.id, html_artifact())
        return lambda: self.start_upload(app.id, html_artifact())

    def cleanup(self) -> None:
        """Delete every application this helper created; an application already gone is skipped."""

        def delete(app_id: str) -> None:
            try:
                self.delete_app(app_id)
            except Exception as error:
                logger.warning(f"Failed to delete hosted application {app_id}: {error}")

        with ThreadPoolExecutor(max_workers=BULK_WORKERS) as pool:
            list(pool.map(delete, list(self._app_ids)))
        self._app_ids.clear()


@dataclass
class HostedUser:
    """A user created for a hosted-application test, with their own client and helper."""

    email: str
    user_id: str
    client: CodeMieClient
    apps: HostedApplicationUtils
    # Kept for a browser sign-in; empty when the user only calls the API.
    password: str = field(default="", repr=False)

    @property
    def personal_project(self) -> str:
        return self.email

    @property
    def name(self) -> str:
        """Display name, as the people search and the share lists show it."""
        return self.client.users.about_me().name

    @property
    def service(self) -> Any:
        return self.client.hosted_applications
