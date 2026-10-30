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

import os
import subprocess
import sys
from datetime import datetime
from importlib.util import find_spec
from time import sleep

import pytest
from codemie_sdk.models.conversation import ConversationCreateRequest
from codemie_sdk.models.skill import SkillVisibility
from requests import HTTPError

from codemie_test_harness.rp_guard import get_rp_logger, log_with_attachment
from codemie_test_harness.tests.ui import conversation_ids
from codemie_test_harness.tests.ui.pageobject.login_page import LoginPage
from codemie_test_harness.tests.ui.test_data.links_names_test_data import AssistantNames
from codemie_test_harness.tests.ui.test_data.mcp_catalog_test_data import (
    catalog_server_with_one_env_var,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver
from codemie_test_harness.tests.utils.logger_util import setup_logger

logger = setup_logger(__name__)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook to capture test results"""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)


@pytest.fixture(autouse=True)
def screenshot_on_failure(request, page):
    """Capture screenshot on test failure"""
    yield
    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_name = request.node.name

        # Create screenshots directory
        screenshot_dir = "test_screenshots"
        os.makedirs(screenshot_dir, exist_ok=True)

        # Capture screenshot
        screenshot_file_path = os.path.join(
            screenshot_dir, f"failure_{test_name}_{timestamp}.png"
        )

        page.screenshot(path=screenshot_file_path, full_page=True)
        with open(screenshot_file_path, "rb") as image_file:
            file_data = image_file.read()
            log_with_attachment(
                get_rp_logger(request.config),
                f"Test failed - Screenshot captured: {test_name}",
                {
                    "name": f"{test_name}_failure_screenshot.png",
                    "data": file_data,
                    "mime": "image/png",
                },
            )


@pytest.fixture(autouse=True)
def login(page):
    login_page = LoginPage(page)
    user = get_client().users.about_me()
    frontend_url = os.getenv("FRONTEND_URL", "")
    login_page.login_suppressing_popups(
        os.getenv("AUTH_USERNAME"),
        os.getenv("AUTH_PASSWORD"),
        user.user_id,
        frontend_url,
    )


@pytest.fixture(scope="session", autouse=True)
def browser_context_args(browser_context_args):
    width = int(os.getenv("VIEWPORT_WIDTH", 1920))
    height = int(os.getenv("VIEWPORT_HEIGHT", 1080))
    return {
        **browser_context_args,
        "viewport": {
            "width": width,
            "height": height,
        },
        "ignore_https_errors": True,
    }


@pytest.fixture(scope="session")
def base_url():
    return os.getenv("FRONTEND_URL")


@pytest.fixture(scope="function")
def create_new_conversation():
    conversation = get_client().conversations.create(
        ConversationCreateRequest(folder="")
    )
    yield conversation
    try:
        get_client().conversations.delete(conversation.get("id"))
    except HTTPError:
        pass


@pytest.fixture(scope="function", autouse=True)
def cleanup_faq_assistant_conversations():
    """Delete all conversations for AI/Run FAQ assistant after each test."""
    yield
    client = get_client()
    assistants = client.assistants.list(
        filters={"search": AssistantNames.AI_RUN_FAQ}, per_page=200, scope="marketplace"
    )
    assistant = next(
        (a for a in assistants if a.name == AssistantNames.AI_RUN_FAQ), None
    )
    if assistant:
        conversations = client.conversations.list_by_assistant_id(assistant.id)
        for conversation in conversations:
            try:
                client.conversations.delete(conversation.id)
            except Exception:
                pass


@pytest.fixture(scope="session", autouse=True)
def ensure_playwright_browsers():
    """Ensure Playwright browsers are installed (auto-install if missing)."""
    try:
        # Check if playwright package is installed
        if find_spec("playwright") is None:
            logger.error("[Playwright] Playwright package not found")
            raise ImportError("Playwright not installed. Run: pip install playwright")

        # Check if browsers are already installed
        check_result = subprocess.run(
            ["playwright", "show"], capture_output=True, text=True, timeout=10
        )

        if check_result.returncode == 0 and "chromium" in check_result.stdout.lower():
            logger.info("[Playwright] Browsers already installed")
            return

        # Browsers not installed, install them
        logger.warning("[Playwright] Browsers not found, installing chromium...")
        install_result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True,
        )

        if install_result.returncode == 0:
            logger.info("[Playwright] Browsers installed successfully")
        else:
            logger.error(
                f"[Playwright] Failed to install browsers: {install_result.stderr}"
            )
            raise RuntimeError(
                "Playwright browsers installation failed. "
                "Run manually: codemie-test-harness install-browsers"
            )

    except FileNotFoundError:
        logger.error("[Playwright] Playwright CLI not found")
        raise ImportError("Playwright not installed. Run: pip install playwright")
    except Exception as e:
        logger.error(f"[Playwright] Browser check failed: {str(e)}")
        logger.warning(
            "[Playwright] Continuing anyway, tests may fail if browsers missing"
        )


@pytest.fixture(scope="session")
def browser_type_launch_args(request):
    """Configure browser launch arguments.

    Control via:
    - pytest.ini: addopts = --ui-headless
    - Command line: pytest --ui-headless or --ui-headed
    - IDE: Add --ui-headed to Additional Arguments
    - Suite config: Automatically adds --ui-headless for smoke suites

    Default: headed mode (browser visible) for development
    """
    ui_headless_flag = request.config.getoption("--ui-headless")
    ui_headed_flag = request.config.getoption("--ui-headed")

    if ui_headed_flag:
        headless_bool = False
        source = "--ui-headed"
    elif ui_headless_flag:
        headless_bool = True
        source = "--ui-headless"
    else:
        headless_bool = False  # Default: headed mode for development
        source = "default (headed)"

    logger.info(
        f"[Playwright] Browser mode: {'HEADLESS' if headless_bool else 'HEADED'} (from {source})"
    )

    return {
        "headless": headless_bool,
        "slow_mo": 400,
    }


@pytest.fixture
def skill_in_other_project(project, skill_utils):
    """Skill in a freshly created project: project visibility, not published, so it is
    absent from the Skills catalog of the default project. Deleted on teardown."""
    skill_name = get_random_name().replace("_", "-")
    skill, _ = skill_utils.send_create_skill_request(
        skill_name=skill_name,
        project_name=project().name,
        visibility=SkillVisibility.PROJECT,
    )
    yield skill
    try:
        skill_utils.delete_skill_by_id(skill.id)
    except Exception as e:
        logger.warning(f"Failed to delete skill {skill.id}: {e}")


@pytest.fixture
def catalog_server(client):
    """Form data of a throwaway MCP catalog server.

    The test creates the server through the Administration UI; on teardown every config
    with exactly this name is deleted through the API, each delete logged on failure.
    """
    server = catalog_server_with_one_env_var()
    yield server
    try:
        configs = client.mcp_configs.list(search=server.name, per_page=100)
    except Exception as e:
        logger.warning(f"Failed to list MCP configs named {server.name}: {e}")
        return
    for config in configs:
        if config.name != server.name:
            continue
        try:
            client.mcp_configs.delete(config.id)
        except Exception as e:
            logger.warning(
                f"Failed to delete MCP config {config.id} ({config.name}): {e}"
            )


def pytest_sessionfinish(session):
    """Run cleanup code after all tests have finished."""
    clean_up_timeout = 1 if EnvironmentResolver.is_production() else 0
    client = get_client()
    for conversation_id in conversation_ids:
        client.conversations.delete(conversation_id)
        sleep(clean_up_timeout)
