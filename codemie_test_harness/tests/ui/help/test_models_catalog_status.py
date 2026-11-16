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

"""UI tests for the status of a model in the Available models catalog (/help/models).

The status is set through the API before the page opens and restored in a fixture
teardown, so the tests run outside parallel mode (``not_for_parallel_run``).
"""

import pytest

from codemie_sdk.models.llm import ModelStatus

from codemie_test_harness.tests.ui.pageobject.available_models_page import (
    AvailableModelsPage,
)


# @case platform-model-management_TC_014
@pytest.mark.not_for_parallel_run
@pytest.mark.help
@pytest.mark.llm
@pytest.mark.ui
def test_help_models_catalog_shows_a_deprecated_badge(
    page, llm_model_status_utils, status_test_model
):
    llm_model_status_utils.apply_status(
        status_test_model.base_name, ModelStatus.DEPRECATED
    )

    catalog_page = AvailableModelsPage(page).navigate_to()

    catalog_page.should_show_model_with_deprecated_mark(status_test_model.label)


# @case platform-model-management_TC_015
@pytest.mark.not_for_parallel_run
@pytest.mark.help
@pytest.mark.llm
@pytest.mark.ui
def test_help_models_catalog_hides_a_disabled_model(
    page, llm_model_status_utils, status_test_model
):
    llm_model_status_utils.apply_status(
        status_test_model.base_name, ModelStatus.DISABLED
    )

    catalog_page = AvailableModelsPage(page).navigate_to()

    catalog_page.should_not_list_model_once_catalog_is_loaded(status_test_model.label)
