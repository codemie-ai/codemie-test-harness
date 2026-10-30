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

import uuid

import pytest
from hamcrest import (
    all_of,
    any_of,
    assert_that,
    contains_string,
    is_not,
)

from codemie_test_harness.tests.enums.tools import Toolkit, VcsTool
from codemie_test_harness.tests.utils.base_utils import assert_tool_triggered

# The prompts name the exact request and ask the assistant to quote the tool
# output verbatim, so the assertions match the tool's own wording, not a paraphrase.
IMAGE_RESPONSES_SECTION = "IMAGE RESPONSES"
UPLOAD_API_REQUEST = '"url": "/api/v4/projects/:id/uploads/:secret/:filename"'
UPLOAD_API_FORM_STEERING = "fetched through this API form"

QUOTE_TOOL_OUTPUT = "Quote the tool result text verbatim in your answer."

IMAGE_DESCRIPTION_KEYWORDS = ("dog", "labrador", "retriever", "puppy")
EXPECTED_IMAGE_DESCRIPTION = (
    "The image shows a smiling light-coloured Labrador retriever dog with an open "
    "mouth, wearing a collar with a bone-shaped tag, sitting on a floor in a kitchen."
)

FAKE_IMAGE_WARNING = "Body is not a valid image/png image; skipped."

FOREIGN_ORIGIN_URL = "https://example.com/api/v4/projects"
FOREIGN_ORIGIN_REJECTION = "absolute URL rejected"
FOREIGN_ORIGIN_MISMATCH = "does not match the configured GitLab origin"


def _get_request_prompt(url: str, follow_up: str) -> str:
    return (
        f"Debug uuid: {uuid.uuid4()} Using the gitlab tool, send a GET request with "
        f"the url '{url}' and no other arguments. {follow_up}"
    )


def describe_image_prompt(api_path: str) -> str:
    """Ask the assistant to fetch the uploaded image and describe what it shows."""
    return _get_request_prompt(
        api_path, "Then describe in one sentence what the downloaded image shows."
    )


def quote_result_prompt(url: str) -> str:
    """Ask the assistant to fetch ``url`` and relay the tool result text."""
    return _get_request_prompt(url, QUOTE_TOOL_OUTPUT)


def missing_upload_path(project_id: int) -> str:
    """API-form path of an upload whose secret does not exist."""
    return f"/api/v4/projects/{project_id}/uploads/{uuid.uuid4().hex}/missing.png"


IMAGE_DESCRIPTION_MATCHERS = [
    contains_string(keyword) for keyword in IMAGE_DESCRIPTION_KEYWORDS
]


@pytest.mark.assistant
@pytest.mark.vcs
@pytest.mark.api
def test_gitlab_tool_user_description_documents_image_responses(assistant_utils):
    # @case gitlab_image_download_TC_001
    tool = assistant_utils.get_tool_details(Toolkit.VCS.value, VcsTool.GITLAB.value)

    assert_that(
        tool.user_description,
        all_of(
            contains_string(IMAGE_RESPONSES_SECTION),
            contains_string(UPLOAD_API_REQUEST),
            contains_string(UPLOAD_API_FORM_STEERING),
        ),
        "GitLab tool user_description must document image responses and steer to the upload API form",
    )


@pytest.mark.requires_setting("gitlab")
@pytest.mark.gitlab
@pytest.mark.vcs
@pytest.mark.assistant
@pytest.mark.api
def test_gitlab_tool_downloads_uploaded_image_for_assistant(
    assistant_utils,
    assistant,
    gitlab_integration,
    gitlab_image_upload,
    similarity_check,
):
    # @case gitlab_image_download_TC_003
    gitlab_assistant = assistant(
        Toolkit.VCS, VcsTool.GITLAB, settings=gitlab_integration
    )

    response, triggered_tools = assistant_utils.ask_assistant(
        gitlab_assistant,
        describe_image_prompt(gitlab_image_upload.api_path),
        minimal_response=False,
    )

    assert_tool_triggered(VcsTool.GITLAB, triggered_tools)
    assert_that(
        response.lower(),
        any_of(*IMAGE_DESCRIPTION_MATCHERS),
        "Answer does not describe the uploaded image, so the image never reached the LLM",
    )
    similarity_check.check_similarity(response, EXPECTED_IMAGE_DESCRIPTION)


@pytest.mark.requires_setting("gitlab")
@pytest.mark.gitlab
@pytest.mark.vcs
@pytest.mark.assistant
@pytest.mark.api
def test_gitlab_tool_keeps_text_error_for_missing_image_upload(
    assistant_utils,
    assistant,
    gitlab_integration,
    gitlab_seed_merge_request,
):
    # @case gitlab_image_download_TC_005
    gitlab_assistant = assistant(
        Toolkit.VCS, VcsTool.GITLAB, settings=gitlab_integration
    )

    response, triggered_tools = assistant_utils.ask_assistant(
        gitlab_assistant,
        quote_result_prompt(missing_upload_path(gitlab_seed_merge_request.project_id)),
        minimal_response=False,
    )

    assert_tool_triggered(VcsTool.GITLAB, triggered_tools)
    assert_that(
        response.lower(),
        any_of(contains_string("404"), contains_string("not found")),
        "Answer does not report the 404 error for the missing upload",
    )
    assert_that(
        response.lower(),
        is_not(any_of(*IMAGE_DESCRIPTION_MATCHERS)),
        "A 404 response must not be treated as an image",
    )


@pytest.mark.requires_setting("gitlab")
@pytest.mark.gitlab
@pytest.mark.vcs
@pytest.mark.assistant
@pytest.mark.api
def test_gitlab_tool_rejects_absolute_url_from_foreign_origin(
    assistant_utils,
    assistant,
    gitlab_integration,
):
    # @case gitlab_image_download_TC_008
    gitlab_assistant = assistant(
        Toolkit.VCS, VcsTool.GITLAB, settings=gitlab_integration
    )

    response, triggered_tools = assistant_utils.ask_assistant(
        gitlab_assistant,
        quote_result_prompt(FOREIGN_ORIGIN_URL),
        minimal_response=False,
    )

    assert_tool_triggered(VcsTool.GITLAB, triggered_tools)
    assert_that(
        response,
        all_of(
            contains_string(FOREIGN_ORIGIN_REJECTION),
            contains_string(FOREIGN_ORIGIN_MISMATCH),
        ),
        "Answer does not relay the origin-mismatch rejection",
    )


@pytest.mark.requires_setting("gitlab")
@pytest.mark.gitlab
@pytest.mark.vcs
@pytest.mark.assistant
@pytest.mark.api
def test_gitlab_tool_skips_non_image_bytes_served_as_png(
    assistant_utils,
    assistant,
    gitlab_integration,
    gitlab_fake_png_upload,
):
    # @case gitlab_image_download_TC_009
    gitlab_assistant = assistant(
        Toolkit.VCS, VcsTool.GITLAB, settings=gitlab_integration
    )

    response, triggered_tools = assistant_utils.ask_assistant(
        gitlab_assistant,
        quote_result_prompt(gitlab_fake_png_upload.api_path),
        minimal_response=False,
    )

    assert_tool_triggered(VcsTool.GITLAB, triggered_tools)
    assert_that(
        response,
        contains_string(FAKE_IMAGE_WARNING),
        "Answer does not relay the signature-mismatch skip text",
    )
