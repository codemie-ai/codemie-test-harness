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

"""Context management test package.

This package contains tests for workflow context management features:
- store_in_context: Controls whether state output is stored in context store (default: true)
- include_in_llm_history: Controls whether state output appears in LLM message history (default: true)
- clear_prior_messages: Clears all prior messages from message history (default: false)
- clear_context_store: Controls context store clearing (false | true | "keep_current", default: false)

These features control how data flows between workflow states, what information
is available to LLM assistants, and when to reset context between workflow phases.
"""

# Test data constants for consistent testing across all context management tests
TEST_DATA = {
    "user_id": "user_12345",
    "project_id": "proj_67890",
    "file_id": "file_abc123",
    "secret_code": "test-value-123",
    "magic_number": "42",
    "secret_word": "BANANA",
}

# System prompts for different assistant roles
SYSTEM_PROMPTS = {
    "data_extractor": "You are a helpful assistant that extracts and outputs structured data.",
    "data_processor": "You are a helpful assistant that processes and uses data from context.",
    "information_provider": "You are a helpful assistant that provides specific information.",
    "information_validator": "You are a helpful assistant that validates and recalls information from conversation history.",
}
