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

from codemie_test_harness.tests.enums.tools import (
    Toolkit,
)
from codemie_test_harness.tests.test_data.vcs_tools_test_data import (
    vcs_tools_test_data,
)
from codemie_test_harness.tests.utils.base_utils import assert_tool_triggered
from codemie_test_harness.tests.utils.constants import vcs_integrations


@pytest.mark.assistant
@pytest.mark.vcs
@pytest.mark.api
@pytest.mark.smokes
@pytest.mark.parametrize(
    "tool_name,prompt,expected_response",
    vcs_tools_test_data,
    ids=[f"{getattr(row, 'values', row)[0]}" for row in vcs_tools_test_data],
)
def test_create_assistant_with_vcs_tool(
    request,
    assistant_utils,
    assistant,
    similarity_check,
    tool_name,
    prompt,
    expected_response,
    seeded,
):
    prompt = seeded(prompt)
    expected_response = seeded(expected_response)

    _integration = request.getfixturevalue(vcs_integrations[tool_name])

    assistant = assistant(Toolkit.VCS, tool_name, settings=_integration)

    response, triggered_tools = assistant_utils.ask_assistant(
        assistant, prompt, minimal_response=False
    )

    assert_tool_triggered(tool_name, triggered_tools)

    similarity_check.check_similarity(response, expected_response)
