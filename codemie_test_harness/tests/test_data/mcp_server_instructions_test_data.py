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

"""Test data for MCP server-side instructions tests.

Builds a real stdio MCP server (via ``uv run ... python -c "<source>"``, the same
``uv``/``mcp<2.0.0`` tooling the other MCP server fixtures in this module use) whose
``FastMCP(..., instructions=...)`` declares server-side instructions at handshake. The
instructions ask the model to relay a predefined, deterministic sentence whenever its one
tool is called, so a chat response can be checked for literal compliance instead of judged
by similarity.
"""

from codemie_sdk.models.assistant import MCPServerDetails, MCPServerConfig

PREDEFINED_REPLY_SENTENCE = "Server instructions acknowledged: reply token RT-7781."

SERVER_INSTRUCTIONS = (
    "Every time the confirm_reply tool is called, your response to the user must "
    f'consist of exactly this sentence and nothing else: "{PREDEFINED_REPLY_SENTENCE}"'
)

# Pin `mcp` below 2.0.0: mcp==2.0.0 renamed `Server.list_tools`, breaking FastMCP
# the same way it breaks the other locally-run MCP server fixtures in this module.
INSTRUCTIONS_FIXTURE_SERVER_SOURCE = f'''
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("instructions-fixture-server", instructions={SERVER_INSTRUCTIONS!r})


@mcp.tool()
def confirm_reply() -> str:
    """Acknowledge the call so the caller can relay the server's instructed reply."""
    return "acknowledged"


if __name__ == "__main__":
    mcp.run()
'''

INSTRUCTIONS_MCP_SERVER = MCPServerDetails(
    name="Instructions MCP server",
    description="Fixture MCP server declaring server-side instructions at handshake",
    enabled=True,
    config=MCPServerConfig(
        command="uv",
        args=[
            "run",
            "--with",
            "mcp<2.0.0",
            "python",
            "-c",
            INSTRUCTIONS_FIXTURE_SERVER_SOURCE,
        ],
    ),
)

INSTRUCTIONS_MCP_SERVER_PROMPT = "Call the confirm_reply tool, then answer the user."
