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

"""Utility class for hosted application operations in tests."""

import hashlib
from enum import Enum
from typing import List, Optional

from codemie_sdk.models.hosted_application import (
    HostedApplication,
    HostedApplicationVersion,
)
from hamcrest import assert_that, equal_to, not_none

from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.utils.base_utils import (
    BaseUtils,
    get_random_name,
    poll_until,
)

HOSTED_APP_DESCRIPTION = "Autotest hosted application"
HOSTED_APP_FILENAME = "index.html"
HOSTED_APP_HTML = (
    b'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
    b"<title>Autotest</title></head>"
    b"<body><p>Autotest hosted application</p></body></html>"
)

# Validation states a version passes through before it is accepted or refused.
_VALIDATION_IN_PROGRESS = ("uploading", "queued", "validating")
VALIDATION_TIMEOUT_SECONDS = 180


class HostedVersionState(str, Enum):
    """What an application created for a test has uploaded."""

    NONE = "no version uploaded"
    UPLOADED = "version uploaded, not active"
    ACTIVE = "active version"


class HostedApplicationUtils(BaseUtils):
    """Create, version, share and delete hosted applications through the SDK."""

    def create_application(
        self,
        name: Optional[str] = None,
        description: str = HOSTED_APP_DESCRIPTION,
        project: str = PROJECT,
        shared: bool = False,
    ) -> HostedApplication:
        """Create a private application (or one shared with its project's members)."""
        return self.client.hosted_applications.create_application(
            name=name or get_random_name(),
            description=description,
            project=project,
            shared=shared,
        )

    def upload_version(
        self,
        app_id: str,
        content: bytes = HOSTED_APP_HTML,
        filename: str = HOSTED_APP_FILENAME,
    ) -> HostedApplicationVersion:
        """Upload an HTML version and wait until validation accepts it.

        The accepted version becomes the application's selected version; it is not live
        until `activate_version` is called.
        """
        service = self.client.hosted_applications
        application = service.get_application(app_id)
        start = service.start_version(
            app_id,
            filename=filename,
            artifact_kind="html",
            byte_size=len(content),
            if_match=application.etag,
            sha256=hashlib.sha256(content).hexdigest(),
        )
        receipt = service.upload_artifact(
            app_id,
            start.version_id,
            content,
            upload_etag=start.upload_etag,
            generation=start.generation,
        )
        service.complete_version(
            app_id,
            start.version_id,
            upload_id=start.upload_id,
            sha256=receipt.sha256,
            generation=start.generation,
            if_match=receipt.version_etag,
        )
        version = poll_until(
            lambda: service.get_version(app_id, start.version_id),
            lambda current: current.validation_state not in _VALIDATION_IN_PROGRESS,
            timeout=VALIDATION_TIMEOUT_SECONDS,
            interval=2,
        )
        assert_that(
            version.validation_state,
            equal_to("accepted"),
            f"Version {start.version_id} of application {app_id} was not accepted",
        )
        return version

    def activate_version(self, app_id: str, version_id: str) -> HostedApplication:
        """Make an accepted version the live version."""
        service = self.client.hosted_applications
        return service.activate(
            app_id, version_id, if_match=service.get_application(app_id).etag
        )

    def bring_to_state(
        self, app_id: str, state: HostedVersionState
    ) -> HostedApplication:
        """Upload and activate versions until the application is in `state`.

        Returns the application as its owner sees it, with the fields only managers get.
        """
        if state is not HostedVersionState.NONE:
            version = self.upload_version(app_id)
            if state is HostedVersionState.ACTIVE:
                self.activate_version(app_id, version.id)
        application = self.get_application(app_id)
        self.assert_state(application, state)
        return application

    def get_application(self, app_id: str) -> HostedApplication:
        """The application as its owner sees it, with the fields only managers get."""
        return self.client.hosted_applications.get_application(app_id)

    def share_with_users(self, app_id: str, user_ids: List[str]) -> None:
        """Grant view access to the given users (owner only)."""
        self.client.hosted_applications.share_with_users(app_id, user_ids)

    def delete_application(self, app_id: str) -> None:
        """Delete an application; its files are purged afterwards."""
        service = self.client.hosted_applications
        service.delete_application(
            app_id, if_match=service.get_application(app_id).etag
        )

    @staticmethod
    def assert_state(application: HostedApplication, state: HostedVersionState) -> None:
        """Check the application is in `state`, so a UI test starts from what it names."""
        assert_that(
            application.has_active_version,
            equal_to(state is HostedVersionState.ACTIVE),
            f"has_active_version of {application.id} does not match '{state.value}'",
        )
        if state is not HostedVersionState.NONE:
            assert_that(
                application.selected_version_id,
                not_none(),
                f"{application.id} has no selected version for '{state.value}'",
            )
