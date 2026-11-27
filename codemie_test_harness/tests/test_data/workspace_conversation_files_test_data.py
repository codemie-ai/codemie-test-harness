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

"""Data for the tests of workspace reads of another user's conversation files."""

import uuid
from dataclasses import dataclass

from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.workspace_file_utils import (
    read_via_content,
    read_via_download,
)

# What the router answers when the workspace service refuses a request (ValidationException).
INVALID_WORKSPACE_REQUEST = "Invalid workspace request"
NOT_FOUND_WORDING = "not found"

READ_ENDPOINTS = [read_via_content, read_via_download]
READ_ENDPOINT_IDS = ["content", "download"]


@dataclass
class ConversationFile:
    """A file one user attached to a conversation of their own."""

    conversation_id: str
    file_name: str
    file_path: str
    marker: str


def new_marker() -> str:
    """A unique file body that cannot appear in any other response."""
    return f"private conversation payload {uuid.uuid4()}"


def new_file_name() -> str:
    return f"conversation_file_{get_random_name()}.txt"
