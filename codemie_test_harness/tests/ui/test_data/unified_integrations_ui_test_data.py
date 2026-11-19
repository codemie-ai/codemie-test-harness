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

"""Test data for the unified Integrations list and form UI tests."""

from codemie_sdk.models.integration import IntegrationType

# Scope filter and Scope toggle labels.
SCOPE_ALL = "All"
SCOPE_USER = "User"
SCOPE_PROJECT = "Project"

# Scope as it appears in the address (None: Scope All leaves it out).
URL_SCOPE_BY_LABEL = {SCOPE_ALL: None, SCOPE_USER: "user", SCOPE_PROJECT: "project"}

# Credential types bound to one scope.
DIAL = "DIAL"
GOOGLE_OAUTH = "Google OAuth"
SCOPE_BADGE_PROJECT_ONLY = "Project only"
SCOPE_BADGE_USER_ONLY = "User only"
# Types that exist once in the Type filter although each has OAuth variants.
SINGLE_ENTRY_TYPES = ["Jira", "Confluence", "Git"]

TYPE_HINT_NOT_AVAILABLE_AT_USER = "Not available at User scope"
TYPE_HINT_NOT_AVAILABLE_AT_PROJECT = "Not available at Project scope"
DIAL_REMOVED_NOTE = "DIAL was removed from Type: it exists only at Project scope."

# Rows seeded for the pagination check: 12 rows at Scope All against 10 per page.
USER_ROWS_FOR_PAGINATION = 7
PROJECT_ROWS_FOR_PAGINATION = 5
ROWS_PER_PAGE = 10

# Create form texts.
NEW_INTEGRATION_FORM_SCOPE_BY_LIST_SCOPE = {
    SCOPE_ALL: SCOPE_USER,
    SCOPE_USER: SCOPE_USER,
    SCOPE_PROJECT: SCOPE_PROJECT,
}
PROJECT_CLEARED_NOTE = (
    "Project was cleared: at Project scope you can pick only projects you administer."
)
DIAL_SWITCH_NOTE = (
    "DIAL is available only at Project scope, so Scope switched to Project."
)
GOOGLE_OAUTH_SWITCH_NOTE = (
    "Google OAuth is available only at User scope, so Scope switched to User."
)
PROJECT_ADMINS_ONLY_REASON = (
    "Project integrations can be created by project admins only."
)
DIAL_MEMBER_HINT = "Project only · needs project admin rights"

# Toasts.
SAVED_TOAST = "Integration saved"
SAME_VIEW_TOAST = "You are back on the same view."
HIDDEN_PROJECT_TOAST = "Your filters hide it: it is a Project A2A integration."
CREATED_TOAST = "Integration created successfully"
UPDATED_TOAST = "Integration updated successfully"
DELETED_TOAST = "Integration deleted successfully"

# Scheduler form kinds, as the Create menu names them.
SCHEDULER_KINDS = ["User", "Project"]

SCOPE_BY_SETTING_TYPE = {
    IntegrationType.USER: SCOPE_USER,
    IntegrationType.PROJECT: SCOPE_PROJECT,
}
