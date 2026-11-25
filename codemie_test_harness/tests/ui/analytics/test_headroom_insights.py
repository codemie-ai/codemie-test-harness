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

"""Analytics Insights tab 'Context Compression' (Headroom) section (needs features:headroom on)."""

import pytest

from codemie_test_harness.tests.ui.test_data.headroom_test_data import (
    HEADROOM_SUMMARY_TILE_LABELS,
    HEADROOM_WIDGET_TITLES,
)


# @case headroom-per-assistant-workflow-configuration_TC_008
@pytest.mark.analytics
@pytest.mark.ui
def test_insights_tab_shows_headroom_section(analytics_page):
    analytics_page.should_show_headroom_section(
        widget_titles=HEADROOM_WIDGET_TITLES,
        summary_labels=HEADROOM_SUMMARY_TILE_LABELS,
    )
