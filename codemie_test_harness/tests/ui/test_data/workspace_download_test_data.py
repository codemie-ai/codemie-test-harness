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

"""Test data for the "Download all" action of the agent workspace browser popup."""

WORKSPACE_POPUP_TITLE = "Agent workspace"

# Name the browser gives to the archive produced by "Download all".
WORKSPACE_ARCHIVE_NAME = "workspace-files.zip"

# Sample files of tests/test_data/files used as uploads.
BINARY_SAMPLE_FILE = "test.jpeg"
TEXT_SAMPLE_FILE = "test.csv"
OTHER_TEXT_SAMPLE_FILE = "test.txt"

# Python script the assistant is asked to write into the chat workspace.
GENERATED_SCRIPT_NAME = "hello_workspace.py"

WORKSPACE_ASSISTANT_SYSTEM_PROMPT = (
    "You are a concise assistant with workspace file tools. "
    "Use the workspace tools only when the user asks you to create or list a "
    "file; otherwise answer in one short sentence without calling any tool."
)

# First message of a chat: gives the chat a message (so "Browse files" is rendered)
# without writing anything into the workspace.
NO_FILE_PROMPT = "Reply with the single word OK. Do not call any tool."

GENERATE_SCRIPT_PROMPT = (
    f"Create a Python script named {GENERATED_SCRIPT_NAME} in the workspace "
    "that prints the text hello. Save it with the write workspace file tool, "
    "then confirm in one short sentence."
)

UPLOAD_ACK_PROMPT = (
    "I attached files. Reply with the single word OK. Do not call any tool."
)
