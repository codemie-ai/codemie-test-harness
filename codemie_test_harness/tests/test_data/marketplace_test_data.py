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

"""Test data for marketplace validation tests."""

import random
import uuid

import pytest

from codemie_test_harness.tests.utils.base_utils import get_random_name

# Valid assistant name
COMPLETE_ASSISTANT_NAME = f"CodeMie Platform Guide ID{random.randint(0, 999)}"

# Valid categories list
COMPLETE_CATEGORIES = "quality-assurance"

# Complete system prompt that should pass validation
COMPLETE_SYSTEM_PROMPT = """## Role
You are a knowledgeable assistant that helps users understand and navigate the CodeMie platform effectively.

## Responsibilities
1. Answer questions about platform features, capabilities, and best practices.
2. Explain concepts and workflows in clear, understandable language.
3. Provide guidance on how to configure and use platform components.
4. Help users find relevant documentation and resources.

## Guidelines
- Always provide accurate and up-to-date information based on the provided context.
- Break down complex topics into easy-to-understand explanations.
- Use examples to illustrate concepts when appropriate.
- Acknowledge limitations and suggest official documentation when needed.

## Scope
- Platform features, integrations, and configuration
- Best practices and recommendations
- Troubleshooting common issues
- Feature usage and workflows"""

# Complete description that should pass validation
COMPLETE_DESCRIPTION = (
    "A comprehensive platform guide designed to help users understand and effectively "
    "use CodeMie's features, integrations, and workflows. It provides clear explanations, "
    "best practices, and step-by-step guidance to help teams get the most out of the platform."
)

# Good conversation starters
GOOD_CONVERSATION_STARTERS = [
    "How do I configure a new integration in CodeMie?",
    "What are the best practices for setting up workflows?",
    "Can you explain how the assistant marketplace works?",
    "What features are available for team collaboration?",
]

# Random data for tests where field should be wrong
WRONG_DATA = get_random_name()

# Test configurations for parametrized validation tests
VALIDATION_TEST_CONFIGS = [
    {
        "id": "wrong_name_good_description_good_prompt",
        "config": {
            "assistant_name": WRONG_DATA,
            "description": COMPLETE_DESCRIPTION,
            "system_prompt": COMPLETE_SYSTEM_PROMPT,
            "conversation_starters": GOOD_CONVERSATION_STARTERS,
            "categories": [COMPLETE_CATEGORIES],
        },
        "expected_issues": ["name"],
        "description": "Wrong assistant name with good description and system prompt",
    },
    {
        "id": "good_name_wrong_description_good_prompt",
        "config": {
            "assistant_name": COMPLETE_ASSISTANT_NAME,
            "description": WRONG_DATA,
            "system_prompt": COMPLETE_SYSTEM_PROMPT,
            "conversation_starters": GOOD_CONVERSATION_STARTERS,
            "categories": [COMPLETE_CATEGORIES],
        },
        "expected_issues": ["description"],
        "description": "Good name with wrong description and good system prompt",
    },
    {
        "id": "good_name_good_description_wrong_prompt",
        "config": {
            "assistant_name": COMPLETE_ASSISTANT_NAME,
            "description": COMPLETE_DESCRIPTION,
            "system_prompt": WRONG_DATA,
            "conversation_starters": GOOD_CONVERSATION_STARTERS,
            "categories": [COMPLETE_CATEGORIES],
        },
        "expected_issues": ["system_prompt"],
        "description": "Good name and description with wrong system prompt",
    },
    {
        "id": "all_fields_wrong",
        "config": {
            "assistant_name": WRONG_DATA,
            "description": WRONG_DATA,
            "system_prompt": WRONG_DATA,
            "conversation_starters": [],
            "categories": [],
        },
        "expected_issues": ["name", "description", "system_prompt"],
        "description": "All fields are wrong",
    },
]

# Complete valid configuration for successful publish tests
COMPLETE_VALID_CONFIG = {
    "assistant_name": COMPLETE_ASSISTANT_NAME,
    "description": COMPLETE_DESCRIPTION,
    "system_prompt": COMPLETE_SYSTEM_PROMPT,
    "conversation_starters": GOOD_CONVERSATION_STARTERS,
    "categories": [COMPLETE_CATEGORIES],
}


def get_publishable_assistant_config() -> dict:
    """Return ``COMPLETE_VALID_CONFIG`` with a name unique to this call.

    With the approval gate armed, a publish is blocked with 422 on any CRITICAL
    gate finding (description under 100 chars, system prompt under 200 chars,
    no category, ...) and ``ignore_recommendations`` cannot waive it, so an
    assistant meant to be published must carry real content. The name doubles
    as the slug, so two assistants in one test need distinct names.
    """
    return {
        **COMPLETE_VALID_CONFIG,
        "assistant_name": f"CodeMie Platform Guide ID{random.randint(1000, 999999)}",
    }


# ---------------------------------------------------------------------------
# Sorting test data
# ---------------------------------------------------------------------------

SORT_ORDER_VALUES = ["asc", "desc"]

# Parametrize matrix for TC-02 metric sort tests.
# Each param: (sort_by, sort_order, response_field_name, reverse_flag)
# response_field_name is the attribute on the Assistant model that holds the metric value.
# reverse_flag=True means sorted(values, reverse=True) is the expected order.
SORT_METRIC_PARAMS = [
    pytest.param("usage", "desc", "unique_users_count", True, id="usage-desc"),
    pytest.param("usage", "asc", "unique_users_count", False, id="usage-asc"),
    pytest.param("likes", "desc", "unique_likes_count", True, id="likes-desc"),
    pytest.param("likes", "asc", "unique_likes_count", False, id="likes-asc"),
    pytest.param("dislikes", "desc", "unique_dislikes_count", True, id="dislikes-desc"),
    pytest.param("dislikes", "asc", "unique_dislikes_count", False, id="dislikes-asc"),
]

# Parametrize matrix for TC-02b name sort tests.
# Each param: (sort_order, reverse_flag)
# Backend uses case-insensitive collation; we replicate with str.lower then default sort.
SORT_NAME_PARAMS = [
    pytest.param("asc", False, id="name-asc"),
    pytest.param("desc", True, id="name-desc"),
]

# Parametrize matrix for TC-10a sort + search metric tests.
# Each param: (sort_by, sort_order, response_field_name, reverse_flag)
# Covers usage/likes/dislikes in both directions; verifies the search filter count
# is preserved and results are monotonically ordered by the metric field.
SORT_QUERY_METRIC_PARAMS = [
    pytest.param("usage", "desc", "unique_users_count", True, id="usage-desc"),
    pytest.param("usage", "asc", "unique_users_count", False, id="usage-asc"),
    pytest.param("likes", "desc", "unique_likes_count", True, id="likes-desc"),
    pytest.param("likes", "asc", "unique_likes_count", False, id="likes-asc"),
    pytest.param("dislikes", "desc", "unique_dislikes_count", True, id="dislikes-desc"),
    pytest.param("dislikes", "asc", "unique_dislikes_count", False, id="dislikes-asc"),
]

# Parametrize matrix for TC-10b sort by name + search tests.
# Each param: (sort_order, reverse_flag)
SORT_QUERY_NAME_PARAMS = [
    pytest.param("asc", False, id="name-asc"),
    pytest.param("desc", True, id="name-desc"),
]


def get_unknown_assistant_id() -> str:
    """Return a well-formed assistant id that matches no stored assistant."""
    return str(uuid.uuid4())
