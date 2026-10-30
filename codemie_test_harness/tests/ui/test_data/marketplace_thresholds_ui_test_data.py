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

"""UI test data for the Marketplace management Config tab.

The Config tab renders one settings card per marketplace declaration; the
thresholds card is titled by the declaration label and carries its own
"Overridden" / "Default from config" marker.
"""

from codemie_test_harness.tests.test_data.marketplace_thresholds_test_data import (
    DEFAULT_THRESHOLDS,
)

# Heading of the thresholds card (declaration label).
THRESHOLDS_CARD_HEADING = "Marketplace Thresholds"

# Input labels exactly as declared for marketplaceThresholds.
LABEL_HOT = "Hot tier min. users"
LABEL_WARM = "Warm tier min. users"
LABEL_COLD = "Cold tier min. users"
LABEL_GRACE = "Cold grace period (days)"
LABEL_ARCHIVE = "Dead grace period (days)"

# Default form values keyed by input label.
DEFAULT_FORM_VALUES = {
    LABEL_HOT: DEFAULT_THRESHOLDS["hotMinUsers"],
    LABEL_WARM: DEFAULT_THRESHOLDS["warmMinUsers"],
    LABEL_COLD: DEFAULT_THRESHOLDS["coldMinUsers"],
    LABEL_GRACE: DEFAULT_THRESHOLDS["graceDays"],
    LABEL_ARCHIVE: DEFAULT_THRESHOLDS["archiveDeadAfterDays"],
}

# A valid change to a single field; every other field keeps its default.
CHANGED_GRACE_DAYS = "45"

# Form values after saving CHANGED_GRACE_DAYS.
CHANGED_FORM_VALUES = {**DEFAULT_FORM_VALUES, LABEL_GRACE: CHANGED_GRACE_DAYS}

MARKER_DEFAULT = "Default from config"
MARKER_OVERRIDDEN = "Overridden"

# Config tab position: label patterns in tab-strip order. The two middle tabs
# append a live count, so they are matched by prefix.
TAB_LABEL_PATTERNS = [
    r"^Overview$",
    r"^Review queue",
    r"^Cleanup queue",
    r"^Config$",
]
