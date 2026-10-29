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

"""
Test Data for Chat UI Tests

This module provides test data generation and management for chat-related UI tests.
Following best practices by separating test data from test logic and providing
reusable data factories for consistent testing.

Architecture follows the same patterns as other test data modules in the framework.
"""

from dataclasses import dataclass


@dataclass
class ChatTestMessage:
    """
    Data class for chat message test data.

    Encapsulates message content and metadata for chat testing scenarios.
    """

    content: str
    expected_response: str


class ChatTestDataFactory:
    """
    Factory class for generating chat test data.

    This factory provides various methods to create different types of
    chat test data for different testing scenarios.
    """

    @staticmethod
    def create_simple_test_message() -> ChatTestMessage:
        """
        Create a simple test message for basic chat functionality testing.

        Returns:
            ChatTestMessage: Simple test message data
        """
        return ChatTestMessage(
            content="Hello, this is a test message for chat functionality validation.",
            expected_response="",
        )

    @staticmethod
    def create_coding_help_message() -> ChatTestMessage:
        """
        Create a coding-related question message.
        """
        return ChatTestMessage(
            content="Hello, I need help with a coding question.",
            expected_response="",
        )

    @staticmethod
    def create_coding_question_message() -> ChatTestMessage:
        """
        Create a coding-related question message.
        """
        return ChatTestMessage(
            content="Can you help me understand Python decorators?",
            expected_response="",
        )

    @staticmethod
    def create_long_running_prompt_message() -> ChatTestMessage:
        """
        Create a short prompt that still produces a long enough streamed response
        for Stop button tests.
        """
        return ChatTestMessage(
            content="List numbers 1 to 100, one per line.",
            expected_response="",
        )


# ==================== CONVENIENCE FUNCTIONS ====================


def get_simple_test_message() -> ChatTestMessage:
    """Convenience function to get simple test message."""
    return ChatTestDataFactory.create_simple_test_message()


def get_coding_help_message() -> ChatTestMessage:
    """Convenience function to get coding help message."""
    return ChatTestDataFactory.create_coding_help_message()


def get_coding_question_message() -> ChatTestMessage:
    """Convenience function to get coding question message."""
    return ChatTestDataFactory.create_coding_question_message()


def get_long_running_prompt_message() -> ChatTestMessage:
    """Convenience function to get a prompt that produces a long assistant response."""
    return ChatTestDataFactory.create_long_running_prompt_message()


@dataclass
class ToolInvokingMessage:
    """Data class for a message that reliably triggers tool execution."""

    content: str


def get_tool_invoking_message() -> ToolInvokingMessage:
    """Returns a prompt that reliably triggers tool execution (Wikipedia search tool)."""
    return ToolInvokingMessage(
        content=(
            "You must call the Wikipedia tool right now. "
            "Search Wikipedia for 'Python programming language'. "
            "Do not answer without calling the tool first."
        )
    )


# ==================== TEST DATA CONSTANTS ====================

# Common test messages for reuse
COMMON_TEST_MESSAGES = {
    "hello": "Hello, how can you help me today?",
    "coding_help": "Can you help me debug this Python code?",
    "documentation": "Please help me write documentation for this API.",
    "code_review": "Can you review this code and suggest improvements?",
    "testing_help": "What are the best practices for unit testing?",
    "architecture": "How should I design a microservices architecture?",
}

# Draft preservation tests
DRAFT_TEXT = "Draft prompt not yet submitted"
