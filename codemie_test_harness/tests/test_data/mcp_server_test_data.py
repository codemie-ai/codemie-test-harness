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

from typing import NamedTuple, Optional


from codemie_sdk.models.assistant import MCPServerDetails, MCPServerConfig

from codemie_test_harness.tests.enums.tools import (
    McpServerSqlite,
    McpServerFilesystem,
    McpServerGithub,
    McpServerPostgresql,
    McpServerPlaywright,
    McpServerPuppeteer,
)
from codemie_test_harness.tests.test_data.vcs_tools_test_data import (
    GITHUB_TOOL_TASK,
    RESPONSE_FOR_GITHUB,
)


class MCPServerTestCase(NamedTuple):
    """Test case for MCP server assistant tests."""

    mcp_server: MCPServerDetails
    user_message: str
    expected_response: str
    expected_tools: list[str]
    integration_fixture: Optional[str] = None


cli_mcp_server_test_data = [
    (
        "ls",
        """
            Here is the list of directories and files in the current directory:
    
            bin
            games
            include
            lib
            lib64
            libexec
            local
            sbin
            share
            src
        """,
    ),
    (
        "ls /tmp",
        """
            It seems that the command `ls /tmp` cannot be executed because it is outside the allowed directory (`/usr`).
            Only commands within the `/usr` directory are permitted.
        """,
    ),
    (
        "touch long-file-name-for-test.txt",
        """
            It appears that the command exceeds the maximum allowed length of 20 characters.
            Let's try a shorter command.
        """,
    ),
    (
        "cat file.txt",
        """
            The `cat` command is not supported in this environment. If you need to list or display
            the contents of a file, please provide an alternative command that is supported.
            You can use `ls` to list files or `echo` to display text.
        """,
    ),
    (
        "ls -a",
        """
            The `-a` flag is not allowed in this environment. Here are the allowed commands and flags:
    
            - Commands: `ls`, `echo`
            - Flags: `-l`, `--help`
    
            Would you like to run a different command?
        """,
    ),
]

CLI_MCP_SERVER = MCPServerDetails(
    name="CLI MCP server",
    description="CLI MCP server",
    enabled=True,
    config=MCPServerConfig(
        command="uvx",
        # Pin `mcp` below 2.0.0: cli-mcp-server declares an unpinned `mcp>=1.10.1`
        # dependency, and mcp==2.0.0 renamed `Server.list_tools`, breaking it.
        args=["--with", "mcp<2.0.0", "cli-mcp-server"],
        env={
            "ALLOWED_DIR": "/usr",
            "ALLOWED_COMMANDS": "ls,echo,touch",
            "ALLOWED_FLAGS": "-l,--help",
            "MAX_COMMAND_LENGTH": "20",
        },
    ),
)

# Pin `mcp` below 2.0.0: mcp-server-time declares an unpinned `mcp>=1.23.0`
# dependency, and mcp==2.0.0 renamed `Server.list_tools`, breaking it.
TIME_MCP_SERVER_WITH_CONFIG = MCPServerDetails(
    name="Time MCP server",
    description="Time MCP server",
    enabled=True,
    config=MCPServerConfig(
        command="uvx", args=["--with", "mcp<2.0.0", "mcp-server-time"]
    ),
)

TIME_MCP_SERVER_WITHOUT_CONFIG = MCPServerDetails(
    name="Time MCP server",
    description="Time MCP server",
    command="uvx",
    arguments="--with mcp<2.0.0 mcp-server-time",
    enabled=True,
)

time_mcp_server_test_data = [
    TIME_MCP_SERVER_WITH_CONFIG,
    TIME_MCP_SERVER_WITHOUT_CONFIG,
]

# Pin `mcp` below 2.0.0: mcp-server-fetch declares an unpinned `mcp>=1.1.3`
# dependency, and mcp==2.0.0 renamed `Server.list_tools`, breaking it.
FETCH_MCP_SERVER = MCPServerDetails(
    name="Fetch MCP server",
    description="Fetch MCP server",
    enabled=True,
    config=MCPServerConfig(
        command="uvx", args=["--with", "mcp<2.0.0", "mcp-server-fetch"]
    ),
)

fetch_server_prompt = "Fetch https://rubular.com/"

fetch_expected_response = r"""
    Rubular is a Ruby regular expression editor. It provides a quick reference guide for regex syntax:

    ### Regex Quick Reference
    
    #### Character Classes
    - `[abc]`: A single character of: a, b, or c
    - `[^abc]`: Any single character except: a, b, or c
    - `[a-z]`: Any single character in the range a-z
    - `[a-zA-Z]`: Any single character in the range a-z or A-Z
    
    #### Anchors
    - `^`: Start of line
    - `$`: End of line
    - `\A`: Start of string
    - `\z`: End of string
    
    #### Special Characters
    - `.`: Any single character
    - `\s`: Any whitespace character
    - `\S`: Any non-whitespace character
    - `\d`: Any digit
    - `\D`: Any non-digit
    - `\w`: Any word character (letter, number, underscore)
    - `\W`: Any non-word character
    - `\b`: Any word boundary
    
    #### Grouping and Quantifiers
    - `(...)`: Capture everything enclosed
    - `(a|b)`: a or b
    - `a?`: Zero or one of a
    - `a*`: Zero or more of a
    - `a+`: One or more of a
    - `a{3}`: Exactly 3 of a
    - `a{3,}`: 3 or more of a
    - `a{3,6}`: Between 3 and 6 of a
    
    #### Options
    - `i`: Case insensitive
    - `m`: Make dot match newlines
    - `x`: Ignore whitespace in regex
    - `o`: Perform `#{...}` substitutions only once
    
    This editor can be helpful for testing and experimenting with Ruby regular expressions.
"""

time_server_prompt = (
    'Convert time 23:11 from "Asia/Tokyo" timezone to "America/New_York" timezone'
)

time_expected_response = """
    The time 23:11 (11:11 PM) in the "Asia/Tokyo" timezone converts to 10:11 (10:11 AM) on the same day
     in the "America/New_York" timezone.
"""

# SQLite MCP Server
# Pin `mcp` below 2.0.0: mcp-server-sqlite declares an unpinned `mcp[cli]>=1.6.0`
# dependency, and mcp==2.0.0 renamed `Server.list_tools`, breaking it.
SQLITE_MCP_SERVER = MCPServerDetails(
    name="SQLITE MCP Server",
    description="SQLITE MCP Server with all tool available",
    enabled=True,
    config=MCPServerConfig(
        command="uvx",
        args=[
            "--with",
            "mcp<2.0.0",
            "mcp-server-sqlite",
            "--db-path",
            "/home/codemie/SQLite/$DB_NAME.db",
        ],
        env={"DB_NAME": "testSQLite"},
    ),
    mcp_connect_url="",
    tools=[tool.value for tool in McpServerSqlite],
)

SQLITE_MCP_SERVER_PROMPT = (
    "Delete table USERS, then create table USERS and fill it with 5 records"
)

SQLITE_MCP_SERVER_EXPECTED_RESPONSE = """
     The USERS table was deleted (if it existed), newly created, and filled with 5 records.
     If you want to view the records or perform further actions, let me know!
"""

# Filesystem MCP Server
FILESYSTEM_MCP_SERVER = MCPServerDetails(
    name="Filesystem MCP Server",
    description="Filesystem MCP Server for file operations",
    enabled=True,
    config=MCPServerConfig(
        command="mcp-server-filesystem",
        args=[
            "$WORKING_FOLDER",
        ],
        env={"WORKING_FOLDER": "/home/codemie"},
    ),
    tools=[tool.value for tool in McpServerFilesystem],
)

FILESYSTEM_MCP_SERVER_PROMPT = "List directory /home/codemie"

FILESYSTEM_MCP_SERVER_EXPECTED_RESPONSE = """
    Here are the contents of the /home/codemie directory:
Files:
.bash_logout
.bashrc
.profile

Directories:
.cache
.local
.npm
SQLite
"""

# GitHub MCP Server
GITHUB_MCP_SERVER = MCPServerDetails(
    name="GitHub MCP Server",
    description="GitHub MCP Server for GitHub API operations",
    enabled=True,
    config=MCPServerConfig(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env={"GITHUB_PERSONAL_ACCESS_TOKEN": "$GITHUB_PERSONAL_ACCESS_TOKEN"},
    ),
    tools=[tool.value for tool in McpServerGithub],
)

# PostgreSQL MCP Server
POSTGRESQL_MCP_SERVER = MCPServerDetails(
    name="PostgreSQL MCP Server",
    description="PostgreSQL MCP Server for database operations",
    enabled=True,
    config=MCPServerConfig(
        command="mcp-server-postgres",
        args=["postgresql://$USERNAME:$PASSWORD@$HOST:$PORT/$DBNAME"],
    ),
    tools=[tool.value for tool in McpServerPostgresql],
)

POSTGRESQL_MCP_SERVER_PROMPT = "Show the DB version"

# Not pinned to an exact version/build string (e.g. "PostgreSQL 17.5 on
# x86_64-pc-linux-gnu, ..."): that breaks on any server upgrade. The
# consuming test only runs this through an LLM-judged similarity_check
# (threshold 60, not exact match), so stating that the answer names the
# PostgreSQL version is enough to score as a match against the real banner.
POSTGRESQL_MCP_SERVER_EXPECTED_RESPONSE = """
    The database version is PostgreSQL, followed by its version number.
"""

# Playwright MCP Server
PLAYWRIGHT_MCP_SERVER = MCPServerDetails(
    name="Playwright MCP Server",
    description="Playwright MCP Server for browser automation",
    enabled=True,
    config=MCPServerConfig(
        command="npx",
        args=[
            "@playwright/mcp@latest",
            "--isolated",
            "--headless",
            "--no-sandbox",
            "--executable-path",
            "/usr/bin/chromium",
            "--viewport-size",
            "1920x1080",
        ],
    ),
    tools=[tool.value for tool in McpServerPlaywright],
)

# Puppeteer MCP Server
PUPPETEER_MCP_SERVER = MCPServerDetails(
    name="Puppeteer MCP Server",
    description="Puppeteer MCP Server for browser automation",
    enabled=True,
    config=MCPServerConfig(
        command="mcp-server-puppeteer",
        args=[],
        env={
            "DEBIAN_FRONTEND": "noninteractive",
            "DOCKER_CONTAINER": True,
            "PUPPETEER_EXECUTABLE_PATH": "/usr/bin/chromium",
            "PUPPETEER_SKIP_CHROMIUM_DOWNLOAD": True,
        },
    ),
    tools=[tool.value for tool in McpServerPuppeteer],
)

PUPPETEER_AND_PLAYWRIGHT_MCP_SERVER_PROMPT = (
    "Open https://hub.docker.com/ and take a screenshot."
    "Capture the visible portion of the homepage (the default viewport)."
)

PUPPETEER_AND_PLAYWRIGHT_MCP_SERVER_EXPECTED_RESPONSE = """
    Here is a screenshot of the default homepage of https://hub.docker.com/
"""

# Parametrized test data for assistant with MCP servers
mcp_server_assistant_test_data = [
    MCPServerTestCase(
        mcp_server=SQLITE_MCP_SERVER,
        user_message=SQLITE_MCP_SERVER_PROMPT,
        expected_response=SQLITE_MCP_SERVER_EXPECTED_RESPONSE,
        expected_tools=[McpServerSqlite.CREATE_TABLE, McpServerSqlite.WRITE_QUERY],
    ),
    MCPServerTestCase(
        mcp_server=FILESYSTEM_MCP_SERVER,
        user_message=FILESYSTEM_MCP_SERVER_PROMPT,
        expected_response=FILESYSTEM_MCP_SERVER_EXPECTED_RESPONSE,
        expected_tools=[McpServerFilesystem.LIST_DIRECTORY],
    ),
    MCPServerTestCase(
        mcp_server=GITHUB_MCP_SERVER,
        user_message=GITHUB_TOOL_TASK,
        expected_response=RESPONSE_FOR_GITHUB,
        expected_tools=[McpServerGithub.GET_ISSUE],
        integration_fixture="github_mcp_integration",
    ),
    MCPServerTestCase(
        mcp_server=POSTGRESQL_MCP_SERVER,
        user_message=POSTGRESQL_MCP_SERVER_PROMPT,
        expected_response=POSTGRESQL_MCP_SERVER_EXPECTED_RESPONSE,
        expected_tools=[McpServerPostgresql.QUERY],
        integration_fixture="mcp_postgres_integration",
    ),
    MCPServerTestCase(
        mcp_server=PLAYWRIGHT_MCP_SERVER,
        user_message=PUPPETEER_AND_PLAYWRIGHT_MCP_SERVER_PROMPT,
        expected_response=PUPPETEER_AND_PLAYWRIGHT_MCP_SERVER_EXPECTED_RESPONSE,
        expected_tools=[
            McpServerPlaywright.BROWSER_NAVIGATE,
            McpServerPlaywright.BROWSER_SCREENSHOT,
        ],
    ),
    MCPServerTestCase(
        mcp_server=PUPPETEER_MCP_SERVER,
        user_message=PUPPETEER_AND_PLAYWRIGHT_MCP_SERVER_PROMPT,
        expected_response=PUPPETEER_AND_PLAYWRIGHT_MCP_SERVER_EXPECTED_RESPONSE,
        expected_tools=[
            McpServerPuppeteer.PUPPETEER_NAVIGATE,
            McpServerPuppeteer.PUPPETEER_SCREENSHOT,
        ],
    ),
]
