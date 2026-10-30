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

"""Image domain allow-list security tests.

Images in LLM-generated Markdown are only loaded from trusted domains. Blocked
images display a "blocked" badge instead of being silently omitted, and never
reach the DOM as an <img src="..."> that would trigger a network request to the
untrusted host.

Implementation (codemie-ui):
- src/utils/imageAllowList.ts: isImageAllowed() decides per-URL. Always allowed:
  data:image/*, same-origin, backend-origin (GET /v1/config -> BASE_URL), and any
  hostname on the configurable allow-list (GET /v1/config -> allowedImageDomains).
  Blocked: non-HTTPS (except localhost dev), unparseable URLs, blank src, and any
  hostname not on the allow-list.
- src/components/markdown/Markdown.sanitize.ts: a DOMPurify hook rewrites every
  blocked <img> (and src/srcset/poster/background attribute) into a
  BlockedImageBadge span (class "blocked-image-badge",
  data-blocked-image-hostname="<host>") instead of leaving the element in the DOM —
  so the browser never issues the request in the first place.

These tests create real conversations through the SDK and inject controlled
Markdown payloads directly into the conversation history (via upsert_history),
simulating assistant responses. This exercises the real, shipped rendering/sanitize
pipeline without depending on a live LLM to literally echo image markdown.
"""

import os
from datetime import datetime

import pytest
from requests import HTTPError

from codemie_sdk.models.conversation import HistoryItem
from codemie_test_harness.tests.ui.pageobject.chats.chat_page import ChatPage
from codemie_test_harness.tests.utils.client_factory import get_client

_DATA_URL_PNG = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


@pytest.fixture
def chat_with_markdown_reply(assistant, conversation_utils):
    """Create a real conversation and inject controlled Markdown as an assistant reply
    via the SDK's upsert_history method. This exercises the real rendering pipeline
    without depending on a live LLM to literally echo image markdown.
    """
    test_assistant = assistant()
    created_conversation = conversation_utils.create_conversation(
        initial_assistant_id=test_assistant.id
    )
    conversation_id = created_conversation.get("id")

    def _open(page, markdown: str) -> ChatPage:
        # Inject a user message and assistant reply into the real conversation history
        user_message = HistoryItem(
            role="User",
            message="show me images",
            messageRaw="<p>show me images</p>",
            historyIndex=0,
            date=datetime.now(),
            fileNames=[],
        )
        assistant_reply = HistoryItem(
            role="Assistant",
            message=markdown,
            historyIndex=0,
            date=datetime.now(),
            fileNames=[],
        )

        conversation_utils.upsert_history(
            conversation_id=conversation_id,
            history=[user_message, assistant_reply],
            assistant_id=test_assistant.id,
        )

        # Navigate to the conversation in the UI and verify the response renders
        chat_page = ChatPage(page)
        chat_page.navigate_to(conversation_id)
        chat_page.should_have_non_blank_assistant_response()
        return chat_page

    yield _open

    try:
        get_client().conversations.delete(conversation_id)
    except HTTPError:
        pass


@pytest.mark.ui
@pytest.mark.sanity
@pytest.mark.prod_regression
def test_blocked_image_shows_badge_not_img_tag(page, chat_with_markdown_reply):
    """Images from a domain outside the allow-list render as a blocked-image badge,
    not an <img> tag — so the browser never requests the untrusted host.
    """
    markdown = "Here is an image: ![test](https://attacker.evil-example.com/image.jpg)"

    chat_page = chat_with_markdown_reply(page, markdown)

    chat_page.should_have_blocked_image_badge_count(1)
    chat_page.should_have_blocked_image_badge_hostname("attacker.evil-example.com")
    chat_page.should_not_have_assistant_image_with_src_containing("attacker")


@pytest.mark.ui
@pytest.mark.sanity
@pytest.mark.prod_regression
def test_data_url_image_renders_without_badge(page, chat_with_markdown_reply):
    """A data:image/* URL never issues a network request, so it is always allowed —
    it renders as a real <img>, with no blocked-image badge.
    """
    markdown = f"Inline image: ![test]({_DATA_URL_PNG})"

    chat_page = chat_with_markdown_reply(page, markdown)

    chat_page.should_have_assistant_data_url_image()
    chat_page.should_have_blocked_image_badge_count(0)


@pytest.mark.ui
@pytest.mark.sanity
@pytest.mark.prod_regression
def test_non_https_external_url_is_blocked(page, chat_with_markdown_reply):
    """A plain http:// URL to an external host is blocked (only https: is accepted
    outright; http: is only safe from a localhost page) — shown as a badge, no <img>.
    """
    markdown = "Insecure image: ![test](http://example.com/image.jpg)"

    chat_page = chat_with_markdown_reply(page, markdown)

    chat_page.should_have_blocked_image_badge_count(1)
    chat_page.should_not_have_assistant_image_with_src_containing("example.com")


@pytest.mark.ui
@pytest.mark.sanity
@pytest.mark.prod_regression
def test_https_backend_origin_image_renders(page, chat_with_markdown_reply):
    """An HTTPS image from the backend's own origin is allowed (same-origin/backend-origin
    policy) — it renders as a real <img>, with no blocked-image badge.
    """
    markdown = f"Backend image: ![test]({os.getenv('FRONTEND_URL')}/assets/favicon-BwTdc52u.svg)"

    chat_page = chat_with_markdown_reply(page, markdown)

    chat_page.should_have_assistant_image_count(1)
    chat_page.should_have_blocked_image_badge_count(0)


@pytest.mark.ui
@pytest.mark.sanity
@pytest.mark.prod_regression
def test_multiple_images_mixed_allowed_and_blocked(page, chat_with_markdown_reply):
    """A reply with several images blocks only the untrusted one; the allow-listed
    ones (here, two data: URLs) still render.
    """
    markdown = (
        "Images:\n\n"
        f"![one]({_DATA_URL_PNG})\n\n"
        "![two](https://evil.example.com/bad.jpg)\n\n"
        f"![three]({_DATA_URL_PNG})\n"
    )

    chat_page = chat_with_markdown_reply(page, markdown)

    chat_page.should_have_assistant_image_count(2)
    chat_page.should_have_blocked_image_badge_count(1)
    chat_page.should_have_blocked_image_badge_hostname("evil.example.com")
