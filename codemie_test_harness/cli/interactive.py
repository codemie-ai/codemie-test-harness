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

"""Interactive mode for CodeMie Test Harness CLI."""

from __future__ import annotations

import os
import re
import subprocess
import sys

import questionary
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

from .constants import (
    TEST_SUITES,
    KEY_CODEMIE_API_DOMAIN,
    KEY_AUTH_SERVER_URL,
    KEY_AUTH_CLIENT_ID,
    KEY_AUTH_CLIENT_SECRET,
    KEY_AUTH_REALM_NAME,
    KEY_AUTH_USERNAME,
    KEY_AUTH_PASSWORD,
    KEY_AWS_ACCESS_KEY,
    KEY_AWS_SECRET_KEY,
    KEY_AWS_PROFILE,
    SENSITIVE_KEYS,
    mask_sensitive_value,
    CREDENTIAL_CATEGORIES,
)
from .utils import (
    load_config,
    set_config_value,
    ensure_env_from_config,
    unset_config_key,
)
from .runner import run_pytest
from .marks_utils import print_marks_list
from .commands.config_cmd import (
    _show_integration_configs,
    _list_integration_categories,
    _setup_integration_category,
    _validate_integrations,
)

# Main menu choices
MAIN_MENU_RUN = "🚀 Run Tests"
MAIN_MENU_CONFIG = "⚙️  Configuration"
MAIN_MENU_ASSISTANT = "🤖 Chat with Assistant"
MAIN_MENU_WORKFLOW = "🔄 Execute Workflow"
MAIN_MENU_HELP = "📚 Help & Guide"
MAIN_MENU_EXIT = "❌ Exit"

# Run submenu choices
RUN_MENU_SUITE = "📦 Run Test Suite (recommended)"
RUN_MENU_MARKS = "🏷️ Run with Custom Marks"
RUN_MENU_CLAUDE = "🧠 Run codemie-claude Tests"
RUN_MENU_GEMINI = "💎 Run codemie-gemini Tests"
RUN_MENU_BACK = "⬅️  Back to Main Menu"

# Questionary style
STYLE = questionary.Style(
    [
        ("qmark", "fg:#673ab7 bold"),  # question mark
        ("question", "bold"),  # question text
        ("answer", "fg:#00bcd4 bold"),  # submitted answer
        ("pointer", "fg:#673ab7 bold"),  # pointer used in select and checkbox prompts
        (
            "highlighted",
            "fg:#673ab7 bold",
        ),  # pointed-at choice in select and checkbox prompts
        ("selected", "fg:#00bcd4"),  # style for a selected item of a checkbox
        ("separator", "fg:#00bcd4"),  # separator in lists
        ("instruction", ""),  # user instructions for select, rawselect, checkbox
        ("text", ""),  # plain text
        (
            "disabled",
            "fg:#858585 italic",
        ),  # disabled choices for select and checkbox prompts
    ]
)


def _prompt_workers(default: int = 8) -> int | None:
    """Prompt user for number of parallel workers.

    Args:
        default: Default number of workers

    Returns:
        Number of workers or None if cancelled
    """
    workers = questionary.text(
        "Number of parallel workers:",
        default=str(default),
        validate=lambda text: text.isdigit()
        and int(text) > 0
        or "Must be a positive number",
    ).ask()

    if workers is None:
        return None

    return int(workers)


def _prompt_reruns(default: int = 2) -> int | None:
    """Prompt user for number of test reruns on failure.

    Args:
        default: Default number of reruns

    Returns:
        Number of reruns or None if cancelled
    """
    reruns = questionary.text(
        "Number of test reruns on failure:",
        default=str(default),
        validate=lambda text: text.isdigit()
        and int(text) >= 0
        or "Must be a non-negative number",
    ).ask()

    if reruns is None:
        return None

    return int(reruns)


def _collect_test_execution_params(
    marks: str,
    default_workers: int,
    default_reruns: int,
    description: str | None = None,
    suite_name: str | None = None,
) -> dict | None:
    """Collect test execution parameters and confirm execution.

    Args:
        marks: Pytest marks expression
        default_workers: Default number of workers
        default_reruns: Default number of reruns
        description: Optional description for suite
        suite_name: Optional suite name for display

    Returns:
        Dict with workers, marks, reruns, or None if cancelled
    """
    console = Console()

    # Prompt for workers and reruns
    workers = _prompt_workers(default=default_workers)
    if workers is None:
        return None

    reruns = _prompt_reruns(default=default_reruns)
    if reruns is None:
        return None

    # Display execution summary
    if suite_name:
        console.print(
            f"\n[bold green]Running test suite:[/bold green] [cyan]{suite_name}[/cyan]"
        )
        if description:
            console.print(f"[dim]Description:[/dim] {description}")
    else:
        console.print("\n[bold green]Running tests with custom marks:[/bold green]")

    console.print(f"[dim]Marks:[/dim] {marks}")
    console.print(f"[dim]Workers:[/dim] {workers}")
    console.print(f"[dim]Reruns:[/dim] {reruns}\n")

    # Confirm execution
    confirm = questionary.confirm(
        "Proceed with test execution?",
        default=True,
        style=STYLE,
    ).ask()

    if not confirm:
        console.print("[yellow]Test execution cancelled.[/yellow]\n")
        return None

    return {
        "workers": workers,
        "marks": marks,
        "reruns": reruns,
    }


def _execute_tests(params: dict, suite_config: dict | None = None) -> None:
    """Execute tests with the given parameters.

    Args:
        params: Dict with workers, marks, reruns
        suite_config: Optional suite configuration dict that may contain env vars
    """
    console = Console()

    # Load configuration into environment before running tests
    ensure_env_from_config()

    # Get suite-specific pytest arguments (e.g., --ui-headless)
    suite_pytest_args = []
    if suite_config and "pytest_args" in suite_config:
        suite_pytest_args = suite_config["pytest_args"]
        console.print(f"[dim]Suite pytest args: {' '.join(suite_pytest_args)}[/dim]")

    # Run tests
    try:
        run_pytest(
            workers=params["workers"],
            marks=params["marks"],
            reruns=params["reruns"],
            count=None,
            timeout=300,
            extra=(*suite_pytest_args, *([] if suite_config else ["--no-gate"])),
        )
    except SystemExit:
        # pytest exits with sys.exit, catch it to return to menu
        pass

    console.print("\n[green]Test execution completed![/green]")
    questionary.press_any_key_to_continue("Press any key to return to menu...").ask()


def run_interactive_mode() -> None:
    """Run the interactive CLI mode."""
    console = Console()

    console.print(
        "\n[bold cyan]╔═══════════════════════════════════════════════╗[/bold cyan]"
    )
    console.print(
        "[bold cyan]║    CodeMie Test Harness - Interactive Mode    ║[/bold cyan]"
    )
    console.print(
        "[bold cyan]╚═══════════════════════════════════════════════╝[/bold cyan]\n"
    )

    while True:
        try:
            choice = questionary.select(
                "What would you like to do?",
                choices=[
                    MAIN_MENU_RUN,
                    MAIN_MENU_CONFIG,
                    MAIN_MENU_ASSISTANT,
                    MAIN_MENU_WORKFLOW,
                    MAIN_MENU_HELP,
                    MAIN_MENU_EXIT,
                ],
                style=STYLE,
            ).ask()

            if choice is None or choice == MAIN_MENU_EXIT:
                console.print("\n[yellow]👋 Goodbye![/yellow]\n")
                sys.exit(0)
            elif choice == MAIN_MENU_RUN:
                _run_tests_interactive()
            elif choice == MAIN_MENU_CONFIG:
                _config_interactive()
            elif choice == MAIN_MENU_ASSISTANT:
                _assistant_interactive()
            elif choice == MAIN_MENU_WORKFLOW:
                _workflow_interactive()
            elif choice == MAIN_MENU_HELP:
                _show_help()

        except KeyboardInterrupt:
            console.print("\n\n[yellow]👋 Goodbye![/yellow]\n")
            sys.exit(0)


def _run_tests_interactive() -> None:
    """Interactive test execution."""
    console = Console()

    # Show contextual help
    console.print(
        "\n[dim italic]💡 Tip: Test suites are pre-configured with optimized settings."
    )
    console.print(
        "[dim italic]   Custom marks allow fine-grained test selection with pytest expressions.[/dim italic]\n"
    )

    choice = questionary.select(
        "How would you like to run tests?",
        choices=[
            RUN_MENU_SUITE,
            RUN_MENU_MARKS,
            RUN_MENU_CLAUDE,
            RUN_MENU_GEMINI,
            RUN_MENU_BACK,
        ],
        style=STYLE,
    ).ask()

    if choice is None or choice == RUN_MENU_BACK:
        return

    if choice == RUN_MENU_SUITE:
        _run_suite_interactive()
    elif choice == RUN_MENU_MARKS:
        _run_marks_interactive()
    elif choice == RUN_MENU_CLAUDE:
        _run_codemie_claude_interactive()
    elif choice == RUN_MENU_GEMINI:
        _run_codemie_gemini_interactive()


def _run_suite_interactive() -> None:
    """Interactive test suite selection and execution."""
    console = Console()

    # Show contextual help for test suites
    console.print("\n[dim italic]💡 Test Suite Guide:[/dim italic]")
    console.print("[dim italic]   • sanity: Fastest (DevOps CI/CD)[/dim italic]")
    console.print(
        "[dim italic]   • smoke: Quick validation for local development (5-10 min)[/dim italic]"
    )
    console.print(
        "[dim italic]   • smoke-api: Quick validation for API critical path (5-10 min)[/dim italic]"
    )
    console.print(
        "[dim italic]   • smoke-ui: Quick validation for UI critical path (5-10 min)[/dim italic]"
    )
    console.print(
        "[dim italic]   • api: Full API regression testing (30-45 min)[/dim italic]"
    )
    console.print(
        "[dim italic]   • ui: UI testing with Playwright browsers (20-30 min)[/dim italic]\n"
    )

    # Build choices with descriptions in preferred order
    suite_order = [
        "sanity",
        "sanity-api",
        "sanity-ui",
        "smoke",
        "smoke-api",
        "smoke-ui",
        "api",
        "enterprise",
        "opensource",
        "ui",
    ]
    suite_choices = []

    for suite_name in suite_order:
        if suite_name in TEST_SUITES:
            config = TEST_SUITES[suite_name]
            choice = questionary.Choice(
                title=f"{suite_name:12} - {config['description']}", value=suite_name
            )
            suite_choices.append(choice)

    suite_choices.append(questionary.Choice(title="⬅️  Back", value="__back__"))

    # Select suite
    suite = questionary.select(
        "Select a test suite:",
        choices=suite_choices,
        style=STYLE,
    ).ask()

    if suite is None or suite == "__back__":
        return

    suite_config = TEST_SUITES[suite]

    # Collect execution parameters
    params = _collect_test_execution_params(
        marks=suite_config["marks"],
        default_workers=suite_config["workers"],
        default_reruns=suite_config["reruns"],
        description=suite_config["description"],
        suite_name=suite,
    )

    if params is None:
        return

    # Execute tests
    _execute_tests(params, suite_config)


def _run_marks_interactive() -> None:
    """Interactive custom marks execution."""
    console = Console()

    # Show contextual help for custom marks
    console.print("\n[dim italic]💡 Custom Marks Guide:[/dim italic]")
    console.print(
        "[dim italic]   • Use logical operators: 'and', 'or', 'not', parentheses[/dim italic]"
    )
    console.print(
        "[dim italic]   • Examples: 'api and gitlab', 'jira or confluence', 'smoke and not ui'[/dim italic]"
    )
    console.print(
        "[dim italic]   • Common marks: api, smoke, gitlab, jira, confluence, ui, mcp[/dim italic]\n"
    )

    # Ask if user wants to view available marks first
    view_marks = questionary.confirm(
        "Do you want to view available marks first?",
        default=True,
        style=STYLE,
    ).ask()

    if view_marks:
        # Ask for view format
        view_choice = questionary.select(
            "Select marks view format:",
            choices=[
                questionary.Choice("📋 List view (simple)", value="list"),
                questionary.Choice("📊 Table view (with file details)", value="table"),
            ],
            style=STYLE,
        ).ask()

        if view_choice is None:
            return

        console.print()
        show_files = view_choice == "table"
        print_marks_list(show_files=show_files)
        console.print()

    marks = questionary.text(
        "Enter pytest marks expression:",
        default="api",
        instruction="(e.g., 'api', 'smoke and gitlab', 'jira or confluence')",
    ).ask()

    if marks is None:
        return

    # Collect execution parameters
    params = _collect_test_execution_params(
        marks=marks,
        default_workers=8,
        default_reruns=2,
    )

    if params is None:
        return

    # Execute tests
    _execute_tests(params)


def _run_codemie_claude_interactive() -> None:
    """Interactive codemie-claude test execution with installation options."""
    console = Console()

    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]    Codemie-Claude Test Configuration    [/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")

    # Step 1: Ask about @codemieai/code installation
    console.print("[bold]Step 1: @codemieai/code Installation[/bold]\n")
    install_codemie_code = questionary.confirm(
        "Install @codemieai/code npm package?",
        default=True,
        style=STYLE,
    ).ask()

    if install_codemie_code is None:
        return

    codemie_install_method = None
    codemie_custom_path = None

    if install_codemie_code:
        # Ask for installation method
        codemie_install_method = questionary.select(
            "Choose installation method:",
            choices=[
                questionary.Choice("📦 Install from npm (recommended)", value="npm"),
                questionary.Choice("📁 Install from custom local path", value="local"),
            ],
            style=STYLE,
        ).ask()

        if codemie_install_method is None:
            return

        if codemie_install_method == "local":
            codemie_custom_path = questionary.path(
                "Enter the path to @codemieai/code package:",
                only_directories=True,
            ).ask()

            if codemie_custom_path is None:
                return

            console.print(f"[dim]Will install from:[/dim] {codemie_custom_path}\n")
    else:
        console.print("[yellow]⚠️ Skipping @codemieai/code installation[/yellow]\n")

    # Step 2: Ask about Claude installation
    console.print("[bold]Step 2: Claude Provider Installation[/bold]\n")

    # Get latest Claude version from npm (default)
    default_claude_version = "latest"
    try:
        result = subprocess.run(
            ["npm", "view", "@anthropic-ai/claude-code", "version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            default_claude_version = result.stdout.strip()
    except Exception:
        pass

    # Ask for Claude version (editable)
    claude_version = questionary.text(
        "Install Claude version (leave empty to skip):",
        default=default_claude_version,
        instruction="(edit version or clear to skip, e.g. '2.1.29')",
    ).ask()

    if claude_version is None:
        return

    # Empty string means skip installation
    claude_version = claude_version.strip()

    if not claude_version:
        console.print("[yellow]⚠️ Skipping Claude installation[/yellow]\n")
        install_claude = False
    else:
        install_claude = True
        console.print(f"[dim]Will install Claude version:[/dim] {claude_version}\n")

    # Step 3: Confirm and execute
    console.print("[bold]Step 3: Test Execution[/bold]\n")

    # Display execution summary
    console.print("[bold green]Running codemie-claude tests:[/bold green]")
    console.print(
        "[dim]Description:[/dim] Tests for codemie-claude CLI with file creation"
    )
    console.print("[dim]Marks:[/dim] codemie_claude")
    console.print("[dim]Parallel workers:[/dim] None (sequential execution)")
    console.print("[dim]Reruns:[/dim] 0 (no retries)\n")

    # Confirm execution
    confirm = questionary.confirm(
        "Proceed with test execution?",
        default=True,
        style=STYLE,
    ).ask()

    if not confirm:
        console.print("[yellow]Test execution cancelled.[/yellow]\n")
        return

    # Set environment variables for fixtures to use
    if not install_codemie_code:
        os.environ["SKIP_CODEMIE_CODE_INSTALL"] = "true"
    else:
        os.environ.pop("SKIP_CODEMIE_CODE_INSTALL", None)
        if codemie_install_method == "local":
            os.environ["CODEMIE_CODE_INSTALL_PATH"] = codemie_custom_path

    if not install_claude:
        os.environ["SKIP_CLAUDE_INSTALL"] = "true"
    else:
        os.environ.pop("SKIP_CLAUDE_INSTALL", None)
        if claude_version and claude_version != "latest":
            os.environ["CLAUDE_VERSION"] = claude_version

    # Load configuration into environment before running tests
    ensure_env_from_config()

    # Run tests sequentially without reruns
    try:
        run_pytest(
            workers=0,  # No parallel workers (sequential execution)
            marks="codemie_claude",
            reruns=0,  # No reruns
            count=None,
            timeout=300,
            extra=(),
        )
    except SystemExit:
        # pytest exits with sys.exit, catch it to return to menu
        pass

    console.print("\n[green]Test execution completed![/green]")
    questionary.press_any_key_to_continue("Press any key to return to menu...").ask()

    # Clean up environment variables
    os.environ.pop("SKIP_CODEMIE_CODE_INSTALL", None)
    os.environ.pop("CODEMIE_CODE_INSTALL_PATH", None)
    os.environ.pop("SKIP_CLAUDE_INSTALL", None)
    os.environ.pop("CLAUDE_VERSION", None)


def _run_codemie_gemini_interactive() -> None:
    """Interactive codemie-gemini test execution with installation options."""
    console = Console()

    console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]    Codemie-Gemini Test Configuration    [/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")

    # Step 1: Ask about @codemieai/code installation
    console.print("[bold]Step 1: @codemieai/code Installation[/bold]\n")
    install_codemie_code = questionary.confirm(
        "Install @codemieai/code npm package?",
        default=True,
        style=STYLE,
    ).ask()

    if install_codemie_code is None:
        return

    codemie_install_method = None
    codemie_custom_path = None

    if install_codemie_code:
        # Ask for installation method
        codemie_install_method = questionary.select(
            "Choose installation method:",
            choices=[
                questionary.Choice("📦 Install from npm (recommended)", value="npm"),
                questionary.Choice("📁 Install from custom local path", value="local"),
            ],
            style=STYLE,
        ).ask()

        if codemie_install_method is None:
            return

        if codemie_install_method == "local":
            codemie_custom_path = questionary.path(
                "Enter the path to @codemieai/code package:",
                only_directories=True,
            ).ask()

            if codemie_custom_path is None:
                return

            console.print(f"[dim]Will install from:[/dim] {codemie_custom_path}\n")
    else:
        console.print("[yellow]⚠️ Skipping @codemieai/code installation[/yellow]\n")

    # Step 2: Ask about Gemini installation
    console.print("[bold]Step 2: Gemini Provider Installation[/bold]\n")

    # Get latest Gemini version from npm (default)
    default_gemini_version = "latest"
    try:
        result = subprocess.run(
            ["npm", "view", "@google/gemini-cli-core", "version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            default_gemini_version = result.stdout.strip()
    except Exception:
        pass

    # Ask for Gemini version (editable)
    gemini_version = questionary.text(
        "Install Gemini version (leave empty to skip):",
        default=default_gemini_version,
        instruction="(edit version or clear to skip, e.g. '1.0.0')",
    ).ask()

    if gemini_version is None:
        return

    # Empty string means skip installation
    gemini_version = gemini_version.strip()

    if not gemini_version:
        console.print("[yellow]⚠️ Skipping Gemini installation[/yellow]\n")
        install_gemini = False
    else:
        install_gemini = True
        console.print(f"[dim]Will install Gemini version:[/dim] {gemini_version}\n")

    # Step 3: Confirm and execute
    console.print("[bold]Step 3: Test Execution[/bold]\n")

    # Display execution summary
    console.print("[bold green]Running codemie-gemini tests:[/bold green]")
    console.print(
        "[dim]Description:[/dim] Tests for codemie-gemini CLI with task execution and session metrics"
    )
    console.print("[dim]Marks:[/dim] codemie_gemini")
    console.print("[dim]Parallel workers:[/dim] None (sequential execution)")
    console.print("[dim]Reruns:[/dim] 0 (no retries)\n")

    # Confirm execution
    confirm = questionary.confirm(
        "Proceed with test execution?",
        default=True,
        style=STYLE,
    ).ask()

    if not confirm:
        console.print("[yellow]Test execution cancelled.[/yellow]\n")
        return

    # Set environment variables for fixtures to use
    if not install_codemie_code:
        os.environ["SKIP_CODEMIE_CODE_INSTALL"] = "true"
    else:
        os.environ.pop("SKIP_CODEMIE_CODE_INSTALL", None)
        if codemie_install_method == "local":
            os.environ["CODEMIE_CODE_INSTALL_PATH"] = codemie_custom_path

    if not install_gemini:
        os.environ["SKIP_GEMINI_INSTALL"] = "true"
    else:
        os.environ.pop("SKIP_GEMINI_INSTALL", None)
        if gemini_version and gemini_version != "latest":
            os.environ["GEMINI_VERSION"] = gemini_version

    # Load configuration into environment before running tests
    ensure_env_from_config()

    # Run tests sequentially without reruns
    try:
        run_pytest(
            workers=0,  # No parallel workers (sequential execution)
            marks="codemie_gemini",
            reruns=0,  # No reruns
            count=None,
            timeout=300,
            extra=(),
        )
    except SystemExit:
        # pytest exits with sys.exit, catch it to return to menu
        pass

    console.print("\n[green]Test execution completed![/green]")
    questionary.press_any_key_to_continue("Press any key to return to menu...").ask()

    # Clean up environment variables
    os.environ.pop("SKIP_CODEMIE_CODE_INSTALL", None)
    os.environ.pop("CODEMIE_CODE_INSTALL_PATH", None)
    os.environ.pop("SKIP_GEMINI_INSTALL", None)
    os.environ.pop("GEMINI_VERSION", None)


def _is_localhost_domain(domain: str) -> bool:
    """Check if the domain is a localhost domain."""
    if not domain:
        return False

    # Remove protocol and trailing slashes
    domain = domain.replace("http://", "").replace("https://", "").rstrip("/")

    # Localhost patterns
    localhost_patterns = [
        r"^localhost(:\d+)?$",
        r"^127\.0\.0\.1(:\d+)?$",
        r"^192\.168\.\d{1,3}\.\d{1,3}(:\d+)?$",
    ]

    for pattern in localhost_patterns:
        if re.match(pattern, domain, re.IGNORECASE):
            return True

    return False


def _get_aws_profiles() -> list[str]:
    """Get list of AWS profiles from ~/.aws/credentials file."""
    credentials_path = os.path.expanduser("~/.aws/credentials")

    if not os.path.exists(credentials_path):
        return []

    profiles = []
    try:
        with open(credentials_path, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("[") and line.endswith("]"):
                    profile = line[1:-1]  # Remove brackets
                    profiles.append(profile)
    except Exception:
        return []

    return profiles


def _create_aws_profile(profile_name: str, access_key: str, secret_key: str) -> bool:
    """Create a new AWS profile in ~/.aws/credentials file.

    Args:
        profile_name: Name of the AWS profile
        access_key: AWS access key ID
        secret_key: AWS secret access key

    Returns:
        True if profile was created successfully, False otherwise
    """
    credentials_path = os.path.expanduser("~/.aws/credentials")
    aws_dir = os.path.dirname(credentials_path)

    try:
        # Create ~/.aws directory if it doesn't exist
        if not os.path.exists(aws_dir):
            os.makedirs(aws_dir, mode=0o700)

        # Check if profile already exists
        existing_profiles = _get_aws_profiles()
        if profile_name in existing_profiles:
            return False

        # Append new profile to credentials file
        with open(credentials_path, "a") as f:
            # Add newline before profile if file exists and is not empty
            if os.path.getsize(credentials_path) > 0:
                f.write("\n")

            f.write(f"[{profile_name}]\n")
            f.write(f"aws_access_key_id = {access_key}\n")
            f.write(f"aws_secret_access_key = {secret_key}\n")

        # Set appropriate permissions
        os.chmod(credentials_path, 0o600)
        return True

    except Exception:
        return False


def _configure_aws_credentials(
    console: Console, allow_skip: bool = False
) -> dict | None:
    """Configure AWS credentials with various options.

    Args:
        console: Rich console for output
        allow_skip: If True, shows "Skip" option; if False, shows "Remove" option

    Returns:
        Dict with aws_profile/aws_access_key/aws_secret_key or None if cancelled/skipped
    """
    # Get existing AWS profiles
    existing_profiles = _get_aws_profiles()

    # Build choices based on context
    aws_choices = []
    if existing_profiles:
        aws_choices.append(
            questionary.Choice("📁 Use existing AWS profile", value="use_profile")
        )
    aws_choices.append(
        questionary.Choice("➕ Create new AWS profile", value="create_profile")
    )
    aws_choices.append(
        questionary.Choice("🔑 Enter access keys directly", value="enter_keys")
    )

    if allow_skip:
        aws_choices.append(
            questionary.Choice("⏭️  Skip AWS configuration", value="skip")
        )
    else:
        aws_choices.append(
            questionary.Choice("🗑️ Remove AWS credentials", value="remove")
        )

    aws_choices.append(questionary.Choice("⬅️  Back", value="back"))

    aws_choice = questionary.select(
        "How would you like to configure AWS Parameter Store credentials? (used only when HARNESS_SECRET_STORE=aws-parameter-store)",
        choices=aws_choices,
        style=STYLE,
    ).ask()

    if aws_choice is None or aws_choice == "back" or aws_choice == "skip":
        return None

    if aws_choice == "use_profile" and existing_profiles:
        # User wants to use existing profile
        aws_profile = questionary.select(
            "Select AWS profile:",
            choices=existing_profiles,
            style=STYLE,
        ).ask()

        if aws_profile:
            set_config_value(KEY_AWS_PROFILE, aws_profile)
            # Remove direct keys if they exist (mutual exclusivity)
            unset_config_key(KEY_AWS_ACCESS_KEY)
            unset_config_key(KEY_AWS_SECRET_KEY)
            console.print(
                f"\n[green]✓[/green] AWS profile '[cyan]{aws_profile}[/cyan]' configured\n"
            )
            return {"aws_profile": aws_profile}

    elif aws_choice == "create_profile":
        # User wants to create a new profile
        console.print("\n[cyan]Creating new AWS profile in ~/.aws/credentials[/cyan]\n")

        new_profile_name = questionary.text(
            "Profile name:",
            default="default",
            instruction="(e.g., default, codemie, dev)",
        ).ask()

        if new_profile_name and new_profile_name.strip():
            new_profile_name = new_profile_name.strip()

            # Check if profile already exists
            if new_profile_name in existing_profiles:
                console.print(
                    f"\n[red]✗[/red] Profile '[cyan]{new_profile_name}[/cyan]' already exists\n"
                )
                return None

            aws_access_key = questionary.text(
                "AWS Access Key ID:",
            ).ask()

            if aws_access_key:
                aws_secret_key = questionary.password(
                    "AWS Secret Access Key:",
                ).ask()

                if aws_access_key and aws_secret_key:
                    # Create the profile
                    if _create_aws_profile(
                        new_profile_name, aws_access_key, aws_secret_key
                    ):
                        set_config_value(KEY_AWS_PROFILE, new_profile_name)
                        # Remove direct keys if they exist (mutual exclusivity)
                        unset_config_key(KEY_AWS_ACCESS_KEY)
                        unset_config_key(KEY_AWS_SECRET_KEY)
                        console.print(
                            f"\n[green]✓[/green] AWS profile '[cyan]{new_profile_name}[/cyan]' created and configured\n"
                        )
                        return {"aws_profile": new_profile_name}
                    else:
                        console.print("\n[red]✗[/red] Failed to create AWS profile\n")
                        return None

    elif aws_choice == "enter_keys":
        # User wants to enter keys directly (stored in test harness JSON)
        console.print(
            "\n[cyan]Storing AWS credentials in test harness configuration[/cyan]\n"
        )

        aws_access_key = questionary.text(
            "AWS Access Key ID:",
        ).ask()

        if aws_access_key:
            aws_secret_key = questionary.password(
                "AWS Secret Access Key:",
            ).ask()

            if aws_access_key and aws_access_key.strip():
                set_config_value(KEY_AWS_ACCESS_KEY, aws_access_key)
            if aws_secret_key and aws_secret_key.strip():
                set_config_value(KEY_AWS_SECRET_KEY, aws_secret_key)

            # Remove profile if it exists (mutual exclusivity)
            unset_config_key(KEY_AWS_PROFILE)

            console.print(
                "\n[green]✓[/green] AWS access keys configured in test harness\n"
            )
            return {"aws_access_key": aws_access_key, "aws_secret_key": aws_secret_key}

    elif aws_choice == "remove":
        # Remove all AWS credentials
        unset_config_key(KEY_AWS_PROFILE)
        unset_config_key(KEY_AWS_ACCESS_KEY)
        unset_config_key(KEY_AWS_SECRET_KEY)
        console.print("\n[green]✓[/green] AWS credentials removed from configuration\n")
        return {}

    return None


def _configure_api_domain() -> str | None:
    """Configure CodeMie API domain.

    Returns:
        API domain or None if cancelled
    """
    console = Console()

    console.print("[bold]Step 1: CodeMie API Domain[/bold]")

    # Predefined environments
    env_urls = {"localhost": "http://localhost:8080"}
    choices = [
        questionary.Choice("Localhost - http://localhost:8080", value="localhost")
    ]
    choices.append(questionary.Choice("Custom - Enter URL manually", value="custom"))
    env_choice = questionary.select(
        "Select environment:",
        choices=choices,
        style=STYLE,
    ).ask()

    if env_choice is None:
        console.print("\n[yellow]Setup cancelled.[/yellow]\n")
        return None

    if env_choice == "custom":
        # Custom URL input
        api_domain = questionary.text(
            "Enter custom API domain URL:",
            instruction="(e.g., https://your-custom-domain.com/api)",
        ).ask()

        if api_domain is None:
            console.print("\n[yellow]Setup cancelled.[/yellow]\n")
            return None
    else:
        # Use predefined URL
        api_domain = env_urls[env_choice]

    # Save API domain (only if not empty)
    if api_domain and api_domain.strip():
        set_config_value(KEY_CODEMIE_API_DOMAIN, api_domain)
        console.print(f"[green]✓[/green] Environment: [cyan]{env_choice}[/cyan]")
        console.print(f"[green]✓[/green] API domain saved: [cyan]{api_domain}[/cyan]\n")
        return api_domain
    else:
        console.print("\n[yellow]Setup cancelled - API domain is required.[/yellow]\n")
        return None


def _configure_authentication(is_localhost: bool) -> dict | None:
    """Configure authentication settings.

    Args:
        is_localhost: Whether API domain is localhost

    Returns:
        Dict with auth settings or empty dict for localhost, None if cancelled
    """
    console = Console()

    if is_localhost:
        console.print("\n[bold green]✓ Localhost detected![/bold green]")
        console.print(
            "[dim]Authentication setup is not required for localhost.[/dim]\n"
        )
        return {}

    # Step 2/3: Authentication setup (only for non-localhost)
    console.print("\n[bold]Step 2: Authentication Configuration[/bold]")
    console.print("[dim]Required for non-localhost environments[/dim]\n")

    # Auth Server URL
    auth_server_url = questionary.text(
        "Auth Server URL:",
        instruction="(e.g., https://auth.example.com/)",
    ).ask()

    if auth_server_url is None:
        console.print("\n[yellow]Setup cancelled.[/yellow]\n")
        return None

    # Auth Client ID
    auth_client_id = questionary.text(
        "Auth Client ID:", instruction="(your Keycloak client ID)"
    ).ask()

    if auth_client_id is None:
        console.print("\n[yellow]Setup cancelled.[/yellow]\n")
        return None

    # Auth Realm Name
    auth_realm_name = questionary.text(
        "Auth Realm Name:",
        instruction="(e.g., my-realm)",
    ).ask()

    if auth_realm_name is None:
        console.print("\n[yellow]Setup cancelled.[/yellow]\n")
        return None

    # Auth Client Secret
    auth_client_secret = questionary.password(
        "Auth Client Secret:",
        instruction="(can be empty if using username/password authentication)",
    ).ask()

    if auth_client_secret is None:
        console.print("\n[yellow]Setup cancelled.[/yellow]\n")
        return None

    # Ask if user wants to use username/password (optional)
    use_user_pass = questionary.confirm(
        "Do you want to configure username/password authentication?",
        default=True,
        style=STYLE,
    ).ask()

    auth_username = None
    auth_password = None
    if use_user_pass:
        auth_username = questionary.text(
            "Auth Username:",
        ).ask()

        if auth_username:
            auth_password = questionary.password(
                "Auth Password:",
            ).ask()

    # Save all auth settings (only non-empty values)
    if auth_server_url and auth_server_url.strip():
        set_config_value(KEY_AUTH_SERVER_URL, auth_server_url)
    if auth_client_id and auth_client_id.strip():
        set_config_value(KEY_AUTH_CLIENT_ID, auth_client_id)
    if auth_client_secret and auth_client_secret.strip():
        set_config_value(KEY_AUTH_CLIENT_SECRET, auth_client_secret)
    if auth_realm_name and auth_realm_name.strip():
        set_config_value(KEY_AUTH_REALM_NAME, auth_realm_name)

    if auth_username and auth_username.strip():
        set_config_value(KEY_AUTH_USERNAME, auth_username)
    if auth_password and auth_password.strip():
        set_config_value(KEY_AUTH_PASSWORD, auth_password)

    return {
        "auth_server_url": auth_server_url,
        "auth_client_id": auth_client_id,
        "auth_client_secret": auth_client_secret,
        "auth_realm_name": auth_realm_name,
        "auth_username": auth_username,
        "auth_password": auth_password,
    }


def _display_setup_summary(
    api_domain: str,
    is_localhost: bool,
    auth_config: dict | None,
    aws_config: dict | None,
) -> None:
    """Display setup configuration summary.

    Args:
        api_domain: The configured API domain
        is_localhost: Whether API domain is localhost
        auth_config: Authentication configuration dict
        aws_config: AWS configuration dict
    """
    console = Console()

    console.print("\n[bold cyan]Configuration Complete![/bold cyan]\n")
    console.print("[green]✓[/green] API Domain: [cyan]{}[/cyan]".format(api_domain))

    if is_localhost:
        console.print("[green]✓[/green] Auth: [cyan]Skipped (localhost)[/cyan]")
    elif auth_config:
        if auth_config.get("auth_server_url"):
            console.print(
                "[green]✓[/green] Auth Server: [cyan]{}[/cyan]".format(
                    auth_config["auth_server_url"]
                )
            )
        if auth_config.get("auth_client_id"):
            console.print(
                "[green]✓[/green] Client ID: [cyan]{}[/cyan]".format(
                    auth_config["auth_client_id"]
                )
            )
        if auth_config.get("auth_client_secret"):
            console.print(
                "[green]✓[/green] Client Secret: [cyan]{}[/cyan]".format(
                    mask_sensitive_value(auth_config["auth_client_secret"])
                )
            )
        if auth_config.get("auth_realm_name"):
            console.print(
                "[green]✓[/green] Realm: [cyan]{}[/cyan]".format(
                    auth_config["auth_realm_name"]
                )
            )
        if auth_config.get("auth_username"):
            console.print(
                "[green]✓[/green] Username: [cyan]{}[/cyan]".format(
                    auth_config["auth_username"]
                )
            )
        if auth_config.get("auth_password"):
            console.print(
                "[green]✓[/green] Password: [cyan]{}[/cyan]".format(
                    mask_sensitive_value(auth_config["auth_password"])
                )
            )

    if aws_config:
        if "aws_profile" in aws_config:
            console.print(
                "[green]✓[/green] AWS Profile: [cyan]{}[/cyan]".format(
                    aws_config["aws_profile"]
                )
            )
        if "aws_access_key" in aws_config and aws_config["aws_access_key"].strip():
            console.print(
                "[green]✓[/green] AWS Access Key: [cyan]{}[/cyan]".format(
                    mask_sensitive_value(aws_config["aws_access_key"])
                )
            )
        if "aws_secret_key" in aws_config and aws_config["aws_secret_key"].strip():
            console.print(
                "[green]✓[/green] AWS Secret Key: [cyan]{}[/cyan]".format(
                    mask_sensitive_value(aws_config["aws_secret_key"])
                )
            )

    console.print("\n[dim]Configuration saved to: ~/.codemie/test-harness.json[/dim]\n")


def _config_interactive() -> None:
    """Interactive configuration management."""
    console = Console()

    while True:
        # Show contextual help for configuration
        console.print("\n[dim italic]💡 Configuration Guide:[/dim italic]")
        console.print(
            "[dim italic]   • Setup: Quick wizard for API domain, auth, and optional AWS Parameter Store credentials[/dim italic]"
        )
        console.print(
            "[dim italic]   • AWS Management: Parameter Store credentials, used only when HARNESS_SECRET_STORE=aws-parameter-store[/dim italic]"
        )
        console.print(
            "[dim italic]   • Integrations: Configure GitLab, JIRA, Confluence, etc.[/dim italic]"
        )
        console.print(
            "[dim italic]   • Config stored in: ~/.codemie/test-harness.json[/dim italic]\n"
        )

        choices = [
            "📋 List Settings",
            "⚙️  Setup (Quick Configuration)",
            "🔐 AWS Management",
            "🔌 Integrations Management",
            "✏️  Set Specific Value",
            "🔍 Get Specific Value",
            "🗑️ Unset Specific Value",
            "⬅️  Back to Main Menu",
        ]

        choice = questionary.select(
            "Configuration options:",
            choices=choices,
            style=STYLE,
        ).ask()

        if choice is None or choice == "⬅️  Back to Main Menu":
            return

        if choice == "📋 List Settings":
            _config_list_settings()
        elif choice == "⚙️  Setup (Quick Configuration)":
            _config_setup_wizard()
        elif choice == "🔐 AWS Management":
            _config_aws_management()
        elif choice == "🔌 Integrations Management":
            _config_integrations_management()
        elif choice == "✏️  Set Specific Value":
            _config_set_value()
        elif choice == "🔍 Get Specific Value":
            _config_get_value()
        elif choice == "🗑️ Unset Specific Value":
            _config_unset_value()


def _config_aws_management() -> None:
    """Manage AWS credentials configuration."""
    console = Console()

    console.print("\n[bold cyan]AWS Credentials Management[/bold cyan]")
    console.print(
        "[dim]Configure AWS credentials for accessing AWS Parameter Store[/dim]"
    )
    console.print("[dim]Not required for Sanity tests[/dim]\n")

    result = _configure_aws_credentials(console, allow_skip=False)

    # Only show "press any key" if user completed an action (not cancelled/back)
    if result is not None:
        questionary.press_any_key_to_continue("Press any key to continue...").ask()


def _config_integrations_management() -> None:
    """Manage integration credentials configuration."""
    console = Console()

    while True:
        console.print("\n[bold cyan]Integrations Management[/bold cyan]")
        console.print(
            "[dim]Manage credentials for GitLab, Jira, Confluence, and more[/dim]"
        )
        console.print(
            "[dim italic]💡 Tip: With AWS configured, integrations load automatically from Parameter Store[/dim italic]\n"
        )

        choice = questionary.select(
            "What would you like to do?",
            choices=[
                questionary.Choice("📋 View Current Integrations", value="view"),
                questionary.Choice("📂 View Categories", value="categories"),
                questionary.Choice("⚙️  Setup by Category", value="setup"),
                questionary.Choice("✅  Validate Integrations", value="validate"),
                questionary.Choice("⬅️  Back", value="back"),
            ],
            style=STYLE,
        ).ask()

        if choice is None or choice == "back":
            return

        if choice == "view":
            # View current integrations
            show_values = questionary.confirm(
                "Show real values (instead of masked)?",
                default=False,
                style=STYLE,
            ).ask()

            if show_values is None:
                continue

            _show_integration_configs(show_real=show_values)
            questionary.press_any_key_to_continue(
                "\nPress any key to continue..."
            ).ask()

        elif choice == "categories":
            # View available categories
            _list_integration_categories()
            questionary.press_any_key_to_continue(
                "\nPress any key to continue..."
            ).ask()

        elif choice == "setup":
            # Setup by category
            _list_integration_categories()
            console.print()

            # Build category choices
            category_choices = [
                questionary.Choice(
                    f"{info['name']} - {info['description']}", value=category_id
                )
                for category_id, info in CREDENTIAL_CATEGORIES.items()
            ]
            category_choices.append(questionary.Choice("⬅️  Back", value="back"))

            selected_category = questionary.select(
                "Select category to configure:",
                choices=category_choices,
                style=STYLE,
            ).ask()

            if selected_category and selected_category != "back":
                _setup_integration_category(selected_category)
                questionary.press_any_key_to_continue(
                    "\nPress any key to continue..."
                ).ask()

        elif choice == "validate":
            # Validate integrations
            console.print("\n[cyan]Validating integrations...[/cyan]\n")
            results = _validate_integrations()

            # Display results
            table = Table(title="Integration Validation Results")
            table.add_column("Category", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Configured", justify="right")
            table.add_column("Missing", justify="right")

            for category_name, status in results.items():
                configured_count = len(status["configured"])
                missing_count = len(status["missing"])
                total_count = configured_count + missing_count

                if configured_count == total_count and total_count > 0:
                    status_str = "[green]✓ Complete[/green]"
                elif configured_count > 0:
                    status_str = "[yellow]⚠ Partial[/yellow]"
                else:
                    status_str = "[dim]○ Not configured[/dim]"

                table.add_row(
                    category_name,
                    status_str,
                    str(configured_count),
                    str(missing_count),
                )

            console.print(table)
            questionary.press_any_key_to_continue(
                "\nPress any key to continue..."
            ).ask()


def _config_list_settings() -> None:
    """Display all configured settings."""
    console = Console()
    config = load_config()

    if not config:
        console.print("\n[yellow]No configuration found.[/yellow]")
        console.print("[dim]Run 'Setup' to configure the test harness.[/dim]\n")
        questionary.press_any_key_to_continue("Press any key to continue...").ask()
        return

    console.print("\n[bold cyan]Current Configuration:[/bold cyan]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan", width=35)
    table.add_column("Value", style="green", width=80)

    # Sort config by key
    for key in sorted(config.keys()):
        value = config[key]
        # Mask sensitive values
        if key in SENSITIVE_KEYS:
            display_value = mask_sensitive_value(str(value))
        else:
            display_value = str(value)

        table.add_row(key, display_value)

    console.print(table)
    console.print(f"\n[dim]Total: {len(config)} settings configured[/dim]")
    console.print("[dim]Config file: ~/.codemie/test-harness.json[/dim]\n")

    questionary.press_any_key_to_continue("Press any key to continue...").ask()


def _config_setup_wizard() -> None:
    """Interactive setup wizard for quick configuration."""
    console = Console()

    console.print(
        "\n[bold cyan]╔═══════════════════════════════════════════════╗[/bold cyan]"
    )
    console.print(
        "[bold cyan]║        Quick Configuration Setup Wizard       ║[/bold cyan]"
    )
    console.print(
        "[bold cyan]╚═══════════════════════════════════════════════╝[/bold cyan]\n"
    )

    # Step 1: API Domain Configuration
    api_domain = _configure_api_domain()
    if api_domain is None:
        questionary.press_any_key_to_continue("Press any key to continue...").ask()
        return

    # Step 2: Authentication Configuration
    is_localhost = _is_localhost_domain(api_domain)
    auth_config = _configure_authentication(is_localhost)
    if auth_config is None:
        questionary.press_any_key_to_continue("Press any key to continue...").ask()
        return

    # Step 3: AWS Credentials (optional)
    aws_step_number = "2" if is_localhost else "3"
    console.print(f"\n[bold]Step {aws_step_number}: AWS Credentials (Optional)[/bold]")
    console.print(
        "[dim]Required only if you need to access AWS Parameter Store for additional configuration[/dim]"
    )
    console.print("[dim]Not required for Sanity tests[/dim]\n")

    configure_aws = questionary.confirm(
        "Do you want to configure AWS credentials?",
        default=True,
        style=STYLE,
    ).ask()

    aws_config = None
    if configure_aws:
        aws_config = _configure_aws_credentials(console, allow_skip=True)

    # Display Summary
    _display_setup_summary(api_domain, is_localhost, auth_config, aws_config)

    questionary.press_any_key_to_continue("Press any key to continue...").ask()


def _config_set_value() -> None:
    """Set a single configuration value."""
    console = Console()

    key = questionary.text(
        "Enter configuration key:", instruction="(e.g., GITLAB_TOKEN, AWS_PROFILE)"
    ).ask()

    if key is None:
        return

    # Check if it's a sensitive key to use password input
    if key in SENSITIVE_KEYS:
        value = questionary.password(
            f"Enter value for {key}:",
        ).ask()
    else:
        value = questionary.text(
            f"Enter value for {key}:",
        ).ask()

    if value is None:
        return

    # Only save non-empty values
    if value and value.strip():
        set_config_value(key, value)

        # Show masked value for sensitive keys
        display_value = mask_sensitive_value(value) if key in SENSITIVE_KEYS else value

        console.print(
            f"\n[green]✓[/green] Configuration saved: [cyan]{key}[/cyan] = [yellow]{display_value}[/yellow]\n"
        )
    else:
        console.print(f"\n[yellow]Empty value not saved for {key}[/yellow]\n")

    questionary.press_any_key_to_continue("Press any key to continue...").ask()


def _config_get_value() -> None:
    """Get a specific configuration value."""
    console = Console()

    key = questionary.text(
        "Enter configuration key:",
        instruction="(e.g., CODEMIE_API_DOMAIN, AUTH_CLIENT_ID)",
    ).ask()

    if key is None:
        return

    config = load_config()

    if key in config:
        value = config[key]
        display_value = (
            mask_sensitive_value(str(value)) if key in SENSITIVE_KEYS else str(value)
        )
        console.print(f"\n[cyan]{key}[/cyan] = [yellow]{display_value}[/yellow]\n")
    else:
        console.print(
            f"\n[yellow]Configuration key '[cyan]{key}[/cyan]' not found.[/yellow]\n"
        )

    questionary.press_any_key_to_continue("Press any key to continue...").ask()


def _config_unset_value() -> None:
    """Unset (remove) a specific configuration value."""
    console = Console()

    config = load_config()

    if not config:
        console.print("\n[yellow]No configuration found.[/yellow]\n")
        questionary.press_any_key_to_continue("Press any key to continue...").ask()
        return

    # Show available keys
    console.print("\n[bold]Current configuration keys:[/bold]")
    for key in sorted(config.keys()):
        console.print(f"  [cyan]{key}[/cyan]")
    console.print()

    key = questionary.text(
        "Enter configuration key to remove:",
        instruction="(e.g., GITLAB_TOKEN, AWS_PROFILE)",
    ).ask()

    if key is None:
        return

    if key in config:
        # Confirm deletion
        confirm = questionary.confirm(
            f"Are you sure you want to remove '[cyan]{key}[/cyan]'?",
            default=False,
            style=STYLE,
        ).ask()

        if confirm:
            if unset_config_key(key):
                console.print(
                    f"\n[green]✓[/green] Configuration key '[cyan]{key}[/cyan]' removed.\n"
                )
            else:
                console.print(
                    f"\n[red]✗[/red] Failed to remove '[cyan]{key}[/cyan]'.\n"
                )
        else:
            console.print("\n[yellow]Removal cancelled.[/yellow]\n")
    else:
        console.print(
            f"\n[yellow]Configuration key '[cyan]{key}[/cyan]' not found.[/yellow]\n"
        )

    questionary.press_any_key_to_continue("Press any key to continue...").ask()


def _assistant_interactive() -> None:
    """Interactive assistant chat."""
    console = Console()

    assistant_id = questionary.text(
        "Enter Assistant ID:", instruction="(e.g., 'asst_123')"
    ).ask()

    if assistant_id is None:
        return

    message = questionary.text(
        "Enter your message:",
        multiline=True,
    ).ask()

    if message is None:
        return

    console.print("\n[yellow]To chat with assistant, run:[/yellow]")
    console.print(
        f'[cyan]codemie-test-harness assistant chat --assistant-id {assistant_id} -m "{message}"[/cyan]\n'
    )
    questionary.press_any_key_to_continue("Press any key to continue...").ask()


def _workflow_interactive() -> None:
    """Interactive workflow execution."""
    console = Console()

    workflow_id = questionary.text(
        "Enter Workflow ID:", instruction="(e.g., 'wf_123')"
    ).ask()

    if workflow_id is None:
        return

    user_input = questionary.text(
        "Enter user input (optional):",
        default="",
    ).ask()

    console.print("\n[yellow]To execute workflow, run:[/yellow]")

    if user_input:
        console.print(
            f'[cyan]codemie-test-harness workflow execute --workflow-id {workflow_id} --user-input "{user_input}"[/cyan]\n'
        )
    else:
        console.print(
            f"[cyan]codemie-test-harness workflow execute --workflow-id {workflow_id}[/cyan]\n"
        )

    questionary.press_any_key_to_continue("Press any key to continue...").ask()


def _show_help() -> None:
    """Display help and guide from README."""
    console = Console()

    help_content = """
# CodeMie Test Harness - Quick Guide

## Overview

End-to-end, integration, and UI test suite for CodeMie services. Test LLM assistants,
workflows, tools, and integrations with this user-friendly CLI.

## Navigation Tips

- **Arrow Keys**: Navigate menu options
- **Enter**: Select an option
- **Ctrl+C**: Cancel/Exit at any time
- **Back Options**: Every submenu has a "Back" option to return
- **Smart Defaults**: Pre-filled values for common configurations
- **Validation**: Input validation prevents invalid values

## Quick Start

**First time?** Select **Configuration → Setup** and follow the prompts.

**Running tests?** Choose **Run Tests → Run Test Suite → smoke** for a quick 5-10 minute validation.

## Configuration Overview

### Setup Wizard

The setup wizard guides you through three steps:

1. **API Domain** - Select environment (Localhost, Preview, Production, or Custom)
2. **Authentication** - Configure auth settings (auto-skipped for localhost)
3. **AWS Credentials** (Optional) - Required for most test suites, except `sanity`

### AWS Credentials

AWS credentials enable automatic loading of integration settings from Parameter Store.

**When do you need AWS?**
- ✅ **Required**: `smoke`, `api`, `ui`, `opensource`, `enterprise` suites
- ⏭️ **Not required**: `sanity` suite (no integrations)

**Options:**
- Use existing AWS profile from ~/.aws/credentials
- Create new AWS profile (saved securely)
- Enter access keys directly
- Skip (for sanity tests only)

### Integrations

Manage credentials for 86+ integration variables across 10 categories:
- Version Control (GitLab, GitHub)
- Project Management (JIRA, Confluence)
- Cloud Providers (AWS, Azure, GCP)
- Code Quality (SonarQube, SonarCloud)
- DevOps (Azure DevOps)
- And more...

**Navigate to:** Configuration → Integrations Management

## Running Tests

### Test Suites

Choose from 6 predefined test suites:

| Suite | Time | Use Case |
|-------|------|----------|
| **sanity** | ~2 min | DevOps CI/CD (no AWS required) |
| **smoke** | 5-10 min | Local development |
| **api** | 30-45 min | Full API regression |
| **ui** | 20-30 min | UI testing with Playwright |
| **opensource** | 25-35 min | Non-enterprise features |
| **enterprise** | 15-25 min | Enterprise features only |

### Custom Marks

Run tests with custom pytest marks expressions:

**Examples:**
- `api` - API integration tests
- `smoke and api` - Quick API tests
- `jira or confluence` - Project management tests
- `api and not ui` - API tests excluding UI
- `(gitlab or github) and code_kb` - Version control with code knowledge base

**View all marks:** Use the marks view option when running with custom marks

## Configuration File

All settings are stored in: `~/.codemie/test-harness.json`

**Priority order:**
1. CLI flags (highest)
2. Environment variables
3. Configuration file
4. AWS Parameter Store
5. Default values (lowest)

**Reset configuration:**
```bash
rm ~/.codemie/test-harness.json
codemie-test-harness  # Start fresh
```

## Common Commands (CLI)

```bash
# Interactive mode
codemie-test-harness

# Quick test runs
codemie-test-harness run sanity     # Fastest
codemie-test-harness run smoke      # Quick
codemie-test-harness run api        # Full

# Configuration
codemie-test-harness config list    # View settings
codemie-test-harness marks          # List marks
```

## Support

For detailed documentation, see the full README.md in the repository.
"""

    console.print("\n")
    console.print(
        Panel(
            Markdown(help_content),
            title="[bold cyan]Help & Guide[/bold cyan]",
            border_style="cyan",
            expand=False,
        )
    )
    console.print("\n")

    questionary.press_any_key_to_continue("Press any key to return to menu...").ask()
