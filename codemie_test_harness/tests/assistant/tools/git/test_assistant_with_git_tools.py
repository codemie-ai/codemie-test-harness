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
from hamcrest import assert_that, equal_to, not_none

from codemie_test_harness.tests.test_data.git_tools_test_data import (
    list_branches_set_active_branch_test_data,
    create_branch_test_data,
    create_file_test_data,
    create_merge_request_test_data,
    delete_file_test_data,
    get_merge_request_changes_test_data,
    update_file_test_data,
)
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    to_camel_case,
    assert_tool_triggered,
)


@pytest.mark.github
@pytest.mark.requires_capability("retrieval")
@pytest.mark.assistant
@pytest.mark.gitlab
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit,tool_name,prompt,expected_response",
    list_branches_set_active_branch_test_data,
    ids=[
        f"{getattr(row, 'values', row)[0]}_{getattr(row, 'values', row)[1]}"
        for row in list_branches_set_active_branch_test_data
    ],
)
def test_assistant_with_list_branch_set_active_branch_tools(
    assistant_utils,
    assistant,
    code_datasource,
    code_context,
    git_utils,
    gitlab_integration,
    similarity_check,
    toolkit,
    tool_name,
    prompt,
    expected_response,
):
    assistant = assistant(
        toolkit,
        tool_name,
        context=code_context(code_datasource),
        settings=gitlab_integration,
    )
    response, triggered_tools = assistant_utils.ask_assistant(
        assistant, prompt, minimal_response=False
    )
    assert_tool_triggered(tool_name, triggered_tools)
    similarity_check.check_similarity(response, expected_response)


@pytest.mark.github
@pytest.mark.requires_capability("retrieval")
@pytest.mark.assistant
@pytest.mark.gitlab
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit,tool_name,prompt_template,expected_template",
    create_branch_test_data,
    ids=[
        f"{getattr(row, 'values', row)[0]}_{getattr(row, 'values', row)[1]}"
        for row in create_branch_test_data
    ],
)
def test_assistant_with_create_branch_tool(
    assistant_utils,
    assistant,
    code_datasource,
    code_context,
    git_utils,
    gitlab_integration,
    similarity_check,
    toolkit,
    tool_name,
    prompt_template,
    expected_template,
):
    branch_name = get_random_name()
    try:
        prompt = prompt_template(branch_name)
        expected = expected_template(branch_name)

        assistant = assistant(
            toolkit,
            tool_name,
            context=code_context(code_datasource),
            settings=gitlab_integration,
        )
        response, triggered_tools = assistant_utils.ask_assistant(
            assistant, prompt, minimal_response=False
        )
        assert_tool_triggered(tool_name, triggered_tools)

        assert_that(
            git_utils.branch_exists(branch_name),
            equal_to(True),
            f"Branch {branch_name} was not created",
        )
        similarity_check.check_similarity(response, expected)

    finally:
        if git_utils.branch_exists(branch_name):
            git_utils.delete_branch(branch_name)


@pytest.mark.github
@pytest.mark.requires_capability("retrieval")
@pytest.mark.assistant
@pytest.mark.gitlab
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit,tool_name,prompt_template,expected_template,expected_content_template",
    create_file_test_data,
    ids=[
        f"{getattr(row, 'values', row)[0]}_{getattr(row, 'values', row)[1]}"
        for row in create_file_test_data
    ],
)
def test_assistant_with_create_file_tool(
    assistant_utils,
    assistant,
    code_context,
    code_datasource,
    git_utils,
    gitlab_integration,
    similarity_check,
    toolkit,
    tool_name,
    prompt_template,
    expected_template,
    expected_content_template,
):
    class_name = to_camel_case(get_random_name())
    file_name = f"{class_name}.java"

    try:
        prompt = prompt_template(class_name)
        expected = expected_template(class_name)
        expected_content = expected_content_template(class_name)

        assistant = assistant(
            toolkit,
            tool_name,
            context=code_context(code_datasource),
            settings=gitlab_integration,
        )
        response, triggered_tools = assistant_utils.ask_assistant(
            assistant, prompt, minimal_response=False
        )
        assert_tool_triggered(tool_name, triggered_tools)

        file_content = git_utils.get_file_content(file_name, "main")

        similarity_check.check_similarity(response, expected)
        similarity_check.check_similarity(file_content, expected_content)

    finally:
        if git_utils.file_exists(file_name, "main"):
            git_utils.delete_file(file_name, "main")


@pytest.mark.github
@pytest.mark.requires_capability("retrieval")
@pytest.mark.assistant
@pytest.mark.gitlab
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit,tool_name,prompt_template,expected_template",
    create_merge_request_test_data,
    ids=[
        f"{getattr(row, 'values', row)[0]}_{getattr(row, 'values', row)[1]}"
        for row in create_merge_request_test_data
    ],
)
def test_assistant_with_create_merge_request_tool(
    assistant_utils,
    assistant,
    code_context,
    code_datasource,
    git_utils,
    gitlab_integration,
    similarity_check,
    toolkit,
    tool_name,
    prompt_template,
    expected_template,
):
    source_branch = get_random_name()
    class_name = to_camel_case(get_random_name())
    mr_name = get_random_name()

    try:
        prompt = prompt_template(source_branch, class_name, mr_name)

        assistant = assistant(
            toolkit,
            tool_name,
            context=code_context(code_datasource),
            settings=gitlab_integration,
        )
        response, triggered_tools = assistant_utils.ask_assistant(
            assistant, prompt, minimal_response=False
        )
        assert_tool_triggered(tool_name, triggered_tools)
        mr_id = git_utils.get_merge_request_id_by_title(mr_name)

        expected = expected_template(source_branch, mr_name, mr_id)
        similarity_check.check_similarity(response, expected)
    finally:
        if git_utils.branch_exists(source_branch):
            git_utils.delete_branch(source_branch)


@pytest.mark.github
@pytest.mark.requires_capability("retrieval")
@pytest.mark.assistant
@pytest.mark.gitlab
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit,tool_name,prompt_template,expected_template,file_content_template",
    delete_file_test_data,
    ids=[
        f"{getattr(row, 'values', row)[0]}_{getattr(row, 'values', row)[1]}"
        for row in delete_file_test_data
    ],
)
def test_assistant_with_delete_file_tool(
    assistant,
    code_context,
    code_datasource,
    git_utils,
    gitlab_integration,
    datasource_utils,
    assistant_utils,
    similarity_check,
    toolkit,
    tool_name,
    prompt_template,
    expected_template,
    file_content_template,
):
    class_name = to_camel_case(get_random_name())
    file_name = f"{class_name}.java"
    file_content = file_content_template(class_name)

    try:
        git_utils.create_file(file_name, "main", file_content)

        assert_that(
            git_utils.file_exists(file_name, "main"),
            equal_to(True),
            f"File {file_name} was not created",
        )

        datasource_utils.update_code_datasource(
            code_datasource.id, full_reindex=True, skip_reindex=False
        )

        prompt = prompt_template(class_name)
        expected = expected_template(class_name)

        assistant = assistant(
            toolkit,
            tool_name,
            context=code_context(code_datasource),
            settings=gitlab_integration,
        )
        response, triggered_tools = assistant_utils.ask_assistant(
            assistant, prompt, minimal_response=False
        )
        assert_tool_triggered(tool_name, triggered_tools)

        assert_that(
            git_utils.file_exists(file_name, "main"),
            equal_to(False),
            f"File {file_name} was not deleted",
        )

        similarity_check.check_similarity(response, expected)
    finally:
        if git_utils.file_exists(file_name, "main"):
            git_utils.delete_file(file_name, "main")


@pytest.mark.github
@pytest.mark.requires_capability("retrieval")
@pytest.mark.assistant
@pytest.mark.gitlab
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit,tool_name,create_mr_prompt_template,create_mr_expected_template,get_mr_changes_prompt_template,get_mr_changes_expected_template",
    get_merge_request_changes_test_data,
    ids=[
        f"{getattr(row, 'values', row)[0]}_{getattr(row, 'values', row)[1]}"
        for row in get_merge_request_changes_test_data
    ],
)
def test_assistant_with_get_merge_request_changes_tool(
    assistant_utils,
    assistant,
    code_context,
    code_datasource,
    git_utils,
    gitlab_integration,
    similarity_check,
    toolkit,
    tool_name,
    create_mr_prompt_template,
    create_mr_expected_template,
    get_mr_changes_prompt_template,
    get_mr_changes_expected_template,
):
    source_branch = get_random_name()
    class_name = to_camel_case(get_random_name())
    mr_name = get_random_name()

    try:
        assistant = assistant(
            toolkit,
            tool_name,
            context=code_context(code_datasource),
            settings=gitlab_integration,
        )

        create_mr_prompt = create_mr_prompt_template(source_branch, class_name, mr_name)

        response, triggered_tools = assistant_utils.ask_assistant(
            assistant, create_mr_prompt, minimal_response=False
        )
        assert_tool_triggered(tool_name[:-1], triggered_tools)
        mr_id = git_utils.get_merge_request_id_by_title(mr_name)

        create_mr_expected = create_mr_expected_template(source_branch, mr_name, mr_id)
        similarity_check.check_similarity(response, create_mr_expected)

        assert_that(
            mr_id, not_none(), f"Merge request with title {mr_name} was not found"
        )

        get_changes_prompt = get_mr_changes_prompt_template(mr_id)
        get_changes_expected = get_mr_changes_expected_template(class_name)

        response, triggered_tools = assistant_utils.ask_assistant(
            assistant, get_changes_prompt, minimal_response=False
        )
        assert_tool_triggered(tool_name[-1], triggered_tools)
        similarity_check.check_similarity(response, get_changes_expected)
    finally:
        if git_utils.branch_exists(source_branch):
            git_utils.delete_branch(source_branch)


@pytest.mark.github
@pytest.mark.requires_capability("retrieval")
@pytest.mark.assistant
@pytest.mark.gitlab
@pytest.mark.api
@pytest.mark.parametrize(
    "toolkit,tool_name,create_prompt_template,create_expected_template,created_content_template,update_prompt_template,update_expected_template,updated_content_template",
    update_file_test_data,
    ids=[
        f"{getattr(row, 'values', row)[0]}_{getattr(row, 'values', row)[1]}"
        for row in update_file_test_data
    ],
)
def test_assistant_with_update_file_tools(
    assistant_utils,
    assistant,
    code_context,
    code_datasource,
    git_utils,
    gitlab_integration,
    datasource_utils,
    similarity_check,
    toolkit,
    tool_name,
    create_prompt_template,
    create_expected_template,
    created_content_template,
    update_prompt_template,
    update_expected_template,
    updated_content_template,
):
    class_name = to_camel_case(get_random_name())
    file_name = f"{class_name}.java"

    try:
        assistant = assistant(
            toolkit,
            tool_name,
            context=code_context(code_datasource),
            settings=gitlab_integration,
        )

        create_prompt = create_prompt_template(class_name)
        response, create_triggered_tools = assistant_utils.ask_assistant(
            assistant, create_prompt, minimal_response=False
        )
        assert_tool_triggered(tool_name[0], create_triggered_tools)

        create_expected = create_expected_template(class_name)
        similarity_check.check_similarity(response, create_expected)

        actual_file_content = git_utils.get_file_content(file_name)
        similarity_check.check_similarity(
            actual_file_content, created_content_template(class_name), 80
        )

        datasource_utils.update_code_datasource(
            code_datasource.id, full_reindex=True, skip_reindex=False
        )

        update_prompt = update_prompt_template(class_name)
        response, update_triggered_tools = assistant_utils.ask_assistant(
            assistant, update_prompt, minimal_response=False
        )
        assert_tool_triggered(tool_name[1], update_triggered_tools)

        update_expected = update_expected_template(class_name)
        similarity_check.check_similarity(response, update_expected)

        actual_file_content = git_utils.get_file_content(file_name)
        similarity_check.check_similarity(
            actual_file_content, updated_content_template(class_name), 80
        )

    finally:
        if git_utils.file_exists(file_name, "main"):
            git_utils.delete_file(file_name, "main")
