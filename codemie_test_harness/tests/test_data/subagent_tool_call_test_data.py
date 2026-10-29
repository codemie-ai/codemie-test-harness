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

from codemie_test_harness.tests.utils.jira_seed import JIRA_SERVER_SEED, Seeded

JIRA_SUB_ASSISTANT_SYSTEM_PROMPT = """
    You are a Jira specialist assistant. When you receive a request, you MUST
    immediately call the appropriate Jira tool to complete the task.

    CRITICAL RULES:
    1. ALWAYS call a Jira tool for EVERY request - never respond without calling a tool first
    2. Get the actual data using your tool, then respond with the results
    3. NEVER say "please wait" or "I will retrieve" - just call the tool immediately
"""

PARENT_ASSISTANT_SYSTEM_PROMPT = (
    "You are a coordinator assistant. "
    "Delegate Jira research tasks to your sub-assistants and return their results."
)

PARENT_ASSISTANT_WITH_MULTIPLE_SUBS_SYSTEM_PROMPT = (
    "You are a coordinator assistant with two Jira specialist sub-assistants. "
    "Delegate tasks to them and consolidate the results."
)

JIRA_SUB_ASSISTANT_PROMPT = Seeded(
    JIRA_SERVER_SEED,
    lambda seed: f"Get a title for {seed.key} ticket using your sub-assistant.",
)

BACKEND_400_ERROR_PATTERN = (
    r"Error code: 400|BadRequestError|role 'tool'|preceeding message"
)
