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
from codemie_sdk.models.integration import CredentialTypes
from hamcrest import assert_that, has_item, equal_to

from codemie_test_harness.tests.enums.model_types import ModelTypes
from codemie_test_harness.tests.test_data.llm_test_data import MODEL_RESPONSES
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.constants import test_project_name
from codemie_test_harness.tests.utils.env_resolver import (
    get_environment,
    EnvironmentResolver,
)

pytestmark = pytest.mark.skipif(
    EnvironmentResolver.is_sandbox() or EnvironmentResolver.is_localhost(),
    reason="Skipping this tests on sandbox environments",
)


@pytest.fixture(scope="function")
def invalid_lite_llm_integration(integration_utils):
    credential_values = CredentialsManager.invalid_lite_llm_credentials()
    integration = integration_utils.create_user_integration(
        CredentialTypes.LITE_LLM,
        credential_values,
        project_name=test_project_name,
    )
    yield integration
    if integration:
        integration_utils.delete_integration(integration)


def pytest_generate_tests(metafunc):
    if "model_type" in metafunc.fixturenames:
        # Use predefined model list with environment-specific filtering
        test_data = []
        env = get_environment()
        for model_data in MODEL_RESPONSES:
            test_data.append(
                pytest.param(
                    model_data.model_type,
                    marks=pytest.mark.skipif(
                        env not in model_data.environments,
                        reason=f"Skip on non {'/'.join(str(env) for env in model_data.environments[:-1])} envs",
                    ),
                )
            )

        metafunc.parametrize("model_type", test_data)


@pytest.mark.assistant
@pytest.mark.lite_llm
@pytest.mark.enterprise
@pytest.mark.api
def test_assistant_with_different_models_in_lite_llm(
    llm_utils,
    lite_llm_integration,
    assistant_factory,
    assistant_utils,
    model_type,
    similarity_check,
):
    assert_that(
        [row.base_name for row in llm_utils.list_llm_models()],
        has_item(model_type),
        f"{model_type} is missing in backend response",
    )
    assistant = assistant_factory.create(model_type)
    response = assistant_utils.ask_assistant(assistant, "Just say one word: 'Hello'")

    if model_type == ModelTypes.DEEPSEEK_V4_PRO:
        response = "\n".join(response.split("\n")[-3:])
        response = response.replace("</think>\n\n", "")
    similarity_check.check_similarity(response, "Hello")


@pytest.mark.assistant
@pytest.mark.lite_llm
@pytest.mark.enterprise
@pytest.mark.api
def test_assistant_with_invalid_lite_llm(
    invalid_lite_llm_integration,
    assistant,
    assistant_utils,
):
    assistant = assistant(project_name=test_project_name)
    response = assistant_utils.ask_assistant(assistant, "Just say one word: 'Hello'")
    assert_that(
        response,
        equal_to(
            """Error code: 401 - {'error': {'message': "LiteLLM Virtual Key expected. Received=wron****_key, expected to start with 'sk-'.", 'type': 'auth_error', 'param': 'None', 'code': '401'}}"""
        ),
    )
