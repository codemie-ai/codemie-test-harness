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

"""Test data for project admin member budget override tests."""

MEMBER_OVERRIDE_MAX = 40.0
MEMBER_OVERRIDE_SOFT = 20.0
DENIED_OVERRIDE_MAX = 10.0
DENIED_OVERRIDE_SOFT = 5.0
NO_PERMISSION_MESSAGE = "do not have permission to manage member budgets"

# (AdminProjectBudgetUtils method name, extra positional args after budget_id/user_id)
DENIED_MUTATIONS = [
    ("override_member", (DENIED_OVERRIDE_MAX, DENIED_OVERRIDE_SOFT)),
    ("clear_member_override", ()),
]
DENIED_MUTATION_IDS = ["patch_override", "delete_override"]
