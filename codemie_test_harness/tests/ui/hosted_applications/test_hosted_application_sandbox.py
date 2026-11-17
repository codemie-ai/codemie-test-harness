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

"""UI test: the JavaScript of an uploaded application cannot reach out of its sandbox."""

import pytest

from codemie_test_harness.tests.test_data.hosted_application_test_data import (
    probe_artifact,
    storage_holder_artifact,
)
from codemie_test_harness.tests.ui.pageobject.hosted_applications.hosted_application_viewer_page import (
    HostedApplicationViewerPage,
)
from codemie_test_harness.tests.ui.test_data.hosted_application_ui_test_data import (
    HOLDER_WRITTEN_TEXT,
    MANAGEMENT_ROUTE,
    PROBE_REPORT,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

CAPABILITY = "features:hostedApplications"


@pytest.fixture
def management_url():
    """Address of a management route of the stand, which the probe page tries to call."""
    domain = CredentialsManager.get_required_parameter("CODEMIE_API_DOMAIN")
    return domain.rstrip("/") + MANAGEMENT_ROUTE


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.ui
def test_uploaded_script_cannot_reach_the_page_cookies_other_storage_or_the_management_api(
    page, ui_owner_apps, ui_project, management_url
):
    # @case hosted-applications-upload-share-view_TC_016
    holder = ui_owner_apps.create_app(ui_project)
    ui_owner_apps.go_live(holder.id, storage_holder_artifact())
    probe = ui_owner_apps.create_app(ui_project)
    ui_owner_apps.go_live(probe.id, probe_artifact(management_url))
    viewer = HostedApplicationViewerPage(page)

    viewer.open(holder.id)
    viewer.should_show_text(holder.name, HOLDER_WRITTEN_TEXT)
    viewer.open(probe.id)

    viewer.should_report(probe.name, PROBE_REPORT)
