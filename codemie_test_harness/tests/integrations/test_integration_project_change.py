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

"""API tests for changing the project of an existing integration.

PUT /v1/settings/project/{id} and PUT /v1/settings/user/{id} move the integration to the
``project_name`` of the request while keeping its id. Covers TC_002, TC_003, TC_004, TC_006
and TC_007.
"""

from typing import List, Optional

import pytest
from hamcrest import (
    any_of,
    assert_that,
    equal_to,
    has_item,
    is_not,
    none,
    not_none,
)
from requests import HTTPError

from codemie_sdk.models.integration import (
    CredentialTypes,
    CredentialValues,
    Integration,
    IntegrationType,
)
from codemie_test_harness.tests.test_data.integration_project_change_test_data import (
    ACCESS_DENIED_DETAILS,
    ALIAS_COLLISION_DETAILS,
    INTEGRATION_UPDATED_MESSAGE,
    git_datasource_source,
    project_change_scope_test_data,
)
from codemie_test_harness.tests.utils.base_utils import (
    assert_error_details,
    get_random_name,
    wait_for_entity,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.integration_utils import IntegrationUtils


def _integration_request(
    project_name: str,
    alias: str,
    setting_type: IntegrationType,
    setting_id: Optional[str] = None,
    credential_type: CredentialTypes = CredentialTypes.GIT,
    credential_values: Optional[List[CredentialValues]] = None,
) -> Integration:
    """Request body for creating (no id) or updating (with id) an integration."""
    return Integration(
        id=setting_id,
        project_name=project_name,
        alias=alias,
        credential_type=credential_type,
        credential_values=credential_values or CredentialsManager.gitlab_credentials(),
        setting_type=setting_type,
    )


@pytest.fixture
def create_integration_in_project(integration_utils):
    """Factory creating an integration in an explicit project; deletes it by id on teardown.

    ``IntegrationUtils.create_integration`` finds the new row by alias only, which is
    ambiguous when two projects hold the same alias, so the row is looked up by
    project and alias here. ``utils`` lets a non-admin client create the row.
    """
    created = []

    def _create(
        project_name: str,
        alias: Optional[str] = None,
        setting_type: IntegrationType = IntegrationType.PROJECT,
        credential_type: CredentialTypes = CredentialTypes.GIT,
        credential_values: Optional[List[CredentialValues]] = None,
        utils: Optional[IntegrationUtils] = None,
    ) -> Integration:
        utils = utils or integration_utils
        alias = alias or get_random_name()
        utils.send_create_integration_request(
            _integration_request(
                project_name,
                alias,
                setting_type,
                credential_type=credential_type,
                credential_values=credential_values,
            )
        )
        found = utils.get_integration_by_project_and_alias(
            project_name, alias, setting_type
        )
        assert_that(
            found,
            not_none(),
            f"Integration '{alias}' was not found in project '{project_name}' after creation.",
        )
        created.append((found.id, setting_type))
        return found

    yield _create

    for integration_id, setting_type in created:
        try:
            integration_utils.delete_integration_by_id(integration_id, setting_type)
        except Exception:
            pass


@pytest.fixture
def create_code_datasource_in_project(datasource_utils, default_embedding_llm):
    """Factory creating an indexed code datasource bound to an integration; deletes it on teardown."""
    created = []

    def _create(project_name: str, setting_id: str, link: str):
        datasource = datasource_utils.create_code_datasource(
            project_name=project_name,
            link=link,
            branch="main",
            embeddings_model=default_embedding_llm.base_name,
            setting_id=setting_id,
        )
        created.append(datasource)
        return datasource

    yield _create

    for datasource in created:
        try:
            datasource_utils.delete_datasource(datasource)
        except Exception:
            pass


@pytest.mark.gitlab
@pytest.mark.integration
@pytest.mark.project_integration
@pytest.mark.api
@pytest.mark.parametrize("setting_type", project_change_scope_test_data)
def test_change_integration_project_moves_integration_keeping_id(
    project, integration_utils, create_integration_in_project, setting_type
):
    # @case integration-project-change_TC_002
    """PUT with a different project_name moves the integration to that project and keeps its id."""
    source = project()
    target = project()
    created = create_integration_in_project(source.name, setting_type=setting_type)

    response = integration_utils.update_integration(
        _integration_request(target.name, created.alias, setting_type, created.id)
    )

    assert_that(
        response["message"],
        equal_to(INTEGRATION_UPDATED_MESSAGE),
        "Project change update response message is not as expected.",
    )
    assert_that(
        integration_utils.list_integration_ids_in_project(target.name, setting_type),
        has_item(created.id),
        "Integration with its original id is missing from the target project.",
    )
    assert_that(
        integration_utils.list_integration_ids_in_project(source.name, setting_type),
        is_not(has_item(created.id)),
        "Integration is still listed in the source project after the move.",
    )


@pytest.fixture
def source_project_admin_member(project, user_utils, non_admin_user):
    """Plain user (no platform role) who is admin of a fresh source project but not of a fresh target.

    The project integration is created by the platform admin, so the user owns nothing: the
    backend lets them update it only because they are admin of its (source) project
    (``ProjectSetting.is_managed_by``). They hold no membership at all in the target project.
    """
    _, member_id, member_client = non_admin_user
    source = project()
    target = project()
    user_utils.assign_user_to_project(member_id, source.name, is_project_admin=True)
    return source, target, IntegrationUtils(member_client)


@pytest.fixture
def integration_visible_to_source_admin_member(
    source_project_admin_member, create_integration_in_project
):
    """Source-project integration that the plain-user project admin can already see.

    The role change reaches the backend through a cache, so the fixture waits until the member
    can list the row before the test acts on it.
    """
    source, target, member_utils = source_project_admin_member
    created = create_integration_in_project(source.name)
    wait_for_entity(
        lambda: member_utils.list_integrations(IntegrationType.PROJECT, per_page=200),
        entity_name=created.alias,
        timeout=60,
    )
    return source, target, member_utils, created


@pytest.mark.gitlab
@pytest.mark.integration
@pytest.mark.project_integration
@pytest.mark.api
def test_change_integration_project_denied_without_target_project_admin(
    integration_utils, integration_visible_to_source_admin_member
):
    # @case integration-project-change_TC_003
    """A caller who is admin of the source but not of the target project gets 403; the integration stays put."""
    source, target, member_utils, created = integration_visible_to_source_admin_member

    with pytest.raises(HTTPError) as exc_info:
        member_utils.update_integration(
            _integration_request(
                target.name,
                created.alias,
                IntegrationType.PROJECT,
                created.id,
            )
        )

    assert_error_details(
        exc_info.value.response,
        403,
        f"{ACCESS_DENIED_DETAILS} '{target.name}'",
    )
    unchanged = integration_utils.get_integration_by_id(
        created.id, IntegrationType.PROJECT
    )
    assert_that(
        unchanged,
        not_none(),
        "Integration disappeared after the denied project change.",
    )
    assert_that(
        unchanged.project_name,
        equal_to(source.name),
        "Integration moved despite the caller not being admin of the target project.",
    )


@pytest.mark.gitlab
@pytest.mark.integration
@pytest.mark.project_integration
@pytest.mark.api
def test_change_integration_project_rejected_on_alias_collision(
    project, integration_utils, create_integration_in_project
):
    # @case integration-project-change_TC_004
    """An alias already used in the target project gives 422 and leaves the integration in the source project."""
    source = project()
    target = project()
    alias = get_random_name()
    source_integration = create_integration_in_project(source.name, alias=alias)
    target_integration = create_integration_in_project(target.name, alias=alias)

    with pytest.raises(HTTPError) as exc_info:
        integration_utils.update_integration(
            _integration_request(
                target.name,
                alias,
                IntegrationType.PROJECT,
                source_integration.id,
            )
        )

    assert_error_details(
        exc_info.value.response, 422, f"{ALIAS_COLLISION_DETAILS} {alias}"
    )
    still_in_source = integration_utils.get_integration_by_project_and_alias(
        source.name, alias, IntegrationType.PROJECT
    )
    assert_that(
        still_in_source,
        not_none(),
        "Integration is no longer in the source project after the rejected move.",
    )
    assert_that(
        still_in_source.id,
        equal_to(source_integration.id),
        "Source integration id changed after the rejected move.",
    )
    assert_that(
        still_in_source.credential_type,
        equal_to(source_integration.credential_type),
        "Source integration credential type changed after the rejected move.",
    )
    still_in_target = integration_utils.get_integration_by_project_and_alias(
        target.name, alias, IntegrationType.PROJECT
    )
    assert_that(
        still_in_target.id,
        equal_to(target_integration.id),
        "Target project's integration was altered by the rejected move.",
    )


@pytest.mark.gitlab
@pytest.mark.integration
@pytest.mark.project_integration
@pytest.mark.api
def test_change_ms_teams_integration_project_rejected(
    default_llm,
    project,
    assistant_factory,
    integration_utils,
    create_integration_in_project,
):
    # @case integration-project-change_TC_006
    """An MS Teams integration cannot change project: 400 'Project mismatch', it stays in its project."""
    source = project()
    target = project()
    assistant = assistant_factory.create(
        llm_model_type=default_llm.base_name, project_name=source.name
    )
    assistant_ids = [CredentialValues(key="assistant_ids", value=[assistant.id])]
    created = create_integration_in_project(
        source.name,
        credential_type=CredentialTypes.MS_TEAMS,
        credential_values=assistant_ids,
    )

    with pytest.raises(HTTPError) as exc_info:
        integration_utils.update_integration(
            _integration_request(
                target.name,
                created.alias,
                IntegrationType.PROJECT,
                created.id,
                credential_type=CredentialTypes.MS_TEAMS,
                credential_values=assistant_ids,
            )
        )

    assert_error_details(
        exc_info.value.response,
        400,
        f"belongs to project '{source.name}', not '{target.name}'",
    )
    unchanged = integration_utils.get_integration_by_id(
        created.id, IntegrationType.PROJECT
    )
    assert_that(
        unchanged,
        not_none(),
        "MS Teams integration disappeared after the rejected project change.",
    )
    assert_that(
        unchanged.project_name,
        equal_to(source.name),
        "MS Teams integration moved to another project.",
    )


@pytest.mark.requires_capability("retrieval")
@pytest.mark.gitlab
@pytest.mark.integration
@pytest.mark.project_integration
@pytest.mark.api
def test_change_integration_project_unlinks_source_project_datasources(
    project,
    integration_utils,
    datasource_utils,
    create_integration_in_project,
    create_code_datasource_in_project,
):
    # @case integration-project-change_TC_007
    """Moving an integration clears setting_id on the source-project datasources that used it."""
    source = project()
    target = project()
    git_source = git_datasource_source()
    created = create_integration_in_project(
        source.name, credential_values=git_source.credentials
    )
    datasource = create_code_datasource_in_project(
        source.name, created.id, git_source.link
    )
    assert_that(
        datasource_utils.get_datasource(datasource.id).setting_id,
        equal_to(created.id),
        "Datasource is not bound to the integration before the move.",
    )

    response = integration_utils.update_integration(
        _integration_request(
            target.name,
            created.alias,
            IntegrationType.PROJECT,
            created.id,
            credential_values=git_source.credentials,
        )
    )

    assert_that(
        response["message"],
        equal_to(INTEGRATION_UPDATED_MESSAGE),
        "Project change update response message is not as expected.",
    )
    moved = integration_utils.get_integration_by_id(created.id, IntegrationType.PROJECT)
    assert_that(
        moved.project_name,
        equal_to(target.name),
        "Integration was not moved to the target project.",
    )
    assert_that(
        datasource_utils.get_datasource(datasource.id).setting_id,
        any_of(none(), equal_to("")),
        "Datasource left in the source project still references the moved integration.",
    )
