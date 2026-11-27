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

"""Test data for the bulk 'Budget Override — N users' UI tests."""

import re

# Category split of the budget group for the two-category bulk scenario.
BULK_TWO_CATEGORY_DISTRIBUTION = {"platform": 60.0, "cli": 40.0}

# Hard limit typed into the CLI card of the bulk modal. The modal caps each selected member at
# the category share divided by the number of selected members: 40.0 / 2 = 20.0 per member.
BULK_CLI_TYPED_HARD_LIMIT = 20.0

# Per-member overrides for two selected members, sized so that the two members together fit
# each category share above (platform 60.0 -> 30.0 each, cli 40.0 -> 20.0 each).
BULK_PLATFORM_MEMBER_MAX = 30.0
BULK_PLATFORM_MEMBER_SOFT = 15.0
BULK_CLI_MEMBER_MAX = 20.0
BULK_CLI_MEMBER_SOFT = 10.0

# Hard limit the Platform card shows after 'Use project allocation': the platform amount of
# the single-category group of the project fixture (100.0), with or without decimals.
PROJECT_PLATFORM_HARD_LIMIT = re.compile(r"^100(\.0+)?$")


def bulk_saved_toast(user_count: int) -> str:
    """Success toast text of a bulk override saved for the given number of users."""
    return f"Updated budget overrides for {user_count} user(s) successfully"
