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

import os

import pytest
from hamcrest import assert_that, equal_to
from requests import HTTPError

from codemie_test_harness.tests.test_data.google_datasource_test_data import (
    RESPONSE_FOR_GOOGLE_DOC,
    USER_PROMPT,
    get_google_doc_url,
)
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    assert_response,
    assert_tool_triggered,
)
from codemie_test_harness.tests.enums.tools import Default


@pytest.mark.datasource
@pytest.mark.google
@pytest.mark.api
@pytest.mark.smoke
def test_create_datasource_with_google_integration(
    datasource_utils,
    assistant,
    assistant_utils,
    similarity_check,
    kb_context,
    google_doc_datasource,
):
    assistant = assistant(
        context=kb_context(google_doc_datasource),
        system_prompt="Run tools on each user prompt",
    )

    response_from_llm, triggered_tools = assistant_utils.ask_assistant(
        assistant, USER_PROMPT, minimal_response=False
    )
    assert_tool_triggered(Default.SEARCH_KB, triggered_tools)
    similarity_check.check_similarity(response_from_llm, RESPONSE_FOR_GOOGLE_DOC)

    datasource_utils.update_google_doc_datasource(
        google_doc_datasource.id, full_reindex=True, skip_reindex=False
    )

    response_from_llm, triggered_tools = assistant_utils.ask_assistant(
        assistant, USER_PROMPT, minimal_response=False
    )
    assert_tool_triggered(Default.SEARCH_KB, triggered_tools)
    similarity_check.check_similarity(response_from_llm, RESPONSE_FOR_GOOGLE_DOC)


@pytest.mark.datasource
@pytest.mark.google
@pytest.mark.api
def test_edit_description_for_google_data_source(
    client, datasource_utils, google_doc_datasource
):
    updated_description = get_random_name()

    datasource_utils.update_google_doc_datasource(
        google_doc_datasource.id, description=updated_description
    )

    updated_datasource = client.datasources.get(google_doc_datasource.id)
    assert_that(updated_datasource.description, equal_to(updated_description))


@pytest.mark.datasource
@pytest.mark.google
@pytest.mark.api
def test_create_google_doc_datasource_with_existing_name(
    google_doc_datasource, datasource_utils
):
    datasource = datasource_utils.get_datasource(google_doc_datasource.id)

    try:
        datasource_utils.create_google_doc_datasource(
            name=datasource.name, google_doc=get_google_doc_url()
        )
        raise AssertionError("There are no error message for duplicate datasource name")
    except HTTPError as e:
        assert_response(
            e.response,
            409,
            f"An index with the name '{datasource.name}' already exists in the project '{os.getenv('PROJECT_NAME')}'.",
        )
