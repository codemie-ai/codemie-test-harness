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

from __future__ import annotations
import click
from rich.table import Table
from typing import Dict, List
from ..constants import (
    CONSOLE,
    CREDENTIAL_CATEGORIES,
    mask_sensitive_value,
    is_sensitive_key,
    INTEGRATION_KEYS,
)
from ..utils import (
    load_config,
    get_config_value,
    set_config_value,
    save_config,
    unset_config_key,
)


# Helper functions (moved from integrations_manager.py)
def _get_integration_category(key: str) -> str:
    """Get the integration category name for a configuration key."""
    for category_id, category_info in CREDENTIAL_CATEGORIES.items():
        if key in category_info["keys"]:
            return category_info["name"]
    return "Unknown"


def _show_integration_configs(category: str = None, show_real: bool = False) -> None:
    """Display current integration configurations in a formatted table."""
    config = load_config()
    if not config:
        CONSOLE.print("[yellow]No integration configurations found[/]")
        return

    # Filter configurations based on category parameter
    if category:
        if category in CREDENTIAL_CATEGORIES:
            keys_to_show = CREDENTIAL_CATEGORIES[category]["keys"]
            filtered_config = {k: v for k, v in config.items() if k in keys_to_show}
        else:
            CONSOLE.print(f"[red]Unknown integration category: {category}[/]")
            return
    else:
        # Show all integration configurations
        filtered_config = {k: v for k, v in config.items() if k in INTEGRATION_KEYS}

    if not filtered_config:
        CONSOLE.print(
            "[yellow]No integration configurations found for the specified criteria[/]"
        )
        return

    # Create formatted table for display
    title = "Integration Configurations" + (
        " (Real Values)" if show_real else " (Masked Values)"
    )
    table = Table(title=title)
    table.add_column("Configuration Key", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Integration Category", style="blue")

    for key, value in sorted(filtered_config.items()):
        display_value = (
            mask_sensitive_value(str(value), show_real=show_real)
            if is_sensitive_key(key)
            else str(value)
        )
        category_name = _get_integration_category(key)
        table.add_row(key, display_value, category_name)

    CONSOLE.print(table)


def _list_integration_categories() -> None:
    """Display all available integration categories in a formatted table."""
    table = Table(title="Available Integration Categories")
    table.add_column("Category ID", style="cyan")
    table.add_column("Category Name", style="green")
    table.add_column("Description", style="blue")
    table.add_column("Config Keys", style="dim", justify="right")

    for category_id, category_info in CREDENTIAL_CATEGORIES.items():
        table.add_row(
            category_id,
            category_info["name"],
            category_info["description"],
            str(len(category_info["keys"])),
        )

    CONSOLE.print(table)


def _validate_integrations() -> Dict[str, Dict[str, List[str]]]:
    """Validate all configured integrations and return detailed status."""
    config = load_config()
    validation_results = {}

    for category_id, category_info in CREDENTIAL_CATEGORIES.items():
        configured_keys = []
        missing_keys = []

        for config_key in category_info["keys"]:
            if config and config_key in config and config[config_key]:
                configured_keys.append(config_key)
            else:
                missing_keys.append(config_key)

        validation_results[category_info["name"]] = {
            "configured": configured_keys,
            "missing": missing_keys,
        }

    return validation_results


def _setup_integration_category(category: str) -> None:
    """Interactively configure all settings for a specific integration category."""
    if category not in CREDENTIAL_CATEGORIES:
        CONSOLE.print(f"[red]Unknown integration category: {category}[/]")
        return

    category_info = CREDENTIAL_CATEGORIES[category]
    CONSOLE.print(f"\n=== {category_info['name']} Configuration Setup ===")
    CONSOLE.print(f"Description: {category_info['description']}\n")
    CONSOLE.print("[dim]Press Enter to skip a setting, or Ctrl+C to cancel setup[/]\n")

    config = load_config()
    updated_count = 0

    for config_key in category_info["keys"]:
        current_value = config.get(config_key, "")

        # Show current value (masked if sensitive)
        current_display = ""
        if current_value:
            displayed_value = (
                mask_sensitive_value(current_value)
                if is_sensitive_key(config_key)
                else current_value
            )
            current_display = f" (current: {displayed_value})"

        prompt = f"{config_key}{current_display}: "

        try:
            user_input = input(prompt).strip()

            if user_input:
                set_config_value(config_key, user_input)
                updated_count += 1
                CONSOLE.print(f"[green]✓ Configured[/] {config_key}")
            else:
                CONSOLE.print(f"[yellow]⚠ Skipped[/] {config_key}")

        except KeyboardInterrupt:
            CONSOLE.print("\n[yellow]Configuration setup cancelled.[/]")
            return

    CONSOLE.print(
        f"\n[green]Successfully updated {updated_count} integration setting(s)[/]"
    )


def _setup_all_integration_categories() -> None:
    """Interactively configure all available integration categories."""
    CONSOLE.print("[cyan]Setting up all integration categories...\n[/]")

    total_categories = len(CREDENTIAL_CATEGORIES)
    current_category = 0

    for category_id in CREDENTIAL_CATEGORIES.keys():
        current_category += 1
        category_name = CREDENTIAL_CATEGORIES[category_id]["name"]

        CONSOLE.print(f"\n[dim]({current_category}/{total_categories})[/]")
        proceed = input(f"Configure {category_name}? (y/N): ").strip().lower()

        if proceed in ["y", "yes"]:
            _setup_integration_category(category_id)
        else:
            CONSOLE.print(f"[yellow]⚠ Skipped {category_name}[/]")

    CONSOLE.print("\n[green]🎉 All integration categories setup completed![/]")


@click.group(name="config")
def config_cmd():
    """Manage configuration and credentials for test harness.

    Supports setting individual credentials, category-based interactive setup,
    validation, and more.

    Categories:
      - version-control: GitLab, GitHub
      - project-management: JIRA, Confluence
      - cloud-providers: AWS, Azure, GCP
      - development-tools: Azure DevOps, ServiceNow, Keycloak, SonarQube
      - notifications: Email, OAuth, Telegram
      - research-tools: Kubernetes, Report Portal, Elasticsearch
      - data-management: LiteLLM, SQL databases
    """
    pass


@config_cmd.command(name="list")
@click.option(
    "--show-values",
    is_flag=True,
    help="Show real values instead of masked values (use with caution)",
)
def config_list(show_values: bool = False):
    """List all configuration values.

    Examples:
      codemie-test-harness config list
      codemie-test-harness config list --show-values
    """
    cfg = load_config()
    if not cfg:
        CONSOLE.print("[yellow]No config set yet[/]")
    else:
        title_suffix = " (Real Values)" if show_values else " (Masked Values)"
        CONSOLE.print(f"[bold cyan]Configuration{title_suffix}[/bold cyan]")
        for k, v in cfg.items():
            display_value = (
                mask_sensitive_value(str(v), show_real=show_values)
                if is_sensitive_key(k)
                else str(v)
            )
            CONSOLE.print(f"[cyan]{k}[/] = [green]{display_value}[/]")


@config_cmd.command(name="set")
@click.argument("key", required=False)
@click.argument("value", required=False)
def config_set(key: str = None, value: str = None):
    """Set configuration values using key-value pairs.

    Supports all 86+ environment variables across 10 categories.

    Examples:
      codemie-test-harness config set GITLAB_TOKEN glpat-xxx
      codemie-test-harness config set SONAR_URL https://sonar.example.com
      codemie-test-harness config set KUBERNETES_TOKEN k8s-token-123
    """
    # If key-value pair provided
    if key and value:
        set_config_value(key, value)
        display_value = mask_sensitive_value(value) if is_sensitive_key(key) else value
        CONSOLE.print(f"[green]Saved[/] {key} = {display_value}")
    else:
        CONSOLE.print(
            "[yellow]Please provide key and value: codemie-test-harness config set KEY VALUE[/yellow]"
        )
        CONSOLE.print("\n[cyan]Examples:[/cyan]")
        CONSOLE.print("  codemie-test-harness config set GITLAB_TOKEN glpat-xxx")
        CONSOLE.print(
            "  codemie-test-harness config set SONAR_URL https://sonar.example.com"
        )
        CONSOLE.print(
            "  codemie-test-harness config set AWS_ACCESS_KEY_ID AKIA1234567890"
        )
        CONSOLE.print(
            "\n[dim]💡 Use 'codemie-test-harness config vars' to see all available variables[/dim]"
        )


@config_cmd.command(name="get")
@click.argument("key")
@click.option(
    "--show-value",
    is_flag=True,
    help="Show real value instead of masked value (use with caution)",
)
def config_get(key: str, show_value: bool = False):
    """Get a configuration value.

    Examples:
      codemie-test-harness config get GITLAB_TOKEN
      codemie-test-harness config get GITLAB_TOKEN --show-value
    """
    val = get_config_value(key)
    if val is None:
        CONSOLE.print(f"[yellow]{key} not set[/]")
    else:
        display_value = (
            mask_sensitive_value(val, show_real=show_value)
            if is_sensitive_key(key)
            else val
        )
        CONSOLE.print(f"{key} = {display_value}")


@config_cmd.command(name="integrations")
@click.option(
    "--category",
    type=click.Choice(list(CREDENTIAL_CATEGORIES.keys())),
    help="Show credentials for specific category",
)
@click.option(
    "--show-values",
    is_flag=True,
    help="Show real values instead of masked values (use with caution)",
)
def config_integrations(category: str = None, show_values: bool = False):
    """Show current credentials.

    Examples:
      codemie-test-harness config integrations
      codemie-test-harness config integrations --category version-control
      codemie-test-harness config integrations --show-values
      codemie-test-harness config integrations --category cloud --show-values
    """
    _show_integration_configs(category=category, show_real=show_values)


@config_cmd.command(name="unset")
@click.option("--keys", help="Comma-separated list of keys to unset (case-insensitive)")
@click.option(
    "--category",
    type=click.Choice(list(CREDENTIAL_CATEGORIES.keys())),
    help="Category to unset all keys from",
)
def config_unset(keys: str = None, category: str = None):
    """Unset (remove) configuration keys.

    Supports case-insensitive key removal and category-based removal.

    Examples:
      codemie-test-harness config unset --keys GITLAB_TOKEN,gitlab_url
      codemie-test-harness config unset --keys some_setting,DEBUG_LEVEL
      codemie-test-harness config unset --category version-control
    """
    if not keys and not category:
        CONSOLE.print("[yellow]Please specify --keys or --category[/yellow]")
        return

    config = load_config()
    if not config:
        CONSOLE.print("[yellow]No configuration found[/yellow]")
        return

    removed_count = 0

    # Handle category removal
    if category:
        category_info = CREDENTIAL_CATEGORIES[category]
        category_keys = category_info["keys"]

        for key in category_keys:
            if unset_config_key(key):
                removed_count += 1

        CONSOLE.print(
            f"[green]category:{category_info['name']}: Removed {removed_count} keys[/green]"
        )

    # Handle specific key removal (case-insensitive)
    if keys:
        key_list = [k.strip() for k in keys.split(",")]
        config = load_config()  # Reload config in case category removal happened
        config_keys_lower = {k.lower(): k for k in config.keys()}

        for key in key_list:
            key_lower = key.lower()
            if key_lower in config_keys_lower:
                actual_key = config_keys_lower[key_lower]
                if unset_config_key(actual_key):
                    removed_count += 1
                    CONSOLE.print(f"[green]{key}: Removed (was: {actual_key})[/green]")
            else:
                CONSOLE.print(f"[yellow]{key}: Not found[/yellow]")

    if removed_count > 0:
        CONSOLE.print(f"[green]Total keys removed: {removed_count}[/green]")
    else:
        CONSOLE.print("[yellow]No keys were removed[/yellow]")


@config_cmd.command(name="setup")
@click.option(
    "--category",
    type=click.Choice(list(CREDENTIAL_CATEGORIES.keys())),
    help="Setup specific category interactively",
)
@click.option(
    "--all", "setup_all", is_flag=True, help="Setup all categories interactively"
)
def config_setup(category: str = None, setup_all: bool = False):
    """Interactive credential setup.

    Examples:
      codemie-test-harness config setup --category version-control
      codemie-test-harness config setup --category cloud-providers
      codemie-test-harness config setup --all
    """
    if setup_all:
        _setup_all_integration_categories()
    elif category:
        _setup_integration_category(category)
    else:
        CONSOLE.print("[yellow]Please specify --category or --all[/yellow]")
        CONSOLE.print("\nAvailable categories:")
        _list_integration_categories()


@config_cmd.command(name="validate")
@click.option(
    "--category",
    type=click.Choice(list(CREDENTIAL_CATEGORIES.keys())),
    help="Validate specific category",
)
def config_validate(category: str = None):
    """Validate configured credentials.

    Examples:
      codemie-test-harness config validate
      codemie-test-harness config validate --category cloud-providers
    """

    validation_results = _validate_integrations()

    # Display validation results
    if not validation_results:
        CONSOLE.print("[yellow]No credentials configured[/yellow]")
        return

    # Filter by category if specified
    if category:
        if category in CREDENTIAL_CATEGORIES:
            category_name = CREDENTIAL_CATEGORIES[category]["name"]
            if category_name in validation_results:
                validation_results = {category_name: validation_results[category_name]}
            else:
                validation_results = {}
        else:
            CONSOLE.print(f"[red]Unknown category: {category}[/red]")
            return

    # Create table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Category", style="cyan", no_wrap=True, width=25)
    table.add_column("Credential", style="white", width=35)
    table.add_column("Status", justify="center", width=15)

    total_configured = 0
    total_missing = 0

    # Sort categories for consistent display
    sorted_categories = sorted(validation_results.items())

    for i, (category_name, results) in enumerate(sorted_categories):
        configured = results["configured"]
        missing = results["missing"]

        total_configured += len(configured)
        total_missing += len(missing)

        # Add configured credentials
        for j, key in enumerate(sorted(configured)):
            cat_display = category_name if j == 0 else ""
            table.add_row(cat_display, key, "[green]✓ Configured[/green]")

        # Add missing credentials
        for j, key in enumerate(sorted(missing)):
            cat_display = category_name if j == 0 and not configured else ""
            table.add_row(cat_display, key, "[yellow]⚠ Missing[/yellow]")

        # Add separator row between categories (except for last category)
        if i < len(sorted_categories) - 1 and (configured or missing):
            table.add_row("", "", "", style="dim")

    # Display table
    CONSOLE.print("\n[bold blue]Credential Validation Results[/bold blue]")
    CONSOLE.print(table)

    # Summary
    CONSOLE.print("\n[bold]Summary:[/bold]")
    CONSOLE.print(f"  [green]Configured: {total_configured}[/green]")
    CONSOLE.print(f"  [yellow]Missing: {total_missing}[/yellow]")

    if total_missing == 0 and total_configured > 0:
        CONSOLE.print("\n[green]✅ All credentials are configured![/green]")
    elif total_configured == 0:
        CONSOLE.print(
            "\n[yellow]⚠️ No credentials are configured. Use 'codemie-test-harness config setup' to get started.[/yellow]"
        )
    else:
        CONSOLE.print(
            "\n[yellow]⚠️ Some credentials are still missing. Use 'codemie-test-harness config setup' to configure them.[/yellow]"
        )


@config_cmd.command(name="categories")
@click.option(
    "--list-vars",
    "-l",
    is_flag=True,
    help="Show environment variables for each category",
)
@click.option("--category", "-c", help="Show variables for specific category only")
def config_categories(list_vars: bool = False, category: str = None):
    """List available credential categories and optionally their environment variables."""
    from ..constants import CREDENTIAL_CATEGORIES
    from rich.console import Console
    from rich.table import Table

    console = Console()

    if category:
        # Show variables for specific category
        if category not in CREDENTIAL_CATEGORIES:
            click.echo(
                f"❌ Category '{category}' not found. Available categories: {', '.join(CREDENTIAL_CATEGORIES.keys())}"
            )
            return

        cat_info = CREDENTIAL_CATEGORIES[category]
        click.echo(f"\n=== {cat_info['name']} ===")
        click.echo(f"{cat_info['description']}\n")

        if list_vars or True:  # Always show vars when specific category requested
            click.echo("Environment Variables:")
            for var in sorted(cat_info["keys"]):
                click.echo(f"  • {var}")
        return

    if list_vars:
        # Show all categories with their variables
        for cat_id, cat_info in CREDENTIAL_CATEGORIES.items():
            click.echo(f"\n=== {cat_info['name']} ({cat_id}) ===")
            click.echo(f"{cat_info['description']}")
            click.echo(f"Environment Variables ({len(cat_info['keys'])} total):")
            for var in sorted(cat_info["keys"]):
                click.echo(f"  • {var}")
            click.echo()
    else:
        # Show summary table (existing functionality)
        table = Table(title="Available Credential Categories")
        table.add_column("Category", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Description", style="yellow")
        table.add_column("Keys", justify="right", style="magenta")

        for cat_id, cat_info in CREDENTIAL_CATEGORIES.items():
            table.add_row(
                cat_id,
                cat_info["name"],
                cat_info["description"],
                str(len(cat_info["keys"])),
            )

        console.print(table)
        click.echo(
            "\n💡 Use 'codemie-test-harness config vars <category>' to see environment variables for a specific category."
        )


@config_cmd.command(name="vars")
@click.argument("category", required=False)
def config_vars(category: str = None):
    """List environment variables for a specific category or all categories."""
    from ..constants import CREDENTIAL_CATEGORIES

    if category:
        # Show variables for specific category
        if category not in CREDENTIAL_CATEGORIES:
            click.echo(f"❌ Category '{category}' not found.")
            click.echo(
                f"Available categories: {', '.join(CREDENTIAL_CATEGORIES.keys())}"
            )
            return

        cat_info = CREDENTIAL_CATEGORIES[category]
        click.echo(f"\n=== {cat_info['name']} ===")
        click.echo(f"{cat_info['description']}")
        click.echo(f"\nEnvironment Variables ({len(cat_info['keys'])} total):")
        for var in sorted(cat_info["keys"]):
            click.echo(f"  {var}")
    else:
        # Show all categories with their variables
        click.echo("Environment Variables by Category:\n")
        for cat_id, cat_info in CREDENTIAL_CATEGORIES.items():
            click.echo(f"=== {cat_info['name']} ({cat_id}) ===")
            click.echo(f"Variables ({len(cat_info['keys'])} total):")
            for var in sorted(cat_info["keys"]):
                click.echo(f"  {var}")
            click.echo()


@config_cmd.command(name="clear")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
def config_clear(force: bool = False):
    """Clear ALL configuration including credentials and settings.

    This will remove EVERYTHING from the configuration file. Use with caution!

    Examples:
      codemie-test-harness config clear
      codemie-test-harness config clear --force
    """
    from ..utils import load_config
    from ..constants import CONSOLE

    # Load current config to check if there's anything to clear
    current_config = load_config()
    if not current_config:
        CONSOLE.print("[yellow]No configuration found to clear.[/yellow]")
        return

    # Count all items that will be removed
    total_count = len(current_config)

    if not force:
        CONSOLE.print(
            f"[yellow]⚠️ WARNING: This will remove ALL {total_count} configuration items![/yellow]"
        )
        CONSOLE.print("[yellow]This action cannot be undone.[/yellow]")

        # Show what will be cleared
        CONSOLE.print("\n[cyan]Items that will be cleared:[/cyan]")
        for key in sorted(current_config.keys()):
            CONSOLE.print(f"  • {key}")

        confirm = click.confirm("\nAre you sure you want to clear ALL configuration?")
        if not confirm:
            CONSOLE.print("[green]Operation cancelled.[/green]")
            return

    # Clear everything
    save_config({})

    CONSOLE.print(
        f"[green]✅ Successfully cleared ALL {total_count} configuration items.[/green]"
    )
    CONSOLE.print("[cyan]Configuration file is now empty.[/cyan]")
