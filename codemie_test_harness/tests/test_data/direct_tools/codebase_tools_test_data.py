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

from codemie_test_harness.tests.enums.tools import Toolkit, CodeBaseTool

# `expected_issue_type` matches the request's `"types":"CODE_SMELL"` filter and is
# checked structurally by `sonar_seed.assert_issue_search_response` - see that module
# for why these tests no longer assert on a hardcoded issues/search response.
sonar_tools_test_data = [
    pytest.param(
        Toolkit.CODEBASE_TOOLS,
        CodeBaseTool.SONAR,
        {
            "relative_url": "/api/issues/search",
            "params": '{"types":"CODE_SMELL","ps":"1"}',
        },
        "CODE_SMELL",
        marks=pytest.mark.sonar,
        id=CodeBaseTool.SONAR,
    ),
    pytest.param(
        Toolkit.CODEBASE_TOOLS,
        CodeBaseTool.SONAR_CLOUD,
        {
            "relative_url": "/api/issues/search",
            "params": '{"types":"CODE_SMELL","ps":"1"}',
        },
        "CODE_SMELL",
        marks=[pytest.mark.sonar, pytest.mark.smoke],
        id=CodeBaseTool.SONAR_CLOUD,
    ),
]
