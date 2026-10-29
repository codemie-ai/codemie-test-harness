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

"""Test data for the personal project budget guard tests."""

# Project type reported for a user's personal project.
PERSONAL_PROJECT_TYPE = "personal"

# Error body returned when a budget is created for a personal project
# (project_budget_service personal-project guard, HTTP 403).
PERSONAL_PROJECT_BUDGET_MESSAGE = "Cannot create a budget for a personal project"
