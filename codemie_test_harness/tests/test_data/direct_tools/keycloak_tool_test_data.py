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

from urllib.parse import quote

from codemie_test_harness.tests.utils.jira_seed import Seeded
from codemie_test_harness.tests.utils.keycloak_seed import (
    KEYCLOAK_SEED_USER,
    SEED_USERNAME,
    render_seed_user_json,
)

# Look up the seed user directly; the realm's other users are irrelevant. The
# query lives in relative_url because stored params are not applied when the
# workflow input overrides the tool args.
KEYCLOAK_DIRECT_TOOL_PROMPT = {
    "method": "GET",
    "relative_url": f"/users?username={quote(SEED_USERNAME)}&exact=true",
    "params": "",
}

# Resolve with the ``seeded`` fixture.
KEYCLOAK_DIRECT_TOOL_RESPONSE = Seeded(KEYCLOAK_SEED_USER, render_seed_user_json)
