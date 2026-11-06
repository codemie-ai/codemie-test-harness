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

"""Provisioning API: what the OpenAPI document of the stand publishes."""

import pytest
from hamcrest import assert_that, empty, equal_to, has_items

from codemie_test_harness.cli.constants import PROVISIONING_FULL_CLIENT_KEYS
from codemie_test_harness.tests.test_data.provisioning_test_data import VENDOR_NAMES
from codemie_test_harness.tests.utils.provisioning_utils import (
    names_with_vendor,
    openapi_names,
)


@pytest.mark.budget
# A configured client login marks a stand prepared for the provisioning API (it is mounted only when enabled).
@pytest.mark.requires_setting(*PROVISIONING_FULL_CLIENT_KEYS)
@pytest.mark.api
def test_provisioning_routes_and_fields_carry_no_vendor_names(swagger_utils):
    # @case provisioning-api-for-third-party_TC_022
    response = swagger_utils.get_openapi_json()

    assert_that(response.status_code, equal_to(200))
    names = openapi_names(response.json())
    assert_that(
        names,
        has_items(
            "/v1/provisioning/projects",
            "/v1/provisioning/projects/{project_name}/budget",
            "amounts",
            "member_email",
        ),
        "the document describes the provisioning routes this check scans",
    )
    assert_that(
        names_with_vendor(names, VENDOR_NAMES),
        empty(),
        "no provisioning path, parameter or field is named after a vendor",
    )
