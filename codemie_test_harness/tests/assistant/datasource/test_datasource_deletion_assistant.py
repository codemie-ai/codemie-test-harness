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

"""Regression test: Assistant becomes broken if attached datasource is deleted.

Verifies that after a datasource attached to an assistant is deleted:
- the datasource reference is automatically detached from the assistant context;
- the assistant remains usable (chat does not fail with HTTP 500).
"""

import pytest
from hamcrest import assert_that, has_item, is_, is_not, not_none, empty

from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.constants import FILES_PATH


@pytest.fixture(scope="function")
def attached_file_datasource(datasource_utils, client):
    """File datasource that is deleted inside the test; teardown is idempotent."""
    datasource = datasource_utils.create_file_datasource(
        name=get_random_name(),
        files=[str(FILES_PATH / "test.txt")],
    )
    yield datasource
    try:
        client.datasources.delete(datasource.id)
    except Exception:
        pass


@pytest.mark.datasource
@pytest.mark.assistant
@pytest.mark.file
@pytest.mark.api
def test_assistant_chat_works_and_context_cleaned_after_attached_datasource_deleted(
    assistant,
    assistant_utils,
    datasource_utils,
    attached_file_datasource,
    kb_context,
):
    """
    Deleting a datasource attached to an assistant must neither break
    the assistant nor leave a dangling reference in its context.

    Steps:
    1. Create an assistant with the file datasource in its context.
    2. Delete the datasource.
    3. Fetch the assistant and assert the deleted datasource was detached.
    4. Chat with the assistant and assert a response is returned (no HTTP 500).
    """
    test_assistant = assistant(context=kb_context(attached_file_datasource))

    datasource_utils.delete_datasource(attached_file_datasource)

    refreshed_assistant = assistant_utils.get_assistant_by_id(test_assistant.id)
    context_names = [ctx.name for ctx in refreshed_assistant.context or []]
    assert_that(
        context_names,
        is_not(has_item(attached_file_datasource.name)),
        "Deleted datasource is still attached to the assistant context.",
    )

    response = assistant_utils.ask_assistant(
        refreshed_assistant, "What is in the attached document?"
    )

    assert_that(
        response,
        is_(not_none()),
        "Assistant returned no response after attached datasource deletion.",
    )
    assert_that(
        response,
        is_not(empty()),
        "Assistant returned an empty response after attached datasource deletion.",
    )
