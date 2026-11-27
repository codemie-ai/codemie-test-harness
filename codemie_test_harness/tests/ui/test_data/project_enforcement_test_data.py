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

"""Test data for the project enforcement confirmation UI tests."""

ORIGINAL_DESCRIPTION = "Original project description"
DESCRIPTION_SUFFIX = " edited before saving"

ENFORCEMENT_FIELD = "enforce_member_spend_limits"

# Confirmation copy. FE source of truth (codemie-ui): src/constants/projectEnforcement.ts:32-44.
TURN_ON_HEADER = "Turn on member spend limit enforcement?"
TURN_ON_CLAUSES = (
    "Each member will be capped at their own limit: their share of the project budget, "
    "or their fixed limit if they have one.",
    "Members who are already over their limit will be blocked right away.",
)
TURN_ON_BUTTON = "Turn on enforcement"

TURN_OFF_HEADER = "Turn off member spend limit enforcement?"
TURN_OFF_CLAUSES = (
    "Members will no longer be capped one by one and can draw on the full project budget.",
    "The project budget cap still applies, spend is still tracked per member, and members "
    "with their own fixed limit stay capped.",
)
TURN_OFF_BUTTON = "Turn off enforcement"

# Body the browser-side fault injection answers a project PATCH with. ProjectDetailsPage shows
# error.parsedError.message (the body's error.message) in an error toast
# (codemie-ui ProjectDetailsPage.tsx:217-220, src/utils/api.ts:525).
INJECTED_SAVE_FAILURE = "injected failure"

# Message of the backend's 403 for a caller who may not update the project
# (codemie project_service.py:110, raised at :568).
ACCESS_DENIED_MESSAGE = "Access denied"
