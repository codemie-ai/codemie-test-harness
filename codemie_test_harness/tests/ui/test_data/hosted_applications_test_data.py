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

"""Test data for the hosted application UI tests."""

import pytest

from codemie_test_harness.tests.utils.hosted_application_utils import (
    HostedVersionState,
)

# Ways to activate an openable card: a click, or a key pressed while the card is focused.
CARD_ACTIVATIONS = [
    pytest.param("click", id="click"),
    pytest.param("Enter", id="enter-key"),
    pytest.param("Space", id="space-key"),
]

# State of the application, the label of the manager's next-step button on its card.
NEXT_STEP_BUTTONS = [
    pytest.param(HostedVersionState.NONE, "Upload version", id="no-version-uploaded"),
    pytest.param(
        HostedVersionState.UPLOADED, "Activate version", id="uploaded-not-active"
    ),
]

# State of the application, whether its details-page launch button is enabled.
DETAILS_LAUNCH_BUTTON_STATES = [
    pytest.param(HostedVersionState.ACTIVE, True, id="active-version-enabled"),
    pytest.param(HostedVersionState.NONE, False, id="no-active-version-disabled"),
]
