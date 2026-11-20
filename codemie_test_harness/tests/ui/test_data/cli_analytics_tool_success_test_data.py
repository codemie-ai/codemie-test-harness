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

"""Test data for the CLI Analytics Tool Success UI tests."""

from dataclasses import dataclass

from codemie_test_harness.tests.ui.test_data.analytics_test_data import (
    TOOL_SUCCESS_DASH,
)


@dataclass(frozen=True)
class ToolSuccessCase:
    """One user's tool calls and the Tool Success each CLI Analytics surface shows for them.

    The Overview card writes the rate with two decimals and a ``succeeded`` suffix, the Users
    table and the user modal with two decimals alone. With no tool calls there is no rate to
    show, so every surface shows the dash.
    """

    id: str
    tool_calls_succeeded: int
    tool_calls_failed: int
    overview_success: str
    users_success: str

    @property
    def tool_calls(self) -> str:
        """Tool Calls as the UI writes it."""
        return str(self.tool_calls_succeeded + self.tool_calls_failed)


NO_TOOL_CALLS = ToolSuccessCase(
    id="no-tool-calls",
    tool_calls_succeeded=0,
    tool_calls_failed=0,
    overview_success=TOOL_SUCCESS_DASH,
    users_success=TOOL_SUCCESS_DASH,
)
SOME_TOOL_CALLS_FAILED = ToolSuccessCase(
    id="some-tool-calls-failed",
    tool_calls_succeeded=3,
    tool_calls_failed=1,
    overview_success="75.00% succeeded",
    users_success="75.00%",
)
ALL_TOOL_CALLS_FAILED = ToolSuccessCase(
    id="all-tool-calls-failed",
    tool_calls_succeeded=0,
    tool_calls_failed=2,
    overview_success="0.00% succeeded",
    users_success="0.00%",
)

TOOL_SUCCESS_CASES = [NO_TOOL_CALLS, SOME_TOOL_CALLS_FAILED, ALL_TOOL_CALLS_FAILED]
