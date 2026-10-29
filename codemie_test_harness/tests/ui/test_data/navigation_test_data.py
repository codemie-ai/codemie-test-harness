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

"""
Test data for left navigation menu UI tests.

Viewport heights are representative picks: the supported viewport set is not
defined by the ticket (AC-6), so these are placeholders to be replaced with the
product-confirmed list.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Viewport:
    """Browser viewport size in pixels."""

    width: int
    height: int


# Heights at which the nav content (logo, links, bottom block) overflows.
LIMITED_VIEWPORTS = [
    Viewport(width=1280, height=480),
    Viewport(width=1440, height=600),
]
LIMITED_VIEWPORT_IDS = ["1280x480", "1440x600"]

# Smallest of the limited viewports, used by single-viewport scenarios.
SMALL_VIEWPORT = LIMITED_VIEWPORTS[0]

# Default desktop viewport the harness uses.
DESKTOP_VIEWPORT = Viewport(width=1920, height=1080)


class ScrollInput:
    """Input methods used to scroll the navigation links."""

    MOUSE_WHEEL = "mouse_wheel"
    KEYBOARD_TAB = "keyboard_tab"
