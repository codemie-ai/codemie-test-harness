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

"""Test data for Transform Node tests that read user_input holding surrogate escapes.

The user_input strings below are raw text: the backslash-u escapes travel to the server
as escape text and are decoded only when the transform node parses user_input as JSON.
The server sanitizes the decoded value: an escaped high+low pair becomes one character,
an unpaired surrogate becomes U+FFFD (REPLACEMENT CHARACTER).
"""

from dataclasses import dataclass

import pytest

# Name of the user_input key the transform node extracts, and the field it writes to
SURROGATE_SOURCE_KEY = "pr_description"
SURROGATE_OUTPUT_FIELD = "pr_text"

# Text of the encoder error the server raised before sanitizing surrogates
SURROGATE_CODEC_ERROR = "surrogates not allowed"


@dataclass(frozen=True)
class SurrogateUserInput:
    user_input: str
    expected_text: str


SURROGATE_USER_INPUTS = [
    pytest.param(
        SurrogateUserInput(
            user_input=r'{"pr_description": "📚"}',
            expected_text="\U0001f4da",
        ),
        id="escaped-surrogate-pair",
    ),
    pytest.param(
        SurrogateUserInput(
            user_input=r'{"pr_description": "x \ud83d y"}',
            expected_text="x � y",
        ),
        id="lone-high-surrogate",
    ),
]
