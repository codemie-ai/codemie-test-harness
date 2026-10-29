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
Tests for codemie CLI tool installation and claude command execution.

This test suite verifies:
1. Installation of @codemieai/code npm package
2. Configuration file creation
3. Claude provider installation
4. Command execution and response validation
5. File creation with task mode and permission handling
"""

import glob
import json
import os
import platform
import subprocess
import uuid
from pathlib import Path

import pytest
from hamcrest import (
    assert_that,
    equal_to,
    greater_than,
    is_not,
    greater_than_or_equal_to,
)

from codemie_test_harness.tests.utils.logger_util import setup_logger

logger = setup_logger(__name__)

# Get timeout from environment or use default
CLI_TIMEOUT = int(os.environ.get("DEFAULT_TIMEOUT", "60"))


@pytest.fixture(scope="session", autouse=True)
def setup_claude_provider(setup_codemie_base):
    """
    Install Claude provider using codemie's native installer.

    Process:
    1. Check if codemie-claude is already installed (which/where command)
    2. Use 'codemie install claude <version>' to install (uses native installer from claude.ai)
    3. Verify codemie-claude command is available with retry logic

    Environment variables:
    - SKIP_CLAUDE_INSTALL: Set to "true" to skip Claude installation
    - CLAUDE_VERSION: Specify Claude version to install (e.g., "2.1.29" or leave unset for "latest")

    Note: This uses 'codemie install claude' which downloads and runs the native installer
    from claude.ai (curl | bash), NOT npm. Creates 'codemie-claude' command.

    Depends on setup_codemie_base fixture from conftest.py.
    """
    skip_install = os.environ.get("SKIP_CLAUDE_INSTALL") == "true"
    claude_version = os.environ.get("CLAUDE_VERSION")

    if skip_install:
        logger.info("Skipping Claude installation (SKIP_CLAUDE_INSTALL=true)")
        return

    # Step 1: Prepare for Claude installation
    is_windows = platform.system() == "Windows"
    # Check for codemie-claude command (created by codemie install)
    check_cmd = (
        ["where", "codemie-claude"] if is_windows else ["which", "codemie-claude"]
    )

    logger.info("Preparing for Claude installation...")

    # Always uninstall first to ensure clean installation
    logger.info("Uninstalling any existing Claude installation...")
    uninstall_result = subprocess.run(
        ["codemie", "uninstall", "claude"],
        capture_output=True,
        text=True,
        timeout=CLI_TIMEOUT,
    )
    logger.info(f"Uninstall output: {uninstall_result.stdout}")

    # Also remove the actual claude binary (native installer creates this)
    # The native installer installs to ~/.local/bin/claude
    claude_binary_path = Path.home() / ".local" / "bin" / "claude"
    if claude_binary_path.exists():
        logger.info(f"Removing native claude binary: {claude_binary_path}")
        try:
            os.remove(claude_binary_path)
            logger.info("Native claude binary removed")
        except Exception as e:
            logger.warning(f"Failed to remove native claude binary: {e}")

    # Step 2: Install Claude with specified version using codemie install command
    # Use codemie install (native installer) instead of npm
    # codemie install uses the native installers from claude.ai (curl | bash)
    if not claude_version:
        # Use 'latest' if no version specified
        logger.info("No version specified, will install latest")
        claude_version = "latest"

    # Build codemie install command
    install_cmd = ["codemie", "install", "claude", claude_version]
    logger.info(f"Installing Claude provider version: {claude_version}")

    claude_install_result = subprocess.run(
        install_cmd,
        capture_output=True,
        text=True,
        input="Y\n",  # Answer 'Y' to reinstall prompt if it appears
        timeout=CLI_TIMEOUT,
    )

    if claude_install_result.returncode != 0:
        logger.warning(
            f"codemie install claude returned non-zero: {claude_install_result.stderr}"
        )

    logger.info(f"Claude install output: {claude_install_result.stdout}")

    # Step 3: Verify Claude is now available in PATH
    logger.info("Verifying Claude installation...")
    verify_result = subprocess.run(
        check_cmd,
        capture_output=True,
        text=True,
        timeout=10,
    )

    if verify_result.returncode == 0:
        logger.info(f"Claude verified at: {verify_result.stdout.strip()}")
    else:
        pytest.fail(
            f"Claude installation succeeded but codemie-claude command not found in PATH. "
            f"Installation output: {claude_install_result.stdout}"
        )


@pytest.mark.codemie_claude
def test_codemie_claude_task_with_file_creation(temp_test_dir):
    """

    Test codemie-claude command with task mode that creates a Java file.

    This test verifies:
    1. Command execution with --task and --permission-mode flags
    2. Handling of interactive version update prompts (answers 'Y')
    3. Creation of a Java HelloWorld file with unique UUID
    4. Session metrics validation with correct session file
    """
    # Generate unique UUID to track this test session
    test_uuid = str(uuid.uuid4())
    logger.info(f"Test UUID: {test_uuid}")

    # Run the command in the temporary directory with UUID in prompt
    result = subprocess.run(
        [
            "codemie-claude",
            "--task",
            f"Create java file with helloworld app that prints: {test_uuid}",
            "--permission-mode",
            "acceptEdits",
        ],
        cwd=temp_test_dir,
        capture_output=True,
        text=True,
        input="Y\n",  # Answer 'Y' to version update prompt if it appears
        timeout=CLI_TIMEOUT,  # 3x timeout for LLM-based file creation task
    )

    logger.info(f"Command stdout: {result.stdout}")
    logger.info(f"Command stderr: {result.stderr}")

    # Check that command completed successfully
    assert_that(
        result.returncode,
        equal_to(0),
        f"Command failed with stderr: {result.stderr}\nstdout: {result.stdout}",
    )

    # Find Java files in the temporary directory
    java_files = glob.glob(os.path.join(temp_test_dir, "*.java"))
    logger.info(f"Found Java files: {java_files}")

    # Verify at least one Java file was created
    assert_that(
        len(java_files),
        greater_than(0),
        f"No Java files were created in {temp_test_dir}. Directory contents: {os.listdir(temp_test_dir)}",
    )

    # Read the content of the first Java file
    java_file_path = java_files[0]
    with open(java_file_path, "r") as f:
        java_content = f.read()

    logger.info(f"Java file content:\n{java_content}")

    # Verify the file contains HelloWorld-related code
    # Check for common patterns in a HelloWorld Java program
    assert_that(
        java_content,
        is_not(""),
        f"Java file {java_file_path} is empty",
    )

    # Verify it's a valid Java file with typical HelloWorld patterns
    assert "class" in java_content.lower() or "public" in java_content.lower(), (
        f"Java file doesn't contain class definition: {java_content}"
    )

    logger.info(
        f"Test completed successfully. Java file created: {Path(java_file_path).name}"
    )

    # Step 4: Verify session metrics contain input tokens
    # Session files are stored in ~/.codemie/sessions/
    # Find the session that contains our test UUID
    logger.info(f"Searching for session containing UUID: {test_uuid}")

    home_dir = Path.home()
    sessions_dir = home_dir / ".codemie" / "sessions"

    assert_that(
        sessions_dir.exists(),
        equal_to(True),
        f"Sessions directory not found: {sessions_dir}",
    )

    # Search conversation files for the one containing our test UUID
    session_id = None
    for conversation_file in sessions_dir.glob("*_conversation.jsonl"):
        try:
            with open(conversation_file, "r") as cf:
                conversation_content = cf.read()
                if test_uuid in conversation_content:
                    # Extract session ID from filename (remove _conversation.jsonl suffix)
                    session_id = conversation_file.name.replace(
                        "_conversation.jsonl", ""
                    )
                    logger.info(f"Found matching session: {session_id}")
                    break
        except Exception as e:
            logger.debug(f"Error reading conversation file {conversation_file}: {e}")
            continue

    assert_that(
        session_id,
        is_not(None),
        f"Could not find session containing UUID {test_uuid} in {sessions_dir}",
    )

    # Now get the metrics file for this specific session
    metrics_file = sessions_dir / f"{session_id}_metrics.jsonl"

    assert_that(
        metrics_file.exists(),
        equal_to(True),
        f"Metrics file not found for session {session_id}: {metrics_file}",
    )

    logger.info(f"Found metrics file: {metrics_file}")

    # Read metrics JSONL file and sum up all token metrics
    total_input_tokens = 0
    total_output_tokens = 0
    total_cache_creation_tokens = 0
    total_cache_read_tokens = 0

    with open(metrics_file, "r") as mf:
        for line in mf:
            if line.strip():
                metric_delta = json.loads(line)
                tokens = metric_delta.get("tokens", {})
                total_input_tokens += tokens.get("input", 0)
                total_output_tokens += tokens.get("output", 0)
                total_cache_creation_tokens += tokens.get("cacheCreation", 0)
                total_cache_read_tokens += tokens.get("cacheRead", 0)

    logger.info("Token metrics from session:")
    logger.info(f"  - Input tokens: {total_input_tokens}")
    logger.info(f"  - Output tokens: {total_output_tokens}")
    logger.info(f"  - Cache creation tokens: {total_cache_creation_tokens}")
    logger.info(f"  - Cache read tokens: {total_cache_read_tokens}")

    # Assert that input tokens are not 0
    assert_that(
        total_input_tokens,
        greater_than(0),
        f"Input tokens should be greater than 0, but got: {total_input_tokens}",
    )

    # Output and cache tokens are expected to be 0 for now
    assert_that(
        total_output_tokens,
        greater_than(0),
        f"Output tokens expected to be 0 for now, but got: {total_output_tokens}",
    )

    assert_that(
        total_cache_creation_tokens,
        greater_than(0),
        f"Cache creation tokens expected to be 0, but got: {total_cache_creation_tokens}",
    )

    assert_that(
        total_cache_read_tokens,
        greater_than_or_equal_to(0),
        f"Cache read tokens expected to be 0, but got: {total_cache_read_tokens}",
    )
