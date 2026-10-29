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

from codemie_test_harness.tests.enums.tools import Toolkit, AccessManagementTool
from codemie_test_harness.tests.test_data.keycloak_tool_test_data import (
    KEYCLOAK_TOOL_PROMPT,
    KEYCLOAK_TOOL_RESPONSE,
)
from codemie_test_harness.tests.utils.base_utils import assert_tool_triggered


@pytest.mark.assistant
@pytest.mark.keycloak
@pytest.mark.api
def test_assistant_with_keycloak_tool(
    assistant_utils,
    assistant,
    keycloak_integration,
    similarity_check,
    seeded,
):
    keycloak_assistant = assistant(
        Toolkit.ACCESS_MANAGEMENT,
        AccessManagementTool.KEYCLOAK,
        settings=keycloak_integration,
    )

    response, triggered_tools = assistant_utils.ask_assistant(
        keycloak_assistant, KEYCLOAK_TOOL_PROMPT, minimal_response=False
    )

    assert_tool_triggered(AccessManagementTool.KEYCLOAK, triggered_tools)

    similarity_check.check_similarity(response, seeded(KEYCLOAK_TOOL_RESPONSE))
