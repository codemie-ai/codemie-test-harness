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

"""Test data for the Image Inspector tool (inspect_workspace_image).

`inspect_workspace_image` now performs an independent LLM call
and returns the analysis as a plain tool response, instead of injecting an extra
message with the base64 image into the conversation history. Prompt factories below
embed a debug UUID (mirroring the pattern used in budget_test_data.py) so reruns and
repeated CI executions don't hit a cached LLM/similarity-workflow response for the
exact same prompt text.
"""

import uuid

IMAGE_FILE = "test.png"
# Non-image content (mirrors the backend unit test
# test_execute_raises_when_file_is_not_image, which also uses a non-image
# extension) — deliberately NOT an image extension so the outer multimodal
# chat call doesn't attempt to validate it as an image attachment; only
# inspect_workspace_image's own magic-byte check should reject it.
INVALID_IMAGE_FILE = "invalid_image.txt"

SYSTEM_PROMPT = (
    "When asked to analyze an image, always use the inspect_workspace_image tool. "
    "Answer with a single word only."
)

INSPECT_IMAGE_PROMPT = (
    "Use the inspect_workspace_image tool to analyze the attached image. "
    "Reply with exactly one word: the name of the animal you see."
)


def inspect_image_prompt() -> str:
    """Unique variant of INSPECT_IMAGE_PROMPT (cache-busting debug UUID)."""
    return f"Debug uuid: {uuid.uuid4()} {INSPECT_IMAGE_PROMPT}"


DESCRIBE_IMAGE_PROMPT = "Describe the attached picture in one sentence."


def describe_image_prompt() -> str:
    """Unique variant of DESCRIBE_IMAGE_PROMPT (cache-busting debug UUID)."""
    return f"Debug uuid: {uuid.uuid4()} {DESCRIBE_IMAGE_PROMPT}"


MULTI_STEP_SYSTEM_PROMPT = (
    "Complete every numbered step in the user's request, in order, even when one of "
    "the steps requires using the inspect_workspace_image tool. Never stop responding "
    "after a tool call if further numbered steps remain."
)

MULTI_STEP_PROMPT = (
    "Complete all three steps below and explicitly address each one in your final answer: "
    "1) State the sum of 2 and 2 as a numeral digit. "
    "2) Use the inspect_workspace_image tool to name the animal in the attached image. "
    "3) State the capital of France."
)


def multi_step_prompt() -> str:
    """Unique variant of MULTI_STEP_PROMPT (cache-busting debug UUID)."""
    return f"Debug uuid: {uuid.uuid4()} {MULTI_STEP_PROMPT}"


INVALID_IMAGE_INSPECT_PROMPT = (
    "Use the inspect_workspace_image tool to analyze the attached file as if it were "
    "an image and describe what you see, even though its extension is not a typical "
    "image extension."
)


def invalid_image_inspect_prompt() -> str:
    """Unique variant of INVALID_IMAGE_INSPECT_PROMPT (cache-busting debug UUID)."""
    return f"Debug uuid: {uuid.uuid4()} {INVALID_IMAGE_INSPECT_PROMPT}"


# Marker text from the removed `content_and_artifact` side-channel
# (the former `InspectWorkspaceImageResponse.text`); must never reappear
# in conversation history after the fix.
OLD_IMAGE_ARTIFACT_MARKER = "attached for visual analysis"
