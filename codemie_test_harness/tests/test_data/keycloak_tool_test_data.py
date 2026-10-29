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

from codemie_test_harness.tests.utils.jira_seed import Seeded
from codemie_test_harness.tests.utils.keycloak_seed import (
    KEYCLOAK_SEED_USER,
    SEED_USERNAME,
    render_seed_user_response,
)

# The realm is shared and its user list changes, so the tool is asked for all
# users but the answer is narrowed to the seed user, which is stable.
KEYCLOAK_TOOL_PROMPT = f"Get information about all users and show only the user with username {SEED_USERNAME}"

# Resolve with the ``seeded`` fixture.
KEYCLOAK_TOOL_RESPONSE = Seeded(KEYCLOAK_SEED_USER, render_seed_user_response)
