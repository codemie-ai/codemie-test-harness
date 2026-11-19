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

"""Fixtures for the hosted application UI tests.

The signed-in UI user owns the applications: they are created through the API and deleted
through the API after the test.
"""

import pytest

from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.test_data.hosted_application_test_data import (
    html_artifact,
)
from codemie_test_harness.tests.utils.hosted_application_utils import (
    HostedApplicationUtils,
)


@pytest.fixture
def ui_owner_apps(client):
    """Hosted-application helper of the signed-in UI user; deletes what the test created."""
    apps = HostedApplicationUtils(client)
    yield apps
    apps.cleanup()


@pytest.fixture
def ui_project(client):
    """Project the UI user creates applications in: the test project when the user has it."""
    applications = client.users.about_me().applications
    return PROJECT if PROJECT in applications else applications[0]


@pytest.fixture
def ui_live_app(ui_owner_apps, ui_project):
    """An application of the UI user with a live HTML version. Yields ``(application, artifact)``."""
    artifact = html_artifact()
    app = ui_owner_apps.create_app(ui_project)
    ui_owner_apps.go_live(app.id, artifact)
    return ui_owner_apps.get_app(app.id), artifact


@pytest.fixture
def ui_unreleased_app(ui_owner_apps, ui_project):
    """An application of the UI user whose only version is accepted but not live.

    Yields ``(application, artifact, version)``.
    """
    artifact = html_artifact()
    app = ui_owner_apps.create_app(ui_project)
    version = ui_owner_apps.upload_accepted_version(app.id, artifact)
    return ui_owner_apps.get_app(app.id), artifact, version
