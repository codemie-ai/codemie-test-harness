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
"""UI test for the platform Activity Events page (maintainer only).

Covers:
    A row of the platform Activity Events page expands to readable detail
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.activity_events_page import (
    ActivityEventsPage,
)


# @case project-history-modal_TC_016
@pytest.mark.activity
@pytest.mark.project
@pytest.mark.ui
def test_platform_activity_events_page_expands_rows_with_readable_detail(
    page, history_trail
):
    events_page = ActivityEventsPage(page).navigate_to()
    events_page.should_show_events_table_with_rows()

    events_page.expand_first_row()

    events_page.should_show_readable_first_row_detail()
