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

from dataclasses import dataclass

from codemie_test_harness.tests.utils.base_utils import get_random_name

# The assistant answers every message with this fixed text, so the output of each
# earlier execution is known to be short and free of any user input marker.
FIXED_REPLY_SYSTEM_PROMPT = (
    "Reply with exactly the text ACK-DONE and nothing else, whatever the message says."
)


@dataclass
class WorkflowChatHistoryData:
    """Unique user inputs of three consecutive messages in one workflow conversation."""

    first_input: str
    second_input: str
    third_input: str


def workflow_chat_history_data() -> WorkflowChatHistoryData:
    return WorkflowChatHistoryData(
        first_input=f"First message marker {get_random_name()}",
        second_input=f"Second message marker {get_random_name()}",
        third_input=f"Third message marker {get_random_name()}",
    )
