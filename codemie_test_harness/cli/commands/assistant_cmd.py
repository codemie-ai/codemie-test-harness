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

"""Assistant CLI commands for interactive chat with assistants."""

from __future__ import annotations

import uuid
from typing import Optional

import click

import os

from codemie_sdk.models.assistant import AssistantChatRequest
from codemie_test_harness.tests.utils.client_factory import get_client
from ..constants import CONSOLE


@click.group(name="assistant")
def assistant_cmd():
    """Interact with CodeMie assistants."""
    pass


@assistant_cmd.command(name="chat")
@click.option(
    "--assistant-id",
    required=True,
    help="Assistant ID to chat with",
)
@click.option(
    "--conversation-id",
    help="Conversation ID to continue existing chat (optional)",
)
@click.option(
    "--message",
    "-m",
    required=True,
    help="Message to send to the assistant",
)
@click.option(
    "--stream/--no-stream",
    default=False,
    help="Stream the response (default: no-stream)",
)
def chat_cmd(
    assistant_id: str,
    conversation_id: Optional[str],
    message: str,
    stream: bool,
):
    """Chat with a specific assistant.

    Example:
        codemie-test-harness assistant chat --assistant-id "asst_123" -m "Hello, how can you help me?"
        codemie-test-harness assistant chat --assistant-id "asst_123" --conversation-id "conv_456" -m "Continue our conversation"
    """
    try:
        client = get_client()

        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            CONSOLE.print(
                f"[green]New conversation started with ID: {conversation_id}[/green]"
            )
        else:
            CONSOLE.print(f"[blue]Continuing conversation: {conversation_id}[/blue]")

        # Create chat request
        langfuse_enabled = (
            os.getenv("LANGFUSE_TRACES_ENABLED", "false").lower() == "true"
        )
        chat_request = AssistantChatRequest(
            text=message,
            conversation_id=conversation_id,
            stream=stream,
            metadata={"langfuse_traces_enabled": langfuse_enabled},
        )

        CONSOLE.print(
            f"[yellow]Sending message to assistant {assistant_id}...[/yellow]"
        )

        # Send chat request
        response = client.assistants.chat(
            assistant_id=assistant_id, request=chat_request
        )

        # Display response
        if hasattr(response, "generated") and response.generated:
            CONSOLE.print("[green]Assistant Response:[/green]")
            CONSOLE.print(response.generated)
        elif hasattr(response, "task_id") and response.task_id:
            CONSOLE.print(
                f"[yellow]Background task created with ID: {response.task_id}[/yellow]"
            )
            CONSOLE.print(
                "[blue]You can check the task status using the task ID[/blue]"
            )
        else:
            CONSOLE.print(f"[cyan]Raw response:[/cyan] {response}")

    except Exception as e:
        CONSOLE.print(f"[red]Error chatting with assistant: {e}[/red]")
        raise click.ClickException(str(e))
