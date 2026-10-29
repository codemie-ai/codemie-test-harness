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

import secrets

import pytest
from codemie_sdk.models.workflow import WorkflowMode

from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.workflow_utils import WorkflowUtils
from codemie_test_harness.tests.utils.yaml_utils import (
    AssistantModel,
    StateModel,
    WorkflowYamlModel,
    prepare_yaml_content,
)


@pytest.fixture
def non_admin_user(keycloak_utils):
    uid = secrets.token_hex(4)
    email = f"autotest_wh_member_{uid}@email.com"
    password = keycloak_utils.create_test_user(email=email, project_name=email)
    member_client = get_client(username=email, password=password)
    member_id = member_client.users.about_me().user_id
    yield email, member_id, member_client
    keycloak_utils.delete_user(email)


@pytest.fixture
def project_with_non_admin_member(project_utils, non_admin_user):
    uid = secrets.token_hex(4)
    project_name = f"autotest-wh-member-{uid}"
    _, member_id, member_client = non_admin_user
    project_utils.create_project(
        name=project_name,
        description="Autotest webhook cross-user scenario",
    )
    project_utils.assign_user_to_project(
        project_name, member_id, is_project_admin=False
    )
    yield project_name, member_client
    project_utils.delete_project_cascade(project_name)


@pytest.fixture
def member_workflow_with_virtual_assistant(non_admin_user, default_llm):
    """Create a workflow using the non-admin member client."""
    _, _, member_client = non_admin_user
    member_workflow_utils = WorkflowUtils(member_client)
    created_workflow = None

    def _create(assistant_and_state_name, project_name=None):
        nonlocal created_workflow
        assistant = AssistantModel(
            id=assistant_and_state_name,
            model=default_llm.base_name,
            system_prompt="You are a helpful integration test assistant.",
        )
        state = StateModel(
            id=assistant_and_state_name,
            assistant_id=assistant_and_state_name,
        )
        workflow_yaml = WorkflowYamlModel(
            assistants=[assistant],
            states=[state],
        )
        yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))
        created_workflow = member_workflow_utils.create_workflow(
            workflow_name=assistant_and_state_name,
            workflow_type=WorkflowMode.SEQUENTIAL,
            shared=True,
            workflow_yaml=yaml_content,
            project_name=project_name,
        )
        return created_workflow

    yield _create

    if created_workflow:
        member_workflow_utils.delete_workflow(created_workflow)


@pytest.fixture
def project_with_member_factory(project_utils, keycloak_utils):
    """Factory fixture: creates a project and assigns a fresh member with given platform and project roles.

    is_platform_admin=True  → user created with developer + admin roles
    is_platform_admin=False → user created with developer role only
    Both users and the project are deleted in teardown.
    """
    created = []  # list of (project_name, member_id, email)

    def _create(is_platform_admin: bool, is_project_admin: bool):
        uid = secrets.token_hex(4)
        project_name = f"autotest-wh-member-{uid}"
        project_utils.create_project(
            name=project_name,
            description="Autotest webhook cross-user scenario",
        )

        email = f"autotest_wh_member_{uid}@email.com"
        if is_platform_admin:
            password = keycloak_utils.create_test_user(email=email, project_name=email)
        else:
            password = keycloak_utils.create_platform_user(email=email)

        member_client = get_client(username=email, password=password)
        member_id = member_client.users.about_me().user_id
        project_utils.assign_user_to_project(
            project_name, member_id, is_project_admin=is_project_admin
        )
        member_client.refresh_token()
        created.append((project_name, member_id, email))
        return project_name, WorkflowUtils(member_client)

    yield _create

    for project_name, member_id, email in created:
        project_utils.remove_user_from_project(project_name, member_id)
        project_utils.delete_project(project_name)
        keycloak_utils.delete_user(email)
