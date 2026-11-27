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

"""UI tests for the Applications area routes with hosted applications switched on."""

import pytest

from codemie_test_harness.tests.ui.pageobject.hosted_applications.hosted_applications_page import (
    HostedApplicationsPage,
)

CAPABILITY = "features:hostedApplications"


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.ui
@pytest.mark.prod_regression
def test_legacy_applications_route_lands_on_apps_and_platform_tab_lists_platform_apps(
    page,
):
    # @case hosted-applications-upload-share-view_TC_003
    applications = HostedApplicationsPage(page)

    applications.open_legacy_applications_route()
    applications.should_be_on_applications_route()

    applications.open_platform_apps_tab()
    applications.should_show_platform_apps()
