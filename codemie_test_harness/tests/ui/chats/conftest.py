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

from operator import methodcaller
from time import sleep

import pytest
from requests import HTTPError

from codemie_sdk.models.conversation import ConversationCreateRequest
from codemie_test_harness.tests.ui.pageobject.assistants.assistants_page import (
    AssistantsPage,
)
from codemie_test_harness.tests.ui.pageobject.chats.chat_page import ChatPage
from codemie_test_harness.tests.ui.test_data.assistant_test_data import (
    AssistantPopUpMessages,
)
from codemie_test_harness.tests.utils.client_factory import get_client


@pytest.fixture(scope="session")
def premium_model_name(client):
    """Display label of the first premium model in the environment.

    Skips the test session when no premium model is configured.
    """
    try:
        models = client.llms.list()
    except HTTPError as exc:
        pytest.skip(f"Could not fetch LLM models: {exc}")
    for model in models:
        if model.is_premium is True:
            return model.label or model.deployment_name
    pytest.skip(
        "No premium model found in this environment — skipping premium UI tests"
    )


@pytest.fixture(scope="session")
def non_premium_model_name(client):
    """Display label of the first enabled non-premium model in the environment."""
    try:
        models = client.llms.list()
    except HTTPError as exc:
        pytest.skip(f"Could not fetch LLM models: {exc}")
    for model in models:
        if model.is_premium is False and model.enabled:
            return model.label or model.deployment_name
    pytest.skip("No non-premium model found in this environment")


@pytest.fixture(scope="function")
def navigate_to_new_chat_page(create_new_conversation):
    def _navigate_to(page):
        chat_id = create_new_conversation.get("id")
        chat_page = ChatPage(page)
        page.set_viewport_size({"width": 1920, "height": 980})
        chat_page.navigate_to(chat_id)
        chat_page.model_selector_button.wait_for(state="visible", timeout=15000)
        return chat_page

    return _navigate_to


@pytest.fixture(scope="function")
def navigate_to_new_chat_page_with_assistant(assistant):
    created_conversation = None

    def _navigate_to(page):
        nonlocal created_conversation
        test_assistant = assistant()
        created_conversation = get_client().conversations.create(
            ConversationCreateRequest(initial_assistant_id=test_assistant.id, folder="")
        )
        chat_id = created_conversation.get("id")
        chat_page = ChatPage(page)
        page.set_viewport_size({"width": 1920, "height": 980})
        chat_page.navigate_to(chat_id)
        chat_page.chat_input.wait_for(state="visible", timeout=15000)
        return chat_page

    yield _navigate_to

    if created_conversation:
        try:
            get_client().conversations.delete(created_conversation.get("id"))
        except HTTPError:
            pass


@pytest.fixture(scope="function")
def chat_with_described_assistant(assistant):
    created_conversation = None
    DESCRIPTION = "Uniquely described assistant for chat intro area verification"

    def _navigate_to(page):
        nonlocal created_conversation
        test_assistant = assistant(description=DESCRIPTION)
        created_conversation = get_client().conversations.create(
            ConversationCreateRequest(initial_assistant_id=test_assistant.id, folder="")
        )
        chat_id = created_conversation.get("id")
        chat_page = ChatPage(page)
        page.set_viewport_size({"width": 1920, "height": 980})
        chat_page.navigate_to(chat_id)
        sleep(5)
        return chat_page, DESCRIPTION

    yield _navigate_to

    if created_conversation:
        try:
            get_client().conversations.delete(created_conversation.get("id"))
        except HTTPError:
            pass


@pytest.fixture(scope="function")
def two_conversations():
    """Create two separate conversations for multi-chat navigation tests.

    Yields:
        tuple[str, str]: (chat_id_a, chat_id_b) — IDs of the two created conversations.
    """
    client = get_client()
    conv_a = client.conversations.create(ConversationCreateRequest(folder=""))
    conv_b = None
    try:
        conv_b = client.conversations.create(ConversationCreateRequest(folder=""))
        yield conv_a.get("id"), conv_b.get("id")
    finally:
        for conv in [c for c in (conv_a, conv_b) if c is not None]:
            try:
                client.conversations.delete(conv.get("id"))
            except Exception:
                pass


@pytest.fixture(scope="function")
def slow_response_conversation(assistant):
    """Conversation with an assistant instructed to answer at length.

    Keeps generation running long enough to reliably land a reload while the
    assistant is still replying.

    Yields:
        str: the created conversation's id.
    """
    test_assistant = assistant(
        system_prompt=(
            "Regardless of what the user says, ignore brevity: respond with a very "
            "detailed, at least 400-word, step-by-step explanation of your reasoning "
            "before giving a short final answer."
        )
    )
    created_conversation = get_client().conversations.create(
        ConversationCreateRequest(initial_assistant_id=test_assistant.id, folder="")
    )
    conversation_id = created_conversation.get("id")

    yield conversation_id

    try:
        get_client().conversations.delete(conversation_id)
    except HTTPError:
        pass


@pytest.fixture(scope="function")
def chat_with_attach_file_disabled(assistant):
    """
    Create an assistant, disable its "Enable file attachments" setting via
    the assistant edit UI, then open a new chat with that assistant.

    Used as the shared precondition for TC_003/TC_005/TC_006:
    "admin has disabled the Attach File setting for the assistant/project".

    Yields:
        callable: ``_navigate_to(page)`` that returns the ChatPage once the
        disabled setting has been saved and the chat has loaded.
    """
    created_conversation = None

    def _navigate_to(page):
        nonlocal created_conversation
        test_assistant = assistant()

        assistants_page = AssistantsPage(page)
        assistants_page.navigate_to()
        assistants_page.search_assistants(test_assistant.name)
        edit_page = assistants_page.click_assistant_edit(test_assistant.name)
        edit_page.toggle_attach_file_setting(enabled=False)
        edit_page.should_have_attach_file_setting_disabled()
        edit_page.click_save()
        assistants_page.should_see_updating_popup(
            AssistantPopUpMessages.ASSISTANT_UPDATED_SUCCESS.value
        )

        created_conversation = get_client().conversations.create(
            ConversationCreateRequest(initial_assistant_id=test_assistant.id, folder="")
        )
        chat_id = created_conversation.get("id")
        chat_page = ChatPage(page)
        page.set_viewport_size({"width": 1920, "height": 980})
        chat_page.navigate_to(chat_id)
        chat_page.chat_input.wait_for(state="visible", timeout=15000)
        return chat_page

    yield _navigate_to

    if created_conversation:
        try:
            get_client().conversations.delete(created_conversation.get("id"))
        except HTTPError:
            pass


def _edit_hide_tool_outputs_flag(page, assistant_name: str, toggle_method: str):
    """Open the assistant's edit form, flip the 'Hide tool outputs' switch with
    ``toggle_method`` (a CreateEditAssistantPage method name) and save."""
    assistants_page = AssistantsPage(page)
    assistants_page.navigate_to()
    assistants_page.search_assistants(assistant_name)
    edit_page = assistants_page.click_assistant_edit(assistant_name)
    # The form must be populated before the switch is touched, or loading the
    # stored values could overwrite the click.
    edit_page.should_have_name_value(assistant_name)
    methodcaller(toggle_method)(edit_page)
    edit_page.click_save()
    assistants_page.should_see_updating_popup(
        AssistantPopUpMessages.ASSISTANT_UPDATED_SUCCESS.value
    )


@pytest.fixture(scope="function")
def enable_hide_tool_outputs_on_assistant(page):
    """Callable ``(assistant_name)`` that turns the assistant-level 'Hide tool outputs
    from end users' flag ON through the edit form.

    The SDK AssistantCreateRequest has no hide_tool_outputs field, so the UI is the
    only way to set it. The assistant itself is cleaned up by its own fixture.
    """

    def _enable(assistant_name: str):
        _edit_hide_tool_outputs_flag(
            page, assistant_name, "enable_hide_tool_outputs_setting"
        )

    return _enable


@pytest.fixture(scope="function")
def disable_hide_tool_outputs_on_assistant(page):
    """Callable ``(assistant_name)`` that turns the assistant-level flag OFF through the
    edit form."""

    def _disable(assistant_name: str):
        _edit_hide_tool_outputs_flag(
            page, assistant_name, "disable_hide_tool_outputs_setting"
        )

    return _disable
