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

"""UI test data for administration page tests."""

from dataclasses import dataclass, field

from codemie_test_harness.tests.utils.base_utils import get_random_name

# ── Customer Configuration marker label strings ───────────────────────────────
# Exact text values as they appear in the live UI (confirmed via playwright-cli
# inspection on 2026-08-31).

MARKER_DEFAULT = "Default from config"
MARKER_OVERRIDDEN = "Overridden"

# Component identifier for the chatDisclaimer setting
COMPONENT_ID_CHAT_DISCLAIMER = "chatDisclaimer"


@dataclass
class DisclaimerFormData:
    """Form input data for the Customer Configuration admin page."""

    disclaimer_text: str = field(
        default_factory=lambda: f"UI autotest disclaimer {get_random_name()}"
    )
    enabled: bool = True


def get_disclaimer_form_data(text: str | None = None) -> DisclaimerFormData:
    """Build UI form input data for disclaimer editing.

    Args:
        text: Custom disclaimer text.  When *None* a short unique text is
              generated that fits the textarea without truncation.

    Returns:
        :class:`DisclaimerFormData` instance ready for use in tests.
    """
    if text is not None:
        return DisclaimerFormData(disclaimer_text=text)
    return DisclaimerFormData()
