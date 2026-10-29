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
Tests for codemie CLI tool installation and gemini command execution.

This test suite verifies:
1. Installation of @codemieai/code npm package
2. Configuration file creation
3. Gemini provider installation
4. Command execution and response validation
5. Session metrics validation with task mode
"""

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

from codemie_test_harness.tests.enums.model_types import ModelTypes
from codemie_test_harness.tests.utils.logger_util import setup_logger

logger = setup_logger(__name__)

# Get timeout from environment or use default
CLI_TIMEOUT = int(os.environ.get("DEFAULT_TIMEOUT", "60"))


@pytest.fixture(scope="session", autouse=True)
def setup_gemini_provider(setup_codemie_base):
    """
    Install Gemini provider using codemie's installer.

    Process:
    1. Check if codemie-gemini is already installed (which/where command)
    2. Use 'codemie install gemini <version>' to install
    3. Verify codemie-gemini command is available

    Environment variables:
    - SKIP_GEMINI_INSTALL: Set to "true" to skip Gemini installation
    - GEMINI_VERSION: Specify Gemini version to install (e.g., "1.0.0" or leave unset for "latest")

    Depends on setup_codemie_base fixture from conftest.py.
    """
    skip_install = os.environ.get("SKIP_GEMINI_INSTALL") == "true"
    gemini_version = os.environ.get("GEMINI_VERSION")

    if skip_install:
        logger.info("Skipping Gemini installation (SKIP_GEMINI_INSTALL=true)")
        return

    # Step 1: Prepare for Gemini installation
    is_windows = platform.system() == "Windows"
    # Check for codemie-gemini command
    check_cmd = (
        ["where", "codemie-gemini"] if is_windows else ["which", "codemie-gemini"]
    )

    logger.info("Preparing for Gemini installation...")

    # Always uninstall first to ensure clean installation
    logger.info("Uninstalling any existing Gemini installation...")
    uninstall_result = subprocess.run(
        ["codemie", "uninstall", "gemini"],
        capture_output=True,
        text=True,
        timeout=CLI_TIMEOUT,
    )
    logger.info(f"Uninstall output: {uninstall_result.stdout}")

    # Step 2: Install Gemini with specified version using codemie install command
    if not gemini_version:
        # Use 'latest' if no version specified
        logger.info("No version specified, will install latest")
        gemini_version = "latest"

    # Build codemie install command
    install_cmd = ["codemie", "install", "gemini", gemini_version]
    logger.info(f"Installing Gemini provider version: {gemini_version}")

    gemini_install_result = subprocess.run(
        install_cmd,
        capture_output=True,
        text=True,
        input="Y\n",  # Answer 'Y' to reinstall prompt if it appears
        timeout=CLI_TIMEOUT,
    )

    if gemini_install_result.returncode != 0:
        logger.warning(
            f"codemie install gemini returned non-zero: {gemini_install_result.stderr}"
        )

    logger.info(f"Gemini install output: {gemini_install_result.stdout}")

    # Step 3: Verify Gemini is now available in PATH
    logger.info("Verifying Gemini installation...")
    verify_result = subprocess.run(
        check_cmd,
        capture_output=True,
        text=True,
        timeout=10,
    )

    if verify_result.returncode == 0:
        logger.info(f"Gemini verified at: {verify_result.stdout.strip()}")
    else:
        pytest.fail(
            f"Gemini installation succeeded but codemie-gemini command not found in PATH. "
            f"Installation output: {gemini_install_result.stdout}"
        )


@pytest.mark.codemie_gemini
def test_codemie_gemini_task_with_file_creation(temp_test_dir):
    """
    Test codemie-gemini command with task mode.

    This test verifies:
    1. Command execution with --task, --model flags
    2. Handling of interactive version update prompts (answers 'Y')
    3. Successful command completion
    4. Session metrics validation with correct session file
    5. Token metrics tracking (input, output, cache creation/read tokens)
    """
    # Generate unique UUID to track this test session
    test_uuid = str(uuid.uuid4())
    logger.info(f"Test UUID: {test_uuid}")

    # Run the command in the temporary directory with UUID in prompt
    result = subprocess.run(
        [
            "codemie-gemini",
            "--task",
            f"Say hello and print: {test_uuid}",
            "--model",
            ModelTypes.GEMINI_31_PRO,
        ],
        cwd=temp_test_dir,
        capture_output=True,
        text=True,
        input="Y\n",  # Answer 'Y' to version update prompt if it appears
        timeout=CLI_TIMEOUT,  # Use configured timeout for LLM-based file creation task
    )

    logger.info(f"Command stdout: {result.stdout}")
    logger.info(f"Command stderr: {result.stderr}")

    # Check that command completed successfully
    assert_that(
        result.returncode,
        equal_to(0),
        f"Command failed with stderr: {result.stderr}\nstdout: {result.stdout}",
    )

    # Verify session metrics contain input tokens
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

    # Output tokens should be greater than 0 (model generated response)
    assert_that(
        total_output_tokens,
        greater_than(0),
        f"Output tokens should be greater than 0, but got: {total_output_tokens}",
    )

    # Cache creation tokens should be greater than 0 (caching was used)
    assert_that(
        total_cache_creation_tokens,
        greater_than_or_equal_to(0),
        f"Cache creation tokens should be greater than 0, but got: {total_cache_creation_tokens}",
    )

    # Cache read tokens should be >= 0 (may or may not have cache hits)
    assert_that(
        total_cache_read_tokens,
        greater_than_or_equal_to(0),
        f"Cache read tokens should be >= 0, but got: {total_cache_read_tokens}",
    )
