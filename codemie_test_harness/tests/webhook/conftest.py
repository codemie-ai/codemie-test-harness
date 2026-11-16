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
from contextlib import ExitStack

import pytest
from codemie_sdk.models.workflow import WorkflowMode

from codemie_test_harness.tests.utils.user_lifecycle_utils import new_logged_in_user
from codemie_test_harness.tests.utils.workflow_utils import WorkflowUtils
from codemie_test_harness.tests.utils.yaml_utils import (
    AssistantModel,
    StateModel,
    WorkflowYamlModel,
    prepare_yaml_content,
)


@pytest.fixture
def project_with_non_admin_member(project_utils, platform_user):
    uid = secrets.token_hex(4)
    project_name = f"autotest-wh-member-{uid}"
    member_id, member_client = platform_user.user_id, platform_user.client
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
def member_workflow_with_virtual_assistant(platform_user, default_llm):
    """Create a workflow using the non-admin member client."""
    member_client = platform_user.client
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
    with ExitStack() as cleanup:

        def _create(is_platform_admin: bool, is_project_admin: bool):
            uid = secrets.token_hex(4)
            project_name = f"autotest-wh-member-{uid}"
            project_utils.create_project(
                name=project_name,
                description="Autotest webhook cross-user scenario",
            )
            cleanup.callback(project_utils.delete_project, project_name)
            member = cleanup.enter_context(
                new_logged_in_user(
                    keycloak_utils,
                    f"autotest_wh_member_{uid}@email.com",
                    admin=is_platform_admin,
                )
            )
            project_utils.assign_user_to_project(
                project_name, member.user_id, is_project_admin=is_project_admin
            )
            # Runs first (last registered): unassign, delete the user, delete the project.
            cleanup.callback(
                project_utils.remove_user_from_project, project_name, member.user_id
            )
            member.client.refresh_token()
            return project_name, WorkflowUtils(member.client)

        yield _create
