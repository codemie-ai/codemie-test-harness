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
Common fixtures for codemie CLI tests.

Provides shared fixtures for configuration and setup.
"""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from codemie_test_harness.tests import CredentialsManager
from codemie_test_harness.tests.enums.model_types import ModelTypes
from codemie_test_harness.tests.utils.logger_util import setup_logger

logger = setup_logger(__name__)

# Get timeout from environment or use default
CLI_TIMEOUT = int(os.environ.get("DEFAULT_TIMEOUT", "60"))


@pytest.fixture(scope="session")
def codemie_config_dir():
    """Get the .codemie config directory path using OS utilities."""
    home_dir = Path.home()
    config_dir = home_dir / ".codemie"
    return config_dir


@pytest.fixture(scope="session")
def config_file_path(codemie_config_dir):
    """Get the codemie-cli.config.json file path."""
    return codemie_config_dir / "codemie-cli.config.json"


@pytest.fixture(scope="session")
def config_data(config_file_path):
    """
    Get the configuration data for codemie CLI with LiteLLM test profile.

    This fixture:
    - Reads existing config if it exists
    - Adds/updates "LiteLLMTest" profile with LiteLLM configuration
    - Sets activeProfile to "LiteLLMTest"
    """
    # Default config structure
    base_config = {
        "version": 2,
        "activeProfile": "sso-autotest",
        "profiles": {},
    }

    # Read existing config if it exists
    if config_file_path.exists():
        logger.info(f"Reading existing config from {config_file_path}")
        with open(config_file_path, "r") as f:
            existing_config = json.load(f)
            # Preserve existing config structure
            base_config = existing_config
    else:
        logger.info("No existing config found, creating new config")

    # Add/update LiteLLMTest profile
    base_config["profiles"]["sso-autotest"] = {
        "name": "sso-autotest",
        "provider": "ai-run-sso",
        "authMethod": "sso",
        "codeMieUrl": CredentialsManager.get_parameter("FRONTEND_URL"),
        "baseUrl": CredentialsManager.get_parameter("CODEMIE_API_DOMAIN"),
        "apiKey": "sso-authenticated",
        "model": ModelTypes.CLAUDE_4_5_SONNET.value,
        "timeout": 300,
        "debug": False,
    }

    # Set activeProfile to LiteLLMTest
    base_config["activeProfile"] = "sso-autotest"

    return base_config


@pytest.fixture(scope="session")
def setup_codemie_base(codemie_config_dir, config_file_path, config_data, request):
    """
    Set up base codemie CLI infrastructure.

    This fixture:
    1. Installs @codemieai/code npm package globally
    2. Creates .codemie directory
    3. Reads existing config or creates new one
    4. Adds/updates LiteLLMTest profile
    5. Sets activeProfile to LiteLLMTest
    6. After tests finish, restores original activeProfile

    Note: Config file and profiles are preserved after tests.
    Only activeProfile is restored to its original value.
    """
    # Store original activeProfile before modifying config
    original_active_profile = None
    if config_file_path.exists():
        with open(config_file_path, "r") as config_file:
            existing_config = json.load(config_file)
            original_active_profile = existing_config.get("activeProfile")
            logger.info(f"Stored original activeProfile: {original_active_profile}")
    else:
        logger.info("No existing config found, no original activeProfile to restore")

    # Step 1: Install @codemieai/code npm package globally
    skip_install = os.environ.get("SKIP_CODEMIE_CODE_INSTALL") == "true"
    custom_path = os.environ.get("CODEMIE_CODE_INSTALL_PATH")

    if skip_install:
        logger.info(
            "Skipping @codemieai/code installation (SKIP_CODEMIE_CODE_INSTALL=true)"
        )
    else:
        if custom_path:
            logger.info(f"Installing @codemieai/code from custom path: {custom_path}")

            # Step 1: npm install
            logger.info("Running npm install...")
            npm_install_result = subprocess.run(
                ["npm", "install"],
                cwd=custom_path,
                capture_output=True,
                text=True,
                timeout=CLI_TIMEOUT,
            )
            if npm_install_result.returncode != 0:
                pytest.fail(f"Failed to run npm install: {npm_install_result.stderr}")
            logger.info(f"npm install output: {npm_install_result.stdout}")

            # Step 2: npm run build && npm link
            logger.info("Running npm run build && npm link...")
            build_link_result = subprocess.run(
                ["sh", "-c", "npm run build && npm link"],
                cwd=custom_path,
                capture_output=True,
                text=True,
                timeout=CLI_TIMEOUT,
            )
            if build_link_result.returncode != 0:
                pytest.fail(f"Failed to build and link: {build_link_result.stderr}")
            logger.info(f"Build and link output: {build_link_result.stdout}")
        else:
            logger.info("Installing @codemieai/code npm package from registry...")
            install_result = subprocess.run(
                ["npm", "install", "-g", "@codemieai/code"],
                capture_output=True,
                text=True,
                timeout=CLI_TIMEOUT,
            )
            if install_result.returncode != 0:
                pytest.fail(
                    f"Failed to install @codemieai/code: {install_result.stderr}"
                )
            logger.info(f"npm install output: {install_result.stdout}")

    # Step 2: Create .codemie directory if it doesn't exist
    logger.info(f"Creating config directory: {codemie_config_dir}")
    codemie_config_dir.mkdir(parents=True, exist_ok=True)

    # Step 3: Write config with LiteLLMTest profile
    logger.info(f"Writing config file with LiteLLMTest profile: {config_file_path}")
    with open(config_file_path, "w") as config_file:
        json.dump(config_data, config_file, indent=2)

    logger.info("Base codemie CLI setup completed with LiteLLMTest profile")

    # Yield to run tests
    yield

    # Step 4: Restore original activeProfile after tests finish
    def restore_active_profile():
        if original_active_profile is not None and config_file_path.exists():
            logger.info(f"Restoring original activeProfile: {original_active_profile}")
            with open(config_file_path, "r") as config_file:
                current_config = json.load(config_file)
            current_config["activeProfile"] = original_active_profile
            with open(config_file_path, "w") as config_file:
                json.dump(current_config, config_file, indent=2)
            logger.info(f"activeProfile restored to: {original_active_profile}")
        else:
            logger.info(
                "No original activeProfile to restore or config file doesn't exist"
            )

    # Register finalizer to restore activeProfile
    request.addfinalizer(restore_active_profile)


@pytest.fixture
def temp_test_dir():
    """
    Create a temporary directory for test execution and clean it up afterwards.

    Yields:
        str: Path to the temporary directory
    """
    temp_dir = tempfile.mkdtemp(prefix="codemie_test_")
    logger.info(f"Created temporary directory: {temp_dir}")

    yield temp_dir

    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        logger.info(f"Cleaned up temporary directory: {temp_dir}")
