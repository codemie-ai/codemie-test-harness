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

import pytest
from hamcrest import assert_that, equal_to
from requests import HTTPError

from codemie_sdk.models.integration import (
    CredentialTypes,
    IntegrationType,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


@pytest.mark.integration
@pytest.mark.enterprise
@pytest.mark.api
@pytest.mark.lite_llm
class TestPersonalLiteLLMIntegrations:
    def test_regular_user_can_create_personal_litellm_integration(
        self, non_admin_general_integration, non_admin_integration_utils
    ):
        alias = get_random_name()
        non_admin_general_integration(
            integration_type=IntegrationType.USER,
            credential_type=CredentialTypes.LITE_LLM,
            credential_values=CredentialsManager.lite_llm_credentials(),
            integration_alias=alias,
        )
        fetched = non_admin_integration_utils.get_integration_by_alias(
            alias, IntegrationType.USER
        )
        assert_that(fetched.setting_type, equal_to(IntegrationType.USER))
        assert_that(fetched.credential_type, equal_to(CredentialTypes.LITE_LLM))

    def test_regular_user_cannot_create_project_level_litellm_integration(
        self, non_admin_integration_utils
    ):
        with pytest.raises(HTTPError) as exc_info:
            non_admin_integration_utils.create_project_integration(
                credential_type=CredentialTypes.LITE_LLM,
                credentials=CredentialsManager.lite_llm_credentials(),
            )
        assert_that(exc_info.value.response.status_code, equal_to(403))
