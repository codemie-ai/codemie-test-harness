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

"""Main CLI entry point for CodeMie Test Harness.

Thin entry point: registers commands and wires common options.
"""

from __future__ import annotations

import os
from typing import Optional

import click

from .constants import (
    CONTEXT_SETTINGS,
    KEY_AUTH_SERVER_URL,
    KEY_AUTH_CLIENT_ID,
    KEY_AUTH_CLIENT_SECRET,
    KEY_AUTH_REALM_NAME,
    KEY_CODEMIE_API_DOMAIN,
    KEY_AUTH_USERNAME,
    KEY_AUTH_PASSWORD,
    KEY_AWS_PROFILE,
    TEST_SUITES,
)
from .result_options import add_result_options
from .utils import ensure_env_from_config
from codemie_test_harness.tests.utils.aws_parameters_store import (
    AwsParameterStore,
    AwsStoreConfig,
    SecretStoreError,
)
from .commands.config_cmd import config_cmd
from .commands.run_cmd import run_cmd
from .commands.assistant_cmd import assistant_cmd
from .commands.workflow_cmd import workflow_cmd
from .commands.marks_cmd import marks_cmd
from .commands.browsers_cmd import browsers_cmd


def _add_suite_flags(func):
    """Add --<suite-name> shortcut flags for every entry in TEST_SUITES."""
    for name in reversed(list(TEST_SUITES.keys())):
        param_name = name.replace("-", "_")
        func = click.option(
            f"--{name}",
            param_name,
            is_flag=True,
            default=False,
            help=f"Shortcut: run the '{name}' test suite",
        )(func)
    return func


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.option("--auth-server-url", envvar=KEY_AUTH_SERVER_URL, help="Auth server url")
@click.option("--auth-client-id", envvar=KEY_AUTH_CLIENT_ID, help="Auth client id")
@click.option(
    "--auth-client-secret", envvar=KEY_AUTH_CLIENT_SECRET, help="Auth client secret"
)
@click.option("--auth-realm-name", envvar=KEY_AUTH_REALM_NAME, help="Auth realm name")
@click.option("--auth-username", envvar=KEY_AUTH_USERNAME, help="Auth username")
@click.option("--auth-password", envvar=KEY_AUTH_PASSWORD, help="Auth password")
@click.option(
    "--api-domain", envvar=KEY_CODEMIE_API_DOMAIN, help="CodeMie API domain URL"
)
@click.option(
    "--aws-profile",
    envvar=KEY_AWS_PROFILE,
    help="AWS profile for the opt-in Parameter Store (used only when HARNESS_SECRET_STORE=aws-parameter-store)",
)
# Integration credentials are set via 'codemie-test-harness config set' command
@add_result_options
@_add_suite_flags
@click.pass_context
def cli(
    ctx: click.Context,
    auth_server_url: Optional[str],
    auth_client_id: Optional[str],
    auth_client_secret: Optional[str],
    auth_realm_name: Optional[str],
    auth_username: Optional[str],
    auth_password: Optional[str],
    api_domain: Optional[str],
    aws_profile: Optional[str],
    results_dir: Optional[str],
    no_junit_xml: bool,
    no_json: bool,
    **suite_flags,
):
    """CodeMie Test Harness CLI.

    \b
    Run without arguments to enter interactive mode:
      codemie-test-harness

    \b
    Or use suite shortcuts directly:
      codemie-test-harness --sanity
      codemie-test-harness --smoke
      codemie-test-harness --api

    \b
    Or use the run subcommand:
      codemie-test-harness run smoke
      codemie-test-harness config list
      codemie-test-harness marks

    Available commands: config, run, assistant, workflow, marks

    Integration credentials should be set using:
      codemie-test-harness config set KEY VALUE

    Use 'codemie-test-harness config vars' to see all available credentials.

    The AWS Parameter Store is opt-in (HARNESS_SECRET_STORE=aws-parameter-store);
    its credentials can be an AWS profile:
      --aws-profile PROFILE_NAME
    """
    ctx.ensure_object(dict)
    # Group-level result options are defaults for the `run` subcommand
    ctx.obj["results"] = {
        "results_dir": results_dir,
        "no_junit_xml": no_junit_xml,
        "no_json": no_json,
    }

    # Ensure env vars. CLI args override env/config.
    provided = {
        # auth/api
        KEY_AUTH_SERVER_URL: auth_server_url,
        KEY_AUTH_CLIENT_ID: auth_client_id,
        KEY_AUTH_CLIENT_SECRET: auth_client_secret,
        KEY_AUTH_USERNAME: auth_username,
        KEY_AUTH_PASSWORD: auth_password,
        KEY_AUTH_REALM_NAME: auth_realm_name,
        KEY_CODEMIE_API_DOMAIN: api_domain,
        # aws
        KEY_AWS_PROFILE: aws_profile,
    }
    for k, v in provided.items():
        if v is not None and v != "":
            os.environ[k] = str(v)
    # populate any missing values from saved config
    ensure_env_from_config()

    # Fail fast before a run when the opt-in secret store is enabled but unusable.
    if ctx.invoked_subcommand in (None, "run"):
        try:
            config = AwsStoreConfig.from_env()
            if config is not None:
                AwsParameterStore.get_instance(config).check()
        except SecretStoreError as e:
            raise click.ClickException(str(e))

    if ctx.invoked_subcommand is None:
        # Check for --<suite> shortcut flags
        active_suite = next(
            (name for name in TEST_SUITES if suite_flags.get(name.replace("-", "_"))),
            None,
        )
        if active_suite:
            ctx.invoke(
                run_cmd,
                suite=active_suite,
                results_dir=results_dir,
                no_junit_xml=no_junit_xml,
                no_json=no_json,
            )
            return

        from .interactive import run_interactive_mode

        if results_dir or no_junit_xml or no_json:
            click.echo(
                "Warning: --results-dir/--no-junit-xml/--no-json are ignored in "
                "interactive mode; use a suite flag or the run command.",
                err=True,
            )

        run_interactive_mode()


# Register subcommands
cli.add_command(config_cmd)
cli.add_command(run_cmd)
cli.add_command(assistant_cmd)
cli.add_command(workflow_cmd)
cli.add_command(marks_cmd)
cli.add_command(browsers_cmd)


if __name__ == "__main__":  # pragma: no cover
    cli()
