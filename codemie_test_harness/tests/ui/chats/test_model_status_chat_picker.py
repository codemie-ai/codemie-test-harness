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

"""UI tests for the status of a model in the chat model picker.

A Deprecated model stays listed, marked, but cannot be picked for new work; a
Disabled model is not listed. The status is set through the API before the chat
opens and restored in a fixture teardown, so the tests run outside parallel mode
(``not_for_parallel_run``).
"""

import pytest

from codemie_sdk.models.llm import ModelStatus


# @case platform-model-management_TC_013
@pytest.mark.not_for_parallel_run
@pytest.mark.chat
@pytest.mark.llm
@pytest.mark.ui
def test_chat_model_picker_marks_a_deprecated_model_and_blocks_it(
    page, navigate_to_new_chat_page, llm_model_status_utils, status_test_model
):
    label = status_test_model.label
    llm_model_status_utils.apply_status(
        status_test_model.base_name, ModelStatus.DEPRECATED
    )
    chat_page = navigate_to_new_chat_page(page)

    chat_page.open_model_picker()
    chat_page.search_model_in_picker(label)
    chat_page.should_show_deprecated_meta_in_picker(label)
    chat_page.should_block_model_in_picker(label)
    chat_page.try_to_pick_blocked_model_in_picker(label)

    chat_page.should_keep_default_model_selected()


# @case platform-model-management_TC_013
@pytest.mark.not_for_parallel_run
@pytest.mark.chat
@pytest.mark.llm
@pytest.mark.ui
def test_chat_model_picker_hides_a_disabled_model(
    page, navigate_to_new_chat_page, llm_model_status_utils, status_test_model
):
    llm_model_status_utils.apply_status(
        status_test_model.base_name, ModelStatus.DISABLED
    )
    chat_page = navigate_to_new_chat_page(page)

    chat_page.open_model_picker()

    chat_page.should_not_list_model_in_picker(status_test_model.label)
