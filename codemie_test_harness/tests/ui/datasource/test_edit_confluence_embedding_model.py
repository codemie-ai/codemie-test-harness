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
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.ui.pageobject.datasources.create_edit_datasource_page import (
    CreateEditDatasourcePage,
)
from codemie_test_harness.tests.ui.pageobject.datasources.datasource_page import (
    DataSourcePage,
)


@pytest.fixture
def alternative_embedding_llm(
    request, client, confluence_datasource, default_embedding_llm
):
    """An embedding model the stand offers other than the one the datasource has.

    The position (``request.param``) selects which of the alternatives is used,
    so the test runs once per non-default model the picker offers. A datasource
    without a stored model is treated as using the default embedding model.
    """
    stored_model = client.datasources.get(confluence_datasource.id).embeddings_model
    current_model = stored_model or default_embedding_llm.base_name
    alternatives = [
        model
        for model in client.llms.list_embeddings()
        if model.enabled and model.base_name != current_model
    ]
    if request.param >= len(alternatives):
        pytest.skip(
            f"the stand offers only {len(alternatives)} embedding model(s) "
            f"besides '{current_model}'"
        )
    return alternatives[request.param]


@pytest.mark.parametrize(
    "alternative_embedding_llm",
    [0, 1],
    ids=["first_non_default_model", "second_non_default_model"],
    indirect=True,
)
@pytest.mark.confluence
@pytest.mark.datasource
@pytest.mark.ui
def test_confluence_datasource_keeps_selected_embedding_model_after_save(
    page,
    client,
    confluence_datasource,
    alternative_embedding_llm,
):
    """Selected embedding model not saved for Confluence data source type:
    always resets to "Text Embedding Ada" after edit.

    Regression: after the user edits a Confluence datasource, selects an embedding
    model other than the default and saves, the edit form still shows that model,
    the backend stores it, and no other datasource parameter changes.

    Steps:
        1. Record description, CQL and "shared with project" of the datasource.
        2. Open the edit form, select a non-default embedding model and click Save.
        3. Reopen the edit form; the picker shows the selected model, not the default.
        4. Read the datasource back through the API; the stored model is the selected one.
        5. Description, CQL and "shared with project" equal the values recorded in step 1.
    """
    # @case selected-embedding-model-not-saved_TC_001
    datasource_page = DataSourcePage(page)
    edit_page = CreateEditDatasourcePage(page)
    model_label = alternative_embedding_llm.label or (
        alternative_embedding_llm.deployment_name
    )
    before = client.datasources.get(confluence_datasource.id)

    datasource_page.navigate_to()
    datasource_page.should_see_datasource_with_name(before.name)
    datasource_page.open_and_select_row_action(before.name, "Edit")
    edit_page.dismiss_guided_tour_if_shown()
    edit_page.should_see_disabled_name_input(before.name)
    edit_page.select_embeddings_model(model_label)
    edit_page.should_see_selected_embeddings_model(model_label)
    edit_page.click_save()
    datasource_page.should_see_datasource_with_name(before.name)

    datasource_page.open_and_select_row_action(before.name, "Edit")
    edit_page.dismiss_guided_tour_if_shown()
    edit_page.should_see_disabled_name_input(before.name)
    edit_page.should_see_selected_embeddings_model(model_label)

    after = client.datasources.get(confluence_datasource.id)
    assert_that(
        after.embeddings_model,
        equal_to(alternative_embedding_llm.base_name),
        "The backend stores the embedding model selected in the UI",
    )
    assert_that(
        after.description,
        equal_to(before.description),
        "Changing the embedding model does not change the description",
    )
    assert_that(
        after.confluence.cql,
        equal_to(before.confluence.cql),
        "Changing the embedding model does not change the CQL query",
    )
    assert_that(
        after.shared_with_project,
        equal_to(before.shared_with_project),
        "Changing the embedding model does not change 'shared with project'",
    )
