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

"""UI test for the upload limits hint of the assistant logo input."""

import pytest

from codemie_test_harness.tests.ui.pageobject.assistants.create_edit_assistant_page import (
    CreateEditAssistantPage,
)


# @case workflow-icon-file-upload_TC_015
@pytest.mark.assistant
@pytest.mark.ui
def test_assistant_logo_input_shows_upload_limits_hint(page):
    create_page = CreateEditAssistantPage(page)
    create_page.navigate_to()

    create_page.should_have_logo_upload_hint()
