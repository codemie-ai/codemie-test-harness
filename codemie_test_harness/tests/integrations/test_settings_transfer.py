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

"""API tests for POST /v1/settings/transfer (move/copy integrations between projects).

Covers scenarios TC-01..TC-13 (including the ``type_of_integration`` / ``list`` filters).
"""

import json

import pytest
from hamcrest import (
    all_of,
    assert_that,
    contains_exactly,
    contains_inanyorder,
    contains_string,
    empty,
    equal_to,
    has_items,
    has_length,
    is_,
    is_not,
    none,
    not_none,
)

from codemie_sdk.models.integration import (
    CredentialTypes,
    CredentialValues,
    IntegrationTestRequest,
    IntegrationTestResponse,
    IntegrationType,
)
from codemie_test_harness.tests import CredentialsManager
from codemie_test_harness.tests.test_data.settings_transfer_test_data import (
    invalid_transfer_payload_test_data,
    missing_project_side_test_data,
    transfer_invalid_filter_test_data,
    transfer_list_selection_test_data,
    transfer_mode_test_data,
    transfer_role_test_data,
    transfer_type_filter_test_data,
)
from codemie_test_harness.tests.utils.base_utils import (
    assert_error_details,
    assert_response,
    get_random_name,
)
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver
from codemie_test_harness.tests.utils.integration_utils import IntegrationUtils

ADMIN_OR_MAINTAINER_REQUIRED = (
    "This action requires administrator or maintainer privileges."
)


def _testable_gitlab_credentials():
    """GitLab credentials that the ``/v1/settings/test/`` endpoint can actually verify.

    ``CredentialsManager.gitlab_credentials()`` points ``url`` at the bare
    GitLab host (used for tool-config-style GIT integrations elsewhere in the
    suite), which the test-connection endpoint rejects with 400 ("Testing the
    connection requires the full repository URL") -- confirmed against the
    live environment. Pointing ``url`` at a real repository's clone URL
    (``GITLAB_PROJECT`` + ``.git``, the same repo already relied on by the
    datasource tests, e.g. datasource_utils.py) is what the endpoint expects.
    """
    return [
        CredentialValues(
            key="url",
            value=f"{CredentialsManager.get_parameter('GITLAB_PROJECT')}.git",
        ),
        CredentialValues(key="name", value=""),
        CredentialValues(
            key="token", value=CredentialsManager.get_parameter("GITLAB_TOKEN")
        ),
    ]


def _find_by_project_and_alias(integration_utils, setting_type, project_name, alias):
    """Return the single integration matching both project_name and alias.

    ``integration_utils.get_integration_by_alias``/the SDK's ``get`` look up rows
    by alias (or id) *without* scoping by project, which is ambiguous once a
    COPY-mode transfer creates a second row that shares the source row's alias
    in the target project. Scoping by project_name here keeps every lookup
    unambiguous.
    """
    matches = [
        row
        for row in integration_utils.list_integrations(setting_type, per_page=200)
        if row.project_name == project_name and row.alias == alias
    ]
    return matches[0] if matches else None


def _seed_integrations(integration_utils, project_name, project_count, user_count):
    """Create PROJECT (GIT) and USER (JIRA) integrations in ``project_name``, keyed by scope."""
    return {
        IntegrationType.PROJECT: [
            integration_utils.create_integration(
                credential_type=CredentialTypes.GIT,
                credential_values=CredentialsManager.gitlab_credentials(),
                setting_type=IntegrationType.PROJECT,
                project_name=project_name,
            )
            for _ in range(project_count)
        ],
        IntegrationType.USER: [
            integration_utils.create_integration(
                credential_type=CredentialTypes.JIRA,
                credential_values=CredentialsManager.jira_credentials(),
                setting_type=IntegrationType.USER,
                project_name=project_name,
            )
            for _ in range(user_count)
        ],
    }


def _create_webhook_integration(integration_utils, project_name, resource_id):
    return integration_utils.create_integration(
        credential_type=CredentialTypes.WEBHOOK,
        credential_values=[
            CredentialValues(key="url", value=CredentialsManager.AUTO_GENERATED),
            CredentialValues(key="webhook_id", value=get_random_name()),
            CredentialValues(key="is_enabled", value=True),
            CredentialValues(key="resource_type", value="assistant"),
            CredentialValues(key="resource_id", value=resource_id),
        ],
        setting_type=IntegrationType.PROJECT,
        project_name=project_name,
    )


def _seeded_ids_in_project(integration_utils, seeded, project_name):
    seeded_aliases = {row.alias for rows in seeded.values() for row in rows}
    return [
        found.id
        for setting_type in seeded
        for found in integration_utils.list_integrations(setting_type, per_page=200)
        if found.project_name == project_name and found.alias in seeded_aliases
    ]


def _aliases_in_project(integration_utils, project_name):
    return [
        row.alias
        for row in integration_utils.list_integrations(
            IntegrationType.PROJECT, per_page=200
        )
        if row.project_name == project_name
    ]


def _assert_moved_only(integration_utils, seeded, moved_ids, source, target):
    """Assert rows in ``moved_ids`` are now in ``target`` (same id) and every other seeded row stayed in ``source``."""
    all_rows = [row for rows in seeded.values() for row in rows]
    assert_that(
        _seeded_ids_in_project(integration_utils, seeded, target.name),
        contains_inanyorder(*[row.id for row in all_rows if row.id in moved_ids]),
        "Target project does not hold exactly the selected integrations with their original ids.",
    )
    assert_that(
        _seeded_ids_in_project(integration_utils, seeded, source.name),
        contains_inanyorder(*[row.id for row in all_rows if row.id not in moved_ids]),
        "Source project does not hold exactly the unselected integrations.",
    )


def _assert_error_names_aliases(response, aliases):
    error_details = json.loads(response.content)["error"]["details"]
    assert_that(
        error_details,
        all_of(*[contains_string(alias) for alias in aliases or []]),
        "Error details do not name every listed alias.",
    )


def _assert_test_connection_succeeds(integration_utils, integration, context):
    """Assert that ``integration`` (identified by its post-transfer row) still tests successfully.

    Mirrors the ``IntegrationTestRequest(credential_type=..., setting_id=...)`` /
    ``IntegrationTestResponse(message="", success=True)`` pattern used for
    already-created integrations elsewhere (see
    ``test_integration_after_creation`` in test_user_integrations.py /
    test_project_integrations.py). Transfer only relocates or duplicates the
    row; the credentials themselves are untouched, so a successful transfer
    must still be able to authenticate.
    """
    test_response = integration_utils.test_integration(
        IntegrationTestRequest(
            credential_type=integration.credential_type,
            setting_id=integration.id,
        ),
        IntegrationTestResponse,
    )
    assert_that(
        test_response,
        equal_to(IntegrationTestResponse(message="", success=True)),
        f"{context} failed its test-connection check.",
    )


@pytest.mark.integration
@pytest.mark.settings_transfer
@pytest.mark.smoke
@pytest.mark.api
def test_transfer_move_relocates_project_and_user_scoped_integrations(
    project, integration_utils
):
    """TC-01: move relocates both PROJECT- and USER-scoped integrations, removing them from source."""
    source = project()
    target = project()

    project_integration = integration_utils.create_integration(
        credential_type=CredentialTypes.GIT,
        credential_values=_testable_gitlab_credentials(),
        setting_type=IntegrationType.PROJECT,
        project_name=source.name,
    )
    user_integration = integration_utils.create_integration(
        credential_type=CredentialTypes.JIRA,
        credential_values=CredentialsManager.jira_credentials(),
        setting_type=IntegrationType.USER,
        project_name=source.name,
    )

    response = integration_utils.transfer_settings(source.name, target.name, "move")

    assert_that(response.mode.value, equal_to("move"))
    assert_that(response.transferred_count, equal_to(2))
    transferred_ids = {item.id for item in response.transferred}
    assert_that(
        transferred_ids, equal_to({project_integration.id, user_integration.id})
    )

    moved_project = _find_by_project_and_alias(
        integration_utils,
        IntegrationType.PROJECT,
        target.name,
        project_integration.alias,
    )
    moved_user = _find_by_project_and_alias(
        integration_utils, IntegrationType.USER, target.name, user_integration.alias
    )
    assert_that(
        moved_project,
        not_none(),
        "PROJECT-scoped integration did not appear in target project.",
    )
    assert_that(
        moved_user,
        not_none(),
        "USER-scoped integration did not appear in target project.",
    )
    assert_that(moved_project.id, equal_to(project_integration.id))
    assert_that(moved_user.id, equal_to(user_integration.id))

    # Structural placement is not enough: the moved rows must still authenticate
    # from their new project.
    _assert_test_connection_succeeds(
        integration_utils,
        moved_project,
        f"Moved PROJECT-scoped integration '{moved_project.alias}' in target project '{target.name}'",
    )
    _assert_test_connection_succeeds(
        integration_utils,
        moved_user,
        f"Moved USER-scoped integration '{moved_user.alias}' in target project '{target.name}'",
    )

    assert_that(
        _find_by_project_and_alias(
            integration_utils,
            IntegrationType.PROJECT,
            source.name,
            project_integration.alias,
        ),
        none(),
        "PROJECT-scoped integration is still present in the source project after move.",
    )
    assert_that(
        _find_by_project_and_alias(
            integration_utils, IntegrationType.USER, source.name, user_integration.alias
        ),
        none(),
        "USER-scoped integration is still present in the source project after move.",
    )


@pytest.mark.integration
@pytest.mark.settings_transfer
@pytest.mark.smoke
@pytest.mark.api
def test_transfer_copy_duplicates_integrations_and_preserves_source(
    project, integration_utils
):
    """TC-02: copy duplicates integrations into target, leaves source untouched, keeps masking."""
    source = project()
    target = project()

    project_integration = integration_utils.create_integration(
        credential_type=CredentialTypes.GIT,
        credential_values=_testable_gitlab_credentials(),
        setting_type=IntegrationType.PROJECT,
        project_name=source.name,
    )
    user_integration = integration_utils.create_integration(
        credential_type=CredentialTypes.JIRA,
        credential_values=CredentialsManager.jira_credentials(),
        setting_type=IntegrationType.USER,
        project_name=source.name,
    )

    response = integration_utils.transfer_settings(source.name, target.name, "copy")

    assert_that(response.mode.value, equal_to("copy"))
    assert_that(response.transferred_count, equal_to(2))

    for original, setting_type in (
        (project_integration, IntegrationType.PROJECT),
        (user_integration, IntegrationType.USER),
    ):
        alias = original.alias
        transferred_item = next(
            item for item in response.transferred if item.alias == alias
        )
        assert_that(
            transferred_item.id,
            is_not(equal_to(original.id)),
            f"Copy of '{alias}' reused the source row id instead of minting a new one.",
        )

        copied = _find_by_project_and_alias(
            integration_utils, setting_type, target.name, alias
        )
        assert_that(
            copied, not_none(), f"Copy of '{alias}' did not appear in target project."
        )
        assert_that(copied.id, equal_to(transferred_item.id))

        remaining_source = _find_by_project_and_alias(
            integration_utils, setting_type, source.name, alias
        )
        assert_that(
            remaining_source,
            not_none(),
            f"Source copy of '{alias}' disappeared after a copy-mode transfer.",
        )
        assert_that(remaining_source.id, equal_to(original.id))

        # Copied credential fields keep the same masking convention as the source.
        source_values = {cv.key: cv.value for cv in remaining_source.credential_values}
        copied_values = {cv.key: cv.value for cv in copied.credential_values}
        for key, source_value in source_values.items():
            copied_value = copied_values.get(key)
            if isinstance(source_value, str) and source_value.startswith("*"):
                assert_that(
                    isinstance(copied_value, str) and copied_value.startswith("*"),
                    is_(True),
                    f"Field '{key}' lost its masking convention after copy.",
                )
            else:
                assert_that(copied_value, equal_to(source_value))

        # Structural masking is not enough: the copy must still authenticate from
        # the target project, and copying must not disturb the source's own
        # ability to authenticate either.
        _assert_test_connection_succeeds(
            integration_utils,
            copied,
            f"Copy of '{alias}' in target project '{target.name}'",
        )
        _assert_test_connection_succeeds(
            integration_utils,
            remaining_source,
            f"Source integration '{alias}' in source project '{source.name}'",
        )


@pytest.mark.integration
@pytest.mark.settings_transfer
@pytest.mark.api
@pytest.mark.parametrize("mode", transfer_mode_test_data)
def test_transfer_empty_source_project_returns_zero_counts(
    project, integration_utils, mode
):
    """TC-03: an empty source project returns 200 with zero counts, for both modes."""
    source = project()
    target = project()

    response = integration_utils.transfer_settings(source.name, target.name, mode)

    assert_that(response.transferred_count, equal_to(0))
    assert_that(response.transferred, equal_to([]))
    assert_that(response.skipped_count, equal_to(0))
    assert_that(
        response.message,
        equal_to(f"No transferable integrations found in project '{source.name}'."),
    )


@pytest.mark.integration
@pytest.mark.settings_transfer
@pytest.mark.api
@pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Scheduler is disabled on sandbox environments",
)
def test_transfer_copy_skips_webhook_and_scheduler_integrations(
    project, integration_utils, assistant
):
    """TC-04: copy mode skips WEBHOOK/SCHEDULER, reporting them in `skipped` instead of duplicating them."""
    source = project()
    target = project()
    resource_assistant = assistant(project_name=source.name)

    ordinary_integration = integration_utils.create_integration(
        credential_type=CredentialTypes.GIT,
        credential_values=CredentialsManager.gitlab_credentials(),
        setting_type=IntegrationType.PROJECT,
        project_name=source.name,
    )
    webhook_integration_row = integration_utils.create_integration(
        credential_type=CredentialTypes.WEBHOOK,
        credential_values=[
            CredentialValues(key="url", value=CredentialsManager.AUTO_GENERATED),
            CredentialValues(key="webhook_id", value=get_random_name()),
            CredentialValues(key="is_enabled", value=True),
            CredentialValues(key="resource_type", value="assistant"),
            CredentialValues(key="resource_id", value=resource_assistant.id),
        ],
        setting_type=IntegrationType.PROJECT,
        project_name=source.name,
    )
    scheduler_alias = get_random_name()
    scheduler_integration_row = integration_utils.create_integration(
        credential_type=CredentialTypes.SCHEDULER,
        credential_values=[
            CredentialValues(key="url", value=CredentialsManager.AUTO_GENERATED),
            CredentialValues(key="is_enabled", value=True),
            CredentialValues(key="schedule", value="0 * * * *"),
            CredentialValues(key="resource_type", value="assistant"),
            CredentialValues(key="resource_id", value=resource_assistant.id),
            CredentialValues(key="prompt", value=f"Scheduler prompt {scheduler_alias}"),
        ],
        setting_type=IntegrationType.PROJECT,
        project_name=source.name,
        integration_alias=scheduler_alias,
    )
    webhook_alias = webhook_integration_row.alias

    response = integration_utils.transfer_settings(source.name, target.name, "copy")

    assert_that(response.transferred_count, equal_to(1))
    assert_that(response.transferred[0].alias, equal_to(ordinary_integration.alias))
    assert_that(response.skipped_count, equal_to(2))
    skipped_aliases = {item.alias for item in response.skipped}
    assert_that(skipped_aliases, equal_to({webhook_alias, scheduler_alias}))
    skipped_types = {item.alias: item.credential_type for item in response.skipped}
    assert_that(skipped_types[webhook_alias], equal_to(CredentialTypes.WEBHOOK.value))
    assert_that(
        skipped_types[scheduler_alias], equal_to(CredentialTypes.SCHEDULER.value)
    )
    skipped_ids = {item.alias: item.id for item in response.skipped}
    assert_that(skipped_ids[webhook_alias], equal_to(webhook_integration_row.id))
    assert_that(skipped_ids[scheduler_alias], equal_to(scheduler_integration_row.id))

    assert_that(
        _find_by_project_and_alias(
            integration_utils,
            IntegrationType.PROJECT,
            target.name,
            ordinary_integration.alias,
        ),
        not_none(),
    )
    assert_that(
        _find_by_project_and_alias(
            integration_utils, IntegrationType.PROJECT, target.name, webhook_alias
        ),
        none(),
        "Webhook integration was copied into the target project despite being copy-blocked.",
    )
    assert_that(
        _find_by_project_and_alias(
            integration_utils, IntegrationType.PROJECT, target.name, scheduler_alias
        ),
        none(),
        "Scheduler integration was copied into the target project despite being copy-blocked.",
    )

    # Skip != delete: all three integrations remain in the source project, unchanged.
    for alias in (ordinary_integration.alias, webhook_alias, scheduler_alias):
        assert_that(
            _find_by_project_and_alias(
                integration_utils, IntegrationType.PROJECT, source.name, alias
            ),
            not_none(),
            f"Integration '{alias}' unexpectedly disappeared from the source project.",
        )


@pytest.mark.integration
@pytest.mark.settings_transfer
@pytest.mark.api
def test_transfer_move_preserves_integration_id(project, integration_utils):
    """TC-05: a moved integration keeps its id and remains resolvable in the target project."""
    source = project()
    target = project()

    original = integration_utils.create_integration(
        credential_type=CredentialTypes.GIT,
        credential_values=CredentialsManager.gitlab_credentials(),
        setting_type=IntegrationType.PROJECT,
        project_name=source.name,
    )

    response = integration_utils.transfer_settings(source.name, target.name, "move")

    assert_that(response.transferred, has_length(1))
    assert_that(response.transferred[0].id, equal_to(original.id))

    resolved = _find_by_project_and_alias(
        integration_utils, IntegrationType.PROJECT, target.name, original.alias
    )
    assert_that(resolved, not_none())
    assert_that(resolved.id, equal_to(original.id))
    assert_that(resolved.project_name, equal_to(target.name))


@pytest.mark.integration
@pytest.mark.settings_transfer
@pytest.mark.api
@pytest.mark.parametrize("mode", transfer_mode_test_data)
def test_transfer_blocked_by_alias_collision_in_target(
    project, integration_utils, mode
):
    """TC-06: an alias collision in the target project blocks the entire transfer atomically."""
    source = project()
    target = project()
    alias = get_random_name()

    source_integration = integration_utils.create_integration(
        credential_type=CredentialTypes.GIT,
        credential_values=CredentialsManager.gitlab_credentials(),
        setting_type=IntegrationType.PROJECT,
        project_name=source.name,
        integration_alias=alias,
    )
    target_integration = integration_utils.create_integration(
        credential_type=CredentialTypes.GIT,
        credential_values=CredentialsManager.gitlab_credentials(),
        setting_type=IntegrationType.PROJECT,
        project_name=target.name,
        integration_alias=alias,
    )

    with pytest.raises(Exception) as exec_info:
        integration_utils.transfer_settings(source.name, target.name, mode)

    assert_error_details(exec_info.value.response, 409, alias)

    # All-or-nothing: neither side changed.
    unchanged_source = _find_by_project_and_alias(
        integration_utils, IntegrationType.PROJECT, source.name, alias
    )
    unchanged_target = _find_by_project_and_alias(
        integration_utils, IntegrationType.PROJECT, target.name, alias
    )
    assert_that(unchanged_source, not_none())
    assert_that(unchanged_source.id, equal_to(source_integration.id))
    assert_that(unchanged_target, not_none())
    assert_that(unchanged_target.id, equal_to(target_integration.id))


@pytest.mark.integration
@pytest.mark.settings_transfer
@pytest.mark.api
@pytest.mark.parametrize(
    "source_override, target_override, mode_override, same_project, expected_message",
    invalid_transfer_payload_test_data,
)
def test_transfer_rejects_invalid_payload(
    project,
    integration_utils,
    source_override,
    target_override,
    mode_override,
    same_project,
    expected_message,
):
    """TC-07: missing/unsupported mode and malformed project-name fields are rejected with 422."""
    source = project()
    target = project()
    seeded = integration_utils.create_integration(
        credential_type=CredentialTypes.GIT,
        credential_values=CredentialsManager.gitlab_credentials(),
        setting_type=IntegrationType.PROJECT,
        project_name=source.name,
    )

    source_project_name = source.name if source_override is None else source_override
    if same_project:
        target_project_name = source_project_name
    else:
        target_project_name = (
            target.name if target_override is None else target_override
        )

    with pytest.raises(Exception) as exec_info:
        integration_utils.transfer_settings(
            source_project_name, target_project_name, mode_override
        )

    # `same_project` is rejected by the service layer with a plain-string `details` field
    # ("Source and target projects must be different."), which is what `assert_error_details()`
    # is built for. The other four rows never reach the service: FastAPI's own request-schema
    # validation rejects them first (missing/unsupported `mode`, blank name), and that failure
    # mode reports its message as a list of pydantic error objects under `details` instead of a
    # plain string -- confirmed against the live endpoint -- so `assert_response()` (the sibling
    # helper in base_utils.py that already handles both shapes, e.g. test_workflow_evaluate.py)
    # is used for those rows to still verify the exact message rather than only the status code.
    if same_project:
        assert_error_details(exec_info.value.response, 422, expected_message)
    else:
        assert_response(exec_info.value.response, 422, expected_message)

    # No integration moved: the seeded row is still where it started.
    assert_that(
        _find_by_project_and_alias(
            integration_utils, IntegrationType.PROJECT, source.name, seeded.alias
        ),
        not_none(),
    )


@pytest.mark.integration
@pytest.mark.settings_transfer
@pytest.mark.api
@pytest.mark.parametrize("missing_side", missing_project_side_test_data)
def test_transfer_rejects_nonexistent_project(project, integration_utils, missing_side):
    """TC-08: a nonexistent source/target project is rejected with 404, checked independently for each side."""
    existing = project()
    missing_project_name = get_random_name()

    if missing_side == "source":
        source_project_name, target_project_name = missing_project_name, existing.name
        expected_details = f"Source project '{missing_project_name}' does not exist."
    else:
        source_project_name, target_project_name = existing.name, missing_project_name
        expected_details = f"Target project '{missing_project_name}' does not exist."

    with pytest.raises(Exception) as exec_info:
        integration_utils.transfer_settings(
            source_project_name, target_project_name, "move"
        )

    assert_error_details(exec_info.value.response, 404, expected_details)


@pytest.mark.integration
@pytest.mark.settings_transfer
@pytest.mark.api
@pytest.mark.not_for_parallel_run
@pytest.mark.parametrize("role, expected_status", transfer_role_test_data)
def test_transfer_requires_admin_or_maintainer_role(
    request, project, integration_utils, role, expected_status
):
    """TC-09: only admin or maintainer callers may invoke the transfer; a plain member is denied."""
    source = project()
    target = project()
    seeded = integration_utils.create_integration(
        credential_type=CredentialTypes.GIT,
        credential_values=CredentialsManager.gitlab_credentials(),
        setting_type=IntegrationType.PROJECT,
        project_name=source.name,
    )

    if role == "plain_member":
        _, _, role_client = request.getfixturevalue("non_admin_user")
    else:
        role_client = request.getfixturevalue(f"{role}_client")

    role_integration_utils = IntegrationUtils(role_client)

    if expected_status == 403:
        with pytest.raises(Exception) as exec_info:
            role_integration_utils.transfer_settings(source.name, target.name, "move")
        assert_error_details(
            exec_info.value.response, 403, ADMIN_OR_MAINTAINER_REQUIRED
        )

        assert_that(
            _find_by_project_and_alias(
                integration_utils, IntegrationType.PROJECT, source.name, seeded.alias
            ),
            not_none(),
            "Integration moved despite the caller lacking admin/maintainer privileges.",
        )
    else:
        response = role_integration_utils.transfer_settings(
            source.name, target.name, "move"
        )
        assert_that(response.transferred_count, equal_to(1))
        assert_that(
            _find_by_project_and_alias(
                integration_utils, IntegrationType.PROJECT, target.name, seeded.alias
            ),
            not_none(),
        )


@pytest.mark.integration
@pytest.mark.settings_transfer
@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.parametrize(
    "type_of_integration, moved_scopes", transfer_type_filter_test_data
)
def test_transfer_type_of_integration_selects_scopes(
    project, integration_utils, type_of_integration, moved_scopes
):
    """TC-10: `type_of_integration` selects which scopes move; `list` omitted transfers all matching rows."""
    source = project()
    target = project()
    seeded = _seed_integrations(
        integration_utils, source.name, project_count=2, user_count=2
    )
    expected_ids = {row.id for scope in moved_scopes for row in seeded[scope]}

    response = integration_utils.transfer_settings(
        source.name, target.name, "move", type_of_integration=type_of_integration
    )

    assert_that(response.transferred_count, equal_to(len(expected_ids)))
    assert_that({item.id for item in response.transferred}, equal_to(expected_ids))
    assert_that(response.skipped_count, equal_to(0))
    _assert_moved_only(integration_utils, seeded, expected_ids, source, target)


@pytest.mark.integration
@pytest.mark.settings_transfer
@pytest.mark.api
@pytest.mark.parametrize(
    "type_of_integration, listed", transfer_list_selection_test_data
)
def test_transfer_list_limits_transfer_to_listed_aliases(
    project, integration_utils, type_of_integration, listed
):
    """TC-11: a provided `list` limits the transfer to the listed aliases only."""
    source = project()
    target = project()
    seeded = _seed_integrations(
        integration_utils, source.name, project_count=2, user_count=1
    )
    listed_rows = [seeded[scope][index] for scope, index in listed]

    response = integration_utils.transfer_settings(
        source.name,
        target.name,
        "move",
        type_of_integration=type_of_integration,
        integrations_list=[row.alias for row in listed_rows],
    )

    expected_ids = {row.id for row in listed_rows}
    assert_that(response.transferred_count, equal_to(len(listed_rows)))
    assert_that({item.id for item in response.transferred}, equal_to(expected_ids))
    assert_that(response.skipped_count, equal_to(0))
    _assert_moved_only(integration_utils, seeded, expected_ids, source, target)


@pytest.mark.integration
@pytest.mark.settings_transfer
@pytest.mark.api
@pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Webhook is disabled on sandbox environments",
)
def test_transfer_copy_with_filter_reports_webhook_as_skipped_when_list_omitted(
    project, integration_utils, assistant
):
    """TC-12: copy mode with a type filter and no `list` reports the webhook in `skipped` instead of failing."""
    source = project()
    target = project()
    resource_assistant = assistant(project_name=source.name)
    ordinary_integration = _seed_integrations(
        integration_utils, source.name, project_count=1, user_count=0
    )[IntegrationType.PROJECT][0]
    webhook_integration = _create_webhook_integration(
        integration_utils, source.name, resource_assistant.id
    )

    response = integration_utils.transfer_settings(
        source.name,
        target.name,
        "copy",
        type_of_integration={"user_integrations": False, "project_integrations": True},
    )

    assert_that(response.transferred_count, equal_to(1))
    assert_that(response.transferred[0].alias, equal_to(ordinary_integration.alias))
    assert_that(response.skipped_count, equal_to(1))
    assert_that(response.skipped[0].alias, equal_to(webhook_integration.alias))
    assert_that(response.skipped[0].id, equal_to(webhook_integration.id))
    assert_that(
        response.skipped[0].credential_type, equal_to(CredentialTypes.WEBHOOK.value)
    )
    assert_that(
        _find_by_project_and_alias(
            integration_utils,
            IntegrationType.PROJECT,
            target.name,
            webhook_integration.alias,
        ),
        none(),
        "Webhook integration was copied into the target project despite being copy-blocked.",
    )
    assert_that(
        _aliases_in_project(integration_utils, target.name),
        contains_exactly(ordinary_integration.alias),
        "Target project does not hold exactly the ordinary integration.",
    )
    assert_that(
        _aliases_in_project(integration_utils, source.name),
        has_items(ordinary_integration.alias, webhook_integration.alias),
        "Integrations unexpectedly disappeared from the source project.",
    )


@pytest.mark.integration
@pytest.mark.settings_transfer
@pytest.mark.api
@pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Webhook is disabled on sandbox environments",
)
def test_transfer_copy_rejects_webhook_named_in_list(
    project, integration_utils, assistant
):
    """TC-12: copy mode rejects with 422 a `list` that names a webhook, and transfers nothing (all-or-nothing)."""
    source = project()
    target = project()
    resource_assistant = assistant(project_name=source.name)
    ordinary_integration = _seed_integrations(
        integration_utils, source.name, project_count=1, user_count=0
    )[IntegrationType.PROJECT][0]
    webhook_integration = _create_webhook_integration(
        integration_utils, source.name, resource_assistant.id
    )

    with pytest.raises(Exception) as exec_info:
        integration_utils.transfer_settings(
            source.name,
            target.name,
            "copy",
            integrations_list=[ordinary_integration.alias, webhook_integration.alias],
        )

    assert_error_details(
        exec_info.value.response, 422, "cannot be transferred in copy mode"
    )
    assert_error_details(exec_info.value.response, 422, webhook_integration.alias)
    assert_that(
        _aliases_in_project(integration_utils, target.name),
        empty(),
        "Integrations were copied despite the rejected transfer.",
    )
    assert_that(
        _aliases_in_project(integration_utils, source.name),
        has_items(ordinary_integration.alias, webhook_integration.alias),
        "Integrations unexpectedly disappeared from the source project.",
    )


@pytest.mark.integration
@pytest.mark.settings_transfer
@pytest.mark.api
@pytest.mark.parametrize(
    "type_of_integration, build_list, expected_details",
    transfer_invalid_filter_test_data,
)
def test_transfer_rejects_invalid_filter_combinations(
    project, integration_utils, type_of_integration, build_list, expected_details
):
    """TC-13: invalid `type_of_integration` / `list` combinations are rejected with 422 and change nothing."""
    source = project()
    target = project()
    seeded = _seed_integrations(
        integration_utils, source.name, project_count=1, user_count=1
    )
    listed_aliases = build_list(seeded)

    with pytest.raises(Exception) as exec_info:
        integration_utils.transfer_settings(
            source.name,
            target.name,
            "move",
            type_of_integration=type_of_integration,
            integrations_list=listed_aliases,
        )

    assert_error_details(exec_info.value.response, 422, expected_details)
    _assert_error_names_aliases(exec_info.value.response, listed_aliases)
    _assert_moved_only(integration_utils, seeded, set(), source, target)
