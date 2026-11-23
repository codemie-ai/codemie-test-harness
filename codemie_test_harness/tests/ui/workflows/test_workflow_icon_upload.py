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

"""UI tests for uploading a workflow icon file in the workflow form."""

import pytest
from hamcrest import any_of, assert_that, equal_to, matches_regexp, none

from codemie_test_harness.tests.test_data.workflow_icon_test_data import (
    decode_file_url,
    stored_icon_name_regexp,
    write_jpeg_icon,
    write_oversized_png,
    write_png_icon,
    write_text_file,
)
from codemie_test_harness.tests.ui.pageobject.chats.chat_page import ChatPage
from codemie_test_harness.tests.ui.pageobject.chats.chats_sidebar import ChatsSidebar
from codemie_test_harness.tests.ui.pageobject.workflows.create_workflow_page import (
    CreateWorkflowPage,
)
from codemie_test_harness.tests.ui.pageobject.workflows.edit_workflow_page import (
    EditWorkflowPage,
)
from codemie_test_harness.tests.ui.pageobject.workflows.workflow_details_page import (
    WorkflowDetailsPage,
)
from codemie_test_harness.tests.ui.pageobject.workflows.workflows_page import (
    WorkflowsPage,
)
from codemie_test_harness.tests.ui.test_data.workflow_node_state_settings_test_data import (
    build_simple_assistant_workflow_yaml,
)
from codemie_test_harness.tests.utils.base_utils import wait_for_entity

WORKFLOW_CREATED_TOAST = "Workflow has been created successfully!"
WORKFLOW_UPDATED_TOAST = "Workflow has been updated successfully!"
OVERSIZED_ICON_BYTES = 600 * 1024
SIZE_LIMIT_ERROR = "File size exceeds 512KB limit"
UNSUPPORTED_FILE_ERROR = (
    "Your logo cannot be uploaded. Make sure it meets the requirements and try again."
)


# @case workflow-icon-file-upload_TC_008
@pytest.mark.workflow
@pytest.mark.ui
def test_upload_icon_in_create_form_previews_it_and_shows_it_on_workflow_list(
    page, workflow_utils, default_llm, ui_workflow_name, tmp_path
):
    create_page = CreateWorkflowPage(page)
    create_page.navigate_to()
    config_panel = create_page.open_workflow_config_panel()
    config_panel.switch_to_basic_tab()
    config_panel.fill_name(ui_workflow_name)

    config_panel.upload_icon(write_png_icon(tmp_path))

    config_panel.should_show_icon_preview()
    config_panel.should_have_uploaded_icon_name("png")

    config_panel.click_save()
    yaml_panel = create_page.open_yaml_panel()
    yaml_panel.fill_yaml_config(
        build_simple_assistant_workflow_yaml(default_llm.base_name)
    )
    yaml_panel.click_save()
    create_page.click_save()

    workflows_page = WorkflowsPage(page)
    workflows_page.should_be_on_workflows_page()
    created = wait_for_entity(
        lambda: workflow_utils.client.workflows.list(per_page=200, filter_by_user=True),
        entity_name=ui_workflow_name,
    )
    # A direct goto('/workflows/new') leaves no in-app history entry, so the app returns to
    # /workflows/all after the create (NewWorkflowPage.tsx, goBackWorkflows.ts). Open the
    # 'My workflows' list from the sidebar once the workflow is saved.
    workflows_page.open_my_workflows()
    workflows_page.should_have_url_containing("/workflows/my")
    saved_icon_url = workflow_utils.get_workflow(created.id).icon_url
    assert_that(
        decode_file_url(saved_icon_url),
        matches_regexp(stored_icon_name_regexp("png")),
        "The workflow created in the form must be saved with the uploaded icon file.",
    )

    workflows_page.refresh_page()
    workflows_page.should_see_my_workflows_card(ui_workflow_name)
    workflows_page.should_show_workflow_icon(ui_workflow_name, saved_icon_url)


# @case workflow-icon-file-upload_TC_009
@pytest.mark.workflow
@pytest.mark.ui
def test_icon_can_be_replaced_and_removed_in_edit_form(
    page, workflow_utils, workflow_with_icon, tmp_path
):
    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(workflow_with_icon.id)
    config_panel = edit_page.open_workflow_config_panel()
    config_panel.switch_to_basic_tab()
    config_panel.should_show_icon_preview()

    config_panel.upload_icon(write_jpeg_icon(tmp_path))
    config_panel.should_have_uploaded_icon_name("jpg")
    config_panel.click_save()
    edit_page.click_save()
    edit_page.toast.should_show(WORKFLOW_UPDATED_TOAST)

    assert_that(
        decode_file_url(workflow_utils.get_workflow(workflow_with_icon.id).icon_url),
        matches_regexp(stored_icon_name_regexp("jpg")),
        "The replaced icon must be saved on the workflow.",
    )
    edit_page.navigate_to(workflow_with_icon.id)
    config_panel = edit_page.open_workflow_config_panel()
    config_panel.switch_to_basic_tab()
    config_panel.should_show_icon_preview()
    config_panel.should_have_uploaded_icon_name("jpg")

    config_panel.remove_icon()
    config_panel.should_not_show_icon_preview()
    config_panel.click_save()
    edit_page.click_save()
    edit_page.toast.should_show(WORKFLOW_UPDATED_TOAST)

    assert_that(
        workflow_utils.get_workflow(workflow_with_icon.id).icon_url,
        any_of(none(), equal_to("")),
        "The removed icon must be cleared on the workflow.",
    )
    edit_page.navigate_to(workflow_with_icon.id)
    config_panel = edit_page.open_workflow_config_panel()
    config_panel.switch_to_basic_tab()
    config_panel.should_not_show_icon_preview()
    config_panel.should_have_empty_icon_url_field()


# @case workflow-icon-file-upload_TC_010
@pytest.mark.workflow
@pytest.mark.ui
def test_oversized_or_unsupported_icon_is_rejected_in_form(page, tmp_path):
    create_page = CreateWorkflowPage(page)
    create_page.navigate_to()
    config_panel = create_page.open_workflow_config_panel()
    config_panel.switch_to_basic_tab()
    config_panel.should_have_icon_hint()

    config_panel.upload_icon(write_oversized_png(tmp_path, size=OVERSIZED_ICON_BYTES))
    config_panel.should_show_icon_error(SIZE_LIMIT_ERROR)
    config_panel.should_not_show_icon_preview()

    config_panel.upload_icon(write_text_file(tmp_path))
    config_panel.should_show_icon_error(UNSUPPORTED_FILE_ERROR)
    config_panel.should_not_show_icon_preview()


# @case workflow-icon-file-upload_TC_013
@pytest.mark.workflow
@pytest.mark.ui
def test_uploaded_icon_appears_on_workflow_page_and_in_chat_sidebar(
    page, workflow_with_icon, workflow_conversation_id
):
    details_page = WorkflowDetailsPage(page)
    details_page.navigate_to(workflow_with_icon.id)
    details_page.should_be_on_workflow_details_page()
    details_page.click_configuration()
    details_page.should_show_workflow_icon_in_configuration_sidebar(
        workflow_with_icon.icon_url
    )

    chat_page = ChatPage(page)
    chat_page.navigate_to(workflow_conversation_id)
    sidebar = ChatsSidebar(page)
    # The sidebar renders a chat row's avatar only when the list density is not Compact
    # (ChatListItem.tsx), and Compact is the default (store/chatViewSettings.ts). The density
    # is kept in the browser's local storage, and every test gets its own browser context, so
    # there is nothing to restore. The 'Show workflow runs separately' setting is not touched.
    sidebar.set_chat_list_density("detailed")
    sidebar.should_show_chat_icon(workflow_conversation_id, workflow_with_icon.icon_url)
