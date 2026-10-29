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

"""Command for installing Playwright browsers."""

import subprocess
import click
from rich.console import Console


def _check_browser_installed(browser):
    """Check if a specific browser is already installed."""
    try:
        # Try to run playwright show to check installed browsers
        result = subprocess.run(
            ["playwright", "show"], capture_output=True, text=True, timeout=10
        )

        if result.returncode == 0:
            # Check if the browser is mentioned in the output
            output = result.stdout.lower()
            if browser == "all":
                # Check if all major browsers are installed
                return all(b in output for b in ["chromium", "firefox", "webkit"])
            else:
                return browser.lower() in output
    except Exception:
        pass
    return False


@click.command(name="install-browsers")
@click.option(
    "--browser",
    type=click.Choice(["chromium", "firefox", "webkit", "all"]),
    default="chromium",
    help="Browser to install (default: chromium)",
)
@click.option("--force", is_flag=True, help="Force reinstall even if already installed")
def browsers_cmd(browser, force):
    """Install Playwright browsers for UI testing.

    This is needed for UI tests to work. Browsers are auto-installed on first run,
    but you can manually install them with this command.

    \b
    Examples:
        codemie-test-harness install-browsers
        codemie-test-harness install-browsers --browser all
        codemie-test-harness install-browsers --browser firefox
        codemie-test-harness install-browsers --force
    """
    console = Console()

    try:
        # Check if already installed (unless --force)
        if not force and _check_browser_installed(browser):
            console.print(
                f"\n[green]✓ {browser.capitalize()} browser(s) already installed[/green]"
            )
            console.print("[dim]Use --force to reinstall[/dim]\n")
            return

        console.print(f"\n[cyan]Installing Playwright {browser} browser(s)...[/cyan]")

        if browser == "all":
            cmd = ["playwright", "install"]
        else:
            cmd = ["playwright", "install", browser]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            console.print(
                f"[green]✓ Successfully installed {browser} browser(s)[/green]\n"
            )
            if result.stdout:
                console.print(f"[dim]{result.stdout}[/dim]")
        else:
            console.print("[red]✗ Failed to install browsers[/red]")
            if result.stderr:
                console.print(f"[red]{result.stderr}[/red]")
            raise SystemExit(1)

    except FileNotFoundError:
        console.print(
            "[red]✗ Playwright CLI not found. Make sure playwright is installed:[/red]"
        )
        console.print("[yellow]  pip install playwright[/yellow]\n")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]\n")
        raise SystemExit(1)
