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

"""Shared fixtures for workflow UI tests."""

import logging

import pytest
from codemie_sdk.models.workflow import WorkflowMode
from hamcrest import assert_that, greater_than

from codemie_test_harness.tests.ui import conversation_ids
from codemie_test_harness.tests.ui.pageobject.chats.chat_page import ChatPage
from codemie_test_harness.tests.ui.pageobject.workflows import WorkflowDetailsPage
from codemie_test_harness.tests.ui.test_data.workflow_node_state_settings_test_data import (
    build_node_workflow_yaml,
    build_simple_assistant_workflow_yaml,
    NodeKind,
)
from codemie_test_harness.tests.ui.test_data.workflows_test_data import (
    MAX_UI_CATEGORIES,
    WorkflowCategoriesUiDataFactory,
)
from codemie_sdk.models.assistant import ToolKitDetails, ToolDetails

from codemie_test_harness.tests.enums.tools import Toolkit, ProjectManagementTool
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.yaml_utils import (
    AssistantModel,
    StateModel,
    WorkflowYamlModel,
    prepare_yaml_content,
)

logger = logging.getLogger(__name__)


ASSISTANT_AND_STATE_NAME = "branch_creator"


@pytest.fixture
def clear_workflow_ai_popup(page):
    """Remove the workflow AI popup suppression so the modal appears for tests that verify it.

    The popup-dismissal flag is user-scoped (``<userId>_codemie-new-workflow-ai-popup``)
    and is pre-seeded to 'false' by the autouse ``login`` fixture (tests/ui/conftest.py)
    via ``page.add_init_script``, which re-runs on every subsequent navigation. Removing
    the key with ``page.evaluate`` only clears it once, before the test's own navigation
    to the workflow page re-runs login's init script and re-suppresses the popup. Using
    ``page.add_init_script`` here (mirroring ``clear_asst_ai_popup`` in
    tests/ui/assistants/conftest.py) registers a second script that removes the key on
    every navigation, after login's script has already re-set it.
    """
    user_id = get_client().users.about_me().user_id
    page.add_init_script(
        f"localStorage.removeItem('{user_id}_codemie-new-workflow-ai-popup');"
    )
    yield


@pytest.fixture
def cleanup_generated_workflow(workflow_utils):
    """Delete AI-generated workflows saved via the UI during a test.

    Tests that exercise the full "generate -> edit -> save" round trip create a
    real, persisted workflow. Since the generated name isn't known up front
    (it comes from the LLM), the test registers the actual name once known and
    this fixture deletes it by name in teardown.
    """
    tracked_names = []

    def _track(name: str):
        tracked_names.append(name)

    yield _track

    for name in tracked_names:
        try:
            match = None
            page_num = 0
            while True:
                workflows_page = get_client().workflows.list(
                    page=page_num, per_page=200, filter_by_user=True
                )
                if not workflows_page:
                    break
                match = next((w for w in workflows_page if w.name == name), None)
                if match or len(workflows_page) < 200:
                    break
                page_num += 1
            if match:
                workflow_utils.delete_workflow(match)
        except Exception:
            pass


@pytest.fixture(scope="function")
def test_workflow_with_description(workflow_utils, default_llm):
    """Create a test workflow with a unique description.

    Yields a ``(workflow, description_text)`` tuple so tests can assert the
    exact description string that was stored on the workflow.

    Teardown: deletes the created workflow via the API.
    """
    description_text = f"Test workflow description {get_random_name()}"

    assistant = AssistantModel(
        id=ASSISTANT_AND_STATE_NAME,
        model=default_llm.base_name,
        system_prompt="You are helpful assistant",
    )
    state = StateModel(
        id=ASSISTANT_AND_STATE_NAME,
        assistant_id=ASSISTANT_AND_STATE_NAME,
    )
    workflow_yaml = WorkflowYamlModel(
        assistants=[assistant],
        states=[state],
    )
    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))

    created_workflow = workflow_utils.create_workflow(
        workflow_name=get_random_name(),
        workflow_type=WorkflowMode.SEQUENTIAL,
        shared=True,
        workflow_yaml=yaml_content,
        description=description_text,
    )
    workflow = workflow_utils.get_workflow(created_workflow.id)
    yield workflow, description_text
    try:
        workflow_utils.delete_workflow(workflow)
    except Exception:
        pass


@pytest.fixture(scope="function")
def workflow_with_real_assistant(
    assistant_factory, workflow_with_assistant, jira_integration
):
    """Create a workflow with a real API-registered Jira assistant shared with the project.

    The assistant is created with ``shared=True`` so the workflow canvas node panel
    shows the 'Your Integration Settings' section.  Without
    ``shared=True`` the UI hides the integration-select section even when the
    assistant has user-selectable slots.

    ``jira_integration`` guarantees the user owns a Jira integration: without one,
    assistant creation fails validation ("missing integrations") and the panel
    renders an 'Add Integration' button instead of the selection dropdown.

    Used by S01-S05 and S13.

    Cleanup: ``assistant_factory`` teardown deletes the assistant; the
    ``workflow_with_assistant`` fixture teardown deletes the workflow. User-mapping
    rows are keyed on (assistant_id, user_id, workflow_id), so they go with the
    assistant — no separate mapping teardown is needed, and none is possible:
    DELETE /v1/assistants/{id}/users/mapping returns 405 Method Not Allowed.

    Yields:
        Tuple of (workflow_obj, real_assistant).
        ``real_assistant.name`` is the React Flow node ID to pass to
        ``open_assistant_node_panel()``.
    """
    toolkits = [
        ToolKitDetails(
            toolkit=Toolkit.PROJECT_MANAGEMENT,
            tools=[ToolDetails(name=ProjectManagementTool.JIRA)],
        )
    ]
    real_assistant = assistant_factory.create(toolkits=toolkits, shared=True)
    workflow_obj = workflow_with_assistant(
        real_assistant, "Use Jira to help with tasks"
    )
    yield workflow_obj, real_assistant


@pytest.fixture(scope="function")
def test_workflow(workflow_utils, default_llm):
    """Create a test workflow for UI tests."""
    assistant = AssistantModel(
        id=ASSISTANT_AND_STATE_NAME,
        model=default_llm.base_name,
        system_prompt="You are helpful assistant",
    )

    state = StateModel(
        id=ASSISTANT_AND_STATE_NAME,
        assistant_id=ASSISTANT_AND_STATE_NAME,
    )

    workflow_yaml = WorkflowYamlModel(
        assistants=[assistant],
        states=[state],
    )

    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))

    # Create workflow using the workflow_utils fixture
    created_workflow = workflow_utils.create_workflow(
        workflow_name=get_random_name(),
        workflow_type=WorkflowMode.SEQUENTIAL,
        shared=True,
        workflow_yaml=yaml_content,
    )
    workflow = workflow_utils.get_workflow(created_workflow.id)
    yield workflow
    try:
        workflow_utils.delete_workflow(workflow)
    except Exception as e:
        logger.warning(f"Failed to delete workflow {workflow.id}: {e}")


_PAGINATION_MIN_WORKFLOWS = (
    13  # needs > 12 to trigger pagination (default page size 12)
)


@pytest.fixture
def ensure_enough_workflows(workflow_utils, default_llm):
    """Ensure at least 13 workflows exist so pagination is visible; delete created ones after."""
    existing = get_client().workflows.list(per_page=200)
    need = max(0, _PAGINATION_MIN_WORKFLOWS - len(existing))
    created = []
    for _ in range(need):
        assistant = AssistantModel(
            id=ASSISTANT_AND_STATE_NAME,
            model=default_llm.base_name,
            system_prompt="You are helpful assistant",
        )
        state = StateModel(
            id=ASSISTANT_AND_STATE_NAME, assistant_id=ASSISTANT_AND_STATE_NAME
        )
        yaml_content = prepare_yaml_content(
            WorkflowYamlModel(assistants=[assistant], states=[state]).model_dump(
                exclude_none=True
            )
        )
        created.append(
            workflow_utils.create_workflow(
                workflow_name=get_random_name(),
                workflow_type=WorkflowMode.SEQUENTIAL,
                shared=True,
                workflow_yaml=yaml_content,
            )
        )
    yield
    for wf in created:
        try:
            workflow_utils.delete_workflow(wf)
        except Exception as e:
            logger.warning(f"Failed to delete workflow {wf.id}: {e}")


@pytest.fixture
def ensure_workflow_exists(workflow_utils, default_llm):
    """Ensure at least one workflow exists before the test; delete it in teardown if created."""
    existing = get_client().workflows.list(per_page=1, filter_by_user=True)
    if existing:
        yield
        return

    assistant = AssistantModel(
        id=ASSISTANT_AND_STATE_NAME,
        model=default_llm.base_name,
        system_prompt="You are helpful assistant",
    )
    state = StateModel(
        id=ASSISTANT_AND_STATE_NAME, assistant_id=ASSISTANT_AND_STATE_NAME
    )
    yaml_content = prepare_yaml_content(
        WorkflowYamlModel(assistants=[assistant], states=[state]).model_dump(
            exclude_none=True
        )
    )
    created = workflow_utils.create_workflow(
        workflow_name=get_random_name(),
        workflow_type=WorkflowMode.SEQUENTIAL,
        shared=True,
        workflow_yaml=yaml_content,
    )
    yield
    workflow_utils.delete_workflow(created)


@pytest.fixture(scope="module")
def workflow_categories(categories_utils):
    """Existing categories (never created or deleted by the tests).

    Needs MAX_UI_CATEGORIES + 1 so the UI limit can be exceeded with a 4th one.
    """
    categories = categories_utils.get_categories()
    assert_that(
        len(categories),
        greater_than(MAX_UI_CATEGORIES),
        "Environment must have at least 4 categories",
    )
    return categories


@pytest.fixture(scope="function")
def categorized_workflows(workflow_utils, default_llm, workflow_categories):
    """Two shared workflows, one with a category and one without.

    Yields ``(data, category)`` where ``data`` holds the workflow names (common
    search prefix) and ``category`` is the one assigned to the first workflow.

    Teardown: deletes both workflows via the API.
    """
    data = WorkflowCategoriesUiDataFactory.create()
    category = workflow_categories[0]
    assistant = AssistantModel(
        id=ASSISTANT_AND_STATE_NAME,
        model=default_llm.base_name,
        system_prompt="You are helpful assistant",
    )
    state = StateModel(
        id=ASSISTANT_AND_STATE_NAME, assistant_id=ASSISTANT_AND_STATE_NAME
    )
    yaml_content = prepare_yaml_content(
        WorkflowYamlModel(assistants=[assistant], states=[state]).model_dump(
            exclude_none=True
        )
    )
    created = []
    try:
        for name, categories in (
            (data.with_category_name, [category.id]),
            (data.without_category_name, None),
        ):
            created.append(
                workflow_utils.create_workflow(
                    workflow_name=name,
                    workflow_type=WorkflowMode.SEQUENTIAL,
                    shared=True,
                    workflow_yaml=yaml_content,
                    categories=categories,
                )
            )
        yield data, category
    finally:
        for workflow in created:
            try:
                workflow_utils.delete_workflow(workflow)
            except Exception as e:
                logger.warning(f"Failed to delete workflow {workflow.id}: {e}")


@pytest.fixture(scope="function")
def conversation_linked_execution(test_workflow, conversation_utils, workflow_utils):
    """Create a conversation and a workflow execution linked to it via ``conversation_id``.

    Used to reproduce the case: while the conversation exists, the linked
    execution's deletion must remain blocked; once the conversation is deleted,
    the execution is automatically removed and no longer lingers as an
    orphaned, permanently-blocked history entry.

    Yields a ``(conversation_id, execution)`` tuple. Teardown best-effort deletes
    the conversation (it may already have been deleted by the test itself) and
    the execution (it may already have been deleted by the test itself).
    """
    created_conv = conversation_utils.create_conversation(
        initial_assistant_id=test_workflow.id,
        is_workflow_conversation=True,
    )
    conversation_id = created_conv["id"]
    execution = workflow_utils.create_workflow_execution(
        workflow_id=test_workflow.id,
        user_input=f"Say hello {get_random_name()}",
        conversation_id=conversation_id,
    )
    yield conversation_id, execution
    try:
        conversation_utils.delete_conversation(conversation_id)
    except Exception:
        pass
    try:
        workflow_utils.delete_workflow_execution(
            test_workflow.id, execution.execution_id
        )
    except Exception:
        pass


@pytest.fixture(scope="function")
def executions(test_workflow, workflow_utils):
    """Create test executions for the workflow."""

    def _create_executions(num_executions=3):
        for _ in range(num_executions):
            workflow_utils.execute_workflow(
                workflow=test_workflow.id,
                execution_name=ASSISTANT_AND_STATE_NAME,
                user_input="Hello, please provide a greeting",
            )
        return workflow_utils.get_executions(test_workflow)

    return _create_executions


@pytest.fixture(scope="function")
def workflow_chat_reloaded_mid_execution(page, workflow_utils, default_llm):
    """Repro fixture (AC-4): open a workflow chat, send "hi", and
    reload the page while the execution is still running.

    Yields a ``(chat_page, chat_id)`` tuple, already positioned right after the
    reload — the exact moment the fix (GET-conversation hydrate + poll resume) is
    meant to restore workflow progress instead of an empty answer node.

    Teardown: waits for the triggered execution to finish (best-effort, bounded)
    before deleting the workflow; the conversation itself is cleaned up by the
    session-level ``conversation_ids`` sweep in ``tests/ui/conftest.py``.
    """
    # Two sequential long-form steps so the run stays IN_PROGRESS for long enough
    # (well beyond a page reload's round trip) regardless of the user's own message
    # ("hi") — each state is instructed to produce a lengthy response to buy a
    # comfortable, non-flaky window for the mid-run reload repro.
    long_response_instruction = (
        "Regardless of what the user says, ignore brevity: respond with a very "
        "detailed, at least 300-word, step-by-step explanation of your reasoning "
        "before giving a short final answer."
    )
    first_state_id = f"{ASSISTANT_AND_STATE_NAME}_1"
    second_state_id = f"{ASSISTANT_AND_STATE_NAME}_2"
    first_assistant = AssistantModel(
        id=first_state_id,
        model=default_llm.base_name,
        system_prompt=f"You are a helpful assistant. {long_response_instruction}",
    )
    second_assistant = AssistantModel(
        id=second_state_id,
        model=default_llm.base_name,
        system_prompt=f"You are a helpful assistant. {long_response_instruction}",
    )
    first_state = StateModel(
        id=first_state_id,
        assistant_id=first_state_id,
        next={"state_id": second_state_id},
    )
    second_state = StateModel(id=second_state_id, assistant_id=second_state_id)
    workflow_yaml = WorkflowYamlModel(
        assistants=[first_assistant, second_assistant],
        states=[first_state, second_state],
    )
    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))

    created_workflow = workflow_utils.create_workflow(
        workflow_name=get_random_name(),
        workflow_type=WorkflowMode.SEQUENTIAL,
        shared=True,
        workflow_yaml=yaml_content,
    )
    workflow = workflow_utils.get_workflow(created_workflow.id)

    details_page = WorkflowDetailsPage(page)
    details_page.navigate_to(workflow.id)
    details_page.click_run_chat()

    chat_page = ChatPage(page)
    chat_page.should_have_chat_input_visible()

    chat_page.send_message("hi")
    chat_page.wait_for_generation_to_start()

    # The conversation is only created once the first message is sent — the URL
    # still shows the empty "/chats" route beforehand (mirrors start_new_chat()).
    chat_id = chat_page.get_id_from_url(chat_page.evaluate_current_url())
    chat_page.chat_id = chat_id
    conversation_ids.append(chat_id)

    execution = workflow_utils.wait_for_executions(workflow)[0]

    page.reload()
    page.wait_for_load_state("networkidle")

    yield chat_page, chat_id

    try:
        workflow_utils.wait_for_completion(
            service=workflow_utils.client.workflows.executions(workflow.id),
            _id=execution.execution_id,
            timeout=60,
        )
    except Exception:
        pass
    try:
        workflow_utils.delete_workflow(workflow)
    except Exception:
        pass


@pytest.fixture(scope="function")
def slow_response_workflow(workflow_utils, default_llm):
    """Single-step workflow instructed to answer at length.

       Used to keep a workflow execution genuinely IN_PROGRESS for several seconds —
       a wide enough window to reliably observe the state via a live GET/UI check
    without racing a fast, near-instant LLM reply.
    """
    assistant = AssistantModel(
        id=ASSISTANT_AND_STATE_NAME,
        model=default_llm.base_name,
        system_prompt=(
            "You are a helpful assistant. Regardless of what the user says, ignore "
            "brevity: respond with a very detailed, at least 400-word, step-by-step "
            "explanation of your reasoning before giving a short final answer."
        ),
    )
    state = StateModel(
        id=ASSISTANT_AND_STATE_NAME, assistant_id=ASSISTANT_AND_STATE_NAME
    )
    workflow_yaml = WorkflowYamlModel(assistants=[assistant], states=[state])
    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))

    created_workflow = workflow_utils.create_workflow(
        workflow_name=get_random_name(),
        workflow_type=WorkflowMode.SEQUENTIAL,
        shared=True,
        workflow_yaml=yaml_content,
    )
    workflow = workflow_utils.get_workflow(created_workflow.id)
    yield workflow
    try:
        workflow_utils.delete_workflow(workflow)
    except Exception:
        pass


@pytest.fixture(scope="function")
def create_node_workflow(workflow_utils, default_llm):
    """Factory creating a workflow with one node (state ``NODE_STATE_ID``) of a chosen kind.

    For ``NodeKind.SUB_WORKFLOW`` the factory first creates a minimal target workflow
    to call. Created workflows are deleted on teardown, the calling workflow before
    its sub-workflow target.

    Usage: ``create_node_workflow(NodeKind.CUSTOM, CustomNodeType.STATE_PROCESSOR)``;
    see ``build_node_workflow_yaml`` for the keyword options.
    """
    created = []

    def _create_workflow(workflow_yaml):
        created_workflow = workflow_utils.create_workflow(
            workflow_name=get_random_name(),
            workflow_type=WorkflowMode.SEQUENTIAL,
            shared=True,
            workflow_yaml=workflow_yaml,
        )
        workflow = workflow_utils.get_workflow(created_workflow.id)
        created.append(workflow)
        return workflow

    def _create(node_kind, custom_node_type=None, **yaml_options):
        sub_workflow_id = None
        if node_kind == NodeKind.SUB_WORKFLOW:
            target = _create_workflow(
                build_simple_assistant_workflow_yaml(default_llm.base_name)
            )
            sub_workflow_id = target.id
        return _create_workflow(
            build_node_workflow_yaml(
                default_llm.base_name,
                node_kind,
                custom_node_type=custom_node_type,
                sub_workflow_id=sub_workflow_id,
                **yaml_options,
            )
        )

    yield _create

    for workflow in reversed(created):
        try:
            workflow_utils.delete_workflow(workflow)
        except Exception as e:
            logger.warning(f"Failed to delete workflow {workflow.id}: {e}")
