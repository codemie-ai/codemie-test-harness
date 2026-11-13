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

from typing import Optional

import pytest
from requests import HTTPError

from codemie_sdk.models.integration import CredentialTypes, Integration, IntegrationType
from codemie_test_harness.tests.utils.integration_utils import IntegrationUtils


@pytest.fixture
def non_admin_integration_utils(platform_user):
    member_client = platform_user.client
    return IntegrationUtils(member_client)


@pytest.fixture
def non_admin_general_integration(platform_user, non_admin_integration_utils):
    email = platform_user.email
    created_integration: Optional[Integration] = None

    def _create(
        integration_type: IntegrationType,
        credential_type: CredentialTypes,
        credential_values: list,
        integration_alias: str = None,
    ):
        nonlocal created_integration
        created_integration = non_admin_integration_utils.create_integration(
            credential_type=credential_type,
            credential_values=credential_values,
            setting_type=integration_type,
            integration_alias=integration_alias,
            project_name=email,
        )
        return created_integration

    yield _create

    if created_integration:
        try:
            non_admin_integration_utils.delete_integration(created_integration)
        except HTTPError:
            pass
