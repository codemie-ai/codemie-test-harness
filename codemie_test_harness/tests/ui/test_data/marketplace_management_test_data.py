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

"""Test data for the marketplace management UI tests."""

import pytest

# (state of the assistant, data-status of its badge, badge label) for assistants that are
# still private, so the Project Assistants tab lists them. A verified assistant is global
# (published) and is listed under the Marketplace tab instead.
BADGE_STATE_PARAMS = [
    pytest.param("pending", "pending", "● REVIEW", id="pending"),
    pytest.param("rejected", "rejected", "✕ REJECTED", id="rejected"),
]

# Reason lengths around the 20-character minimum of the reject form.
SHORT_REJECT_REASON = "r" * 19
MINIMUM_REJECT_REASON = "r" * 20
BULK_REJECT_REASON = "The description does not explain what this assistant is for."
