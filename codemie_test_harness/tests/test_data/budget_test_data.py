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

"""Test data for Budget and spending tests."""

import uuid

from codemie_test_harness.tests.enums.model_types import ModelTypes

BUDGET_CHAT_PROMPT = "Say hello"


def budget_chat_prompt() -> str:
    return f"Debug uuid: {uuid.uuid4()} {BUDGET_CHAT_PROMPT}"


BUDGET_CHAT_PROMPT_BIGGER = (
    "Give me sentence with 1000 words. Random theme, nothing else."
)


def budget_chat_prompt_bigger() -> str:
    return f"Debug uuid: {uuid.uuid4()} {BUDGET_CHAT_PROMPT_BIGGER}"


PREMIUM_MODEL = ModelTypes.CLAUDE_4_7_OPUS.value
CLI_CLIENT_HEADER = {"X-CodeMie-Client": "codemie-cli"}
DEFAULT_PLATFORM_BUDGET_ID = "default"
DEFAULT_CLI_BUDGET_ID = "codemie_cli"
DEFAULT_PREMIUM_BUDGET_ID = "codemie_premium_models"
PROJECT_KEY_ALIAS_TEMPLATE = "codemie:project:{project_name}:category:{category}"
MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE = (
    "codemie:project:{project_name}:category:{category}:user:{user_id}"
)
CHROME_EXTENSION_CLIENT_HEADER = {"X-CodeMie-Client": "codemie-chrome-extension"}


PLATFORM_BUDGET_CATEGORIES = {"platform": {"max_budget": 100.0, "soft_budget": 50.0}}
CLI_BUDGET_CATEGORIES = {"cli": {"max_budget": 100.0, "soft_budget": 50.0}}
PREMIUM_BUDGET_CATEGORIES = {
    "premium_models": {"max_budget": 100.0, "soft_budget": 50.0}
}
ALL_BUDGET_CATEGORIES = {
    **PLATFORM_BUDGET_CATEGORIES,
    **CLI_BUDGET_CATEGORIES,
    **PREMIUM_BUDGET_CATEGORIES,
}
# Every budget group must keep a Platform hard limit above 0. Groups
# defined without Platform get this minimal Platform share added on creation.
MIN_PLATFORM_BUDGET = {"max_budget": 1.0, "soft_budget": 0.5}
# Project budget availability is cached by the backend for about a minute.
BUDGET_CACHE_DELAY = 60
# Member budget tracking has to settle before a budget group can be created for a project.
PROJECT_BUDGET_TRACKING_DELAY = 30
CLI_PROJECT_HEADER = "X-CodeMie-Project"


def budget_skill_description() -> str:
    return f"Skill that summarises meeting notes. Debug uuid: {uuid.uuid4()}"


def project_key_alias(project_name: str, category: str = "platform") -> str:
    return PROJECT_KEY_ALIAS_TEMPLATE.format(
        project_name=project_name, category=category
    )
