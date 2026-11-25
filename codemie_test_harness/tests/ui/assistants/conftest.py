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

import pytest

from codemie_test_harness.tests.utils.logger_util import setup_logger

logger = setup_logger(__name__)


@pytest.fixture
def clear_asst_ai_popup(page):
    """Remove the assistant AI popup suppression so the modal appears for tests that verify it."""
    page.add_init_script("localStorage.removeItem('codemie-new-asst-ai-popup');")
    yield


@pytest.fixture
def ui_created_assistant_names(assistant_utils):
    """Names of assistants created through the UI form; deleted through the API on teardown."""
    names = []
    yield names
    for name in names:
        try:
            assistant_utils.delete_assistant(
                assistant_utils.get_assistant_by_name(name)
            )
        except Exception as e:
            logger.warning(f"Failed to delete UI-created assistant {name}: {e}")
