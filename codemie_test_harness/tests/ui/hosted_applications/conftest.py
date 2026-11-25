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

from types import SimpleNamespace

import pytest

from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.test_data.hosted_application_test_data import (
    html_artifact,
)
from codemie_test_harness.tests.test_data.hosted_application_category_test_data import (
    CATEGORY_APP_LABELS,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.hosted_application_utils import (
    HostedApplicationUtils,
)


@pytest.fixture(autouse=True)
def allow_local_network_access(context):
    """Let the viewer frame load application content served from a private address.

    Where the content domain resolves to a private address and the UI to a public one,
    Chromium's Local Network Access check blocks the frame (ERR_BLOCKED_BY_LOCAL_NETWORK_ACCESS_CHECKS)
    and the viewer reports the application as unavailable. A real browser asks the user;
    granting the permission is the test's answer to that prompt.
    """
    context.grant_permissions(["local-network-access"])


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
def ui_empty_app(ui_owner_apps, ui_project):
    """An application of the UI user that has no version at all."""
    app = ui_owner_apps.create_app(ui_project)
    return ui_owner_apps.get_app(app.id)


@pytest.fixture
def ui_unreleased_app(ui_owner_apps, ui_project):
    """An application of the UI user whose only version is accepted but not live.

    Yields ``(application, artifact, version)``.
    """
    artifact = html_artifact()
    app = ui_owner_apps.create_app(ui_project)
    version = ui_owner_apps.upload_accepted_version(app.id, artifact)
    return ui_owner_apps.get_app(app.id), artifact, version


# The applications of the category filter test that are published, by the collection it opens.
PUBLISHED_IN_COLLECTION = {"mine": (), "marketplace": ("alpha", "beta", "both")}
# The ones that collection does not list while no category is selected.
UNLISTED_IN_COLLECTION = {"mine": (), "marketplace": ("plain",)}


@pytest.fixture
def ui_new_app_name(ui_owner_apps):
    """A name for an application the test creates through the browser.

    After the test, an application of that name is found and deleted through the API.
    """
    name = get_random_name()
    yield name
    ui_owner_apps.adopt(name)


@pytest.fixture
def ui_category_apps(request, ui_owner_apps, ui_project, hosted_categories):
    """Applications of the UI user tagged with the first two of ``hosted_categories``, or with none.

    Parametrize it indirectly with a collection name: ``mine`` or ``marketplace``. The
    applications of the marketplace are published, the one without a category is not.
    ``names`` maps a label from ``CATEGORY_APP_LABELS`` to the application's name, which starts
    with ``token``.
    """
    token = get_random_name()
    names = {}
    for label, indexes in CATEGORY_APP_LABELS.items():
        app = ui_owner_apps.create_app(
            ui_project,
            name=f"{token} {label}",
            categories=[hosted_categories[index].id for index in indexes],
        )
        names[label] = app.name
        if label in PUBLISHED_IN_COLLECTION[request.param]:
            ui_owner_apps.publish(app.id, [c.id for c in app.categories])
    return SimpleNamespace(
        collection=request.param,
        token=token,
        names=names,
        listed=[
            name
            for label, name in names.items()
            if label not in UNLISTED_IN_COLLECTION[request.param]
        ],
    )
