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

"""UI test data for project ownership tests."""

# (acting role, whether the row actions menu offers "Change ownership").
# Roles are resolved by the `acting_credentials` fixture of tests/ui/administration/conftest.py.
CHANGE_OWNERSHIP_VISIBILITY = [
    ("admin", True),
    ("project_admin_member", True),
    ("plain_member", False),
]

CHANGE_OWNERSHIP_VISIBILITY_IDS = ["admin", "project_admin", "plain_member"]
