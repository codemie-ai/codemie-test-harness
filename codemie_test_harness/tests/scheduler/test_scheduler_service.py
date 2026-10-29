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

"""Scheduler integration tests for CodeMie.

This module contains tests for scheduler functionality including:
- Basic scheduler operations with different resource types (assistant, workflow, datasource)
- Error handling and validation for invalid cron expressions
- Error handling for invalid resource IDs
- Disabled scheduler verification
"""

import pytest
from datetime import datetime

from tzlocal import get_localzone_name

from codemie_sdk.models.datasource import DataSourceStatus

from hamcrest import (
    assert_that,
    equal_to,
    has_item,
    any_of,
)
from requests import HTTPError
from codemie_test_harness.tests.utils.base_utils import get_random_name, wait_for_entity

from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver


@pytest.fixture
def jira_datasource_with_schedule(datasource_utils, jira_integration):
    next_minute = (datetime.now().minute + 1) % 60
    cron_expression = f"{next_minute} * * * *"
    datasource = datasource_utils.create_jira_datasource(
        setting_id=jira_integration.id,
        cron_expression=cron_expression,
        timezone=get_localzone_name(),
    )
    yield datasource
    datasource_utils.delete_datasource(datasource)


@pytest.mark.scheduler
@pytest.mark.api
@pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Scheduler is disabled on sandbox environments",
)
class TestSchedulerValidIntegrations:
    """Tests for valid scheduler integrations - verify scheduler creation with different resource types."""

    def test_scheduler_with_assistant(
        self, assistant, scheduler_integration, conversation_utils
    ):
        """Test scheduler can be created with assistant resource type.

        This test verifies:
        1. Scheduler integration can be created with an assistant
        2. Integration stores correct configuration (schedule, resource type, resource ID)
        3. Assistant can be triggered manually to verify the resource is valid
        """
        scheduler_alias = get_random_name()
        message = f"Test message for scheduler {scheduler_alias}"

        # Create assistant
        assistant = assistant()

        # Create scheduler integration with assistant
        scheduler_integration(
            alias=scheduler_alias,
            resource_type="assistant",
            resource_id=assistant.id,
            prompt=message,
            is_enabled=True,
        )

        # Wait for conversation
        conversation = wait_for_entity(
            lambda: conversation_utils.list_conversations(),
            entity_name=f"Scheduler: {assistant.id}",
            timeout=180,
        )

        # Verify conversation details
        assert_that(conversation.name, equal_to(f"Scheduler: {assistant.id}"))
        assert_that(conversation.initial_assistant_id, equal_to(assistant.id))
        assert_that(conversation.assistant_ids, has_item(assistant.id))

    def test_scheduler_with_workflow(
        self,
        workflow_with_virtual_assistant,
        scheduler_integration,
        workflow_utils,
    ):
        """Test scheduler can be created with workflow resource type.

        This test verifies:
        1. Scheduler integration can be created with a workflow
        2. Integration stores correct configuration
        3. Workflow can be executed manually to verify the resource is valid
        """
        scheduler_alias = get_random_name()
        message = f"Test message for scheduler {scheduler_alias}"

        # Create a simple workflow
        workflow = workflow_with_virtual_assistant(scheduler_alias)

        # Create scheduler integration with workflow
        scheduler_integration(
            alias=scheduler_alias,
            resource_type="workflow",
            resource_id=workflow.id,
            prompt=message,
            is_enabled=True,
        )

        # Wait for execution with specific prompt
        execution = wait_for_entity(
            lambda: workflow_utils.get_executions(workflow),
            entity_name=message,
            timeout=180,
        )

        # Verify execution details
        assert_that(execution.prompt.strip('""'), equal_to(message))
        assert_that(execution.workflow_id, equal_to(workflow.id))

    @pytest.mark.requires_capability("retrieval")
    @pytest.mark.parametrize(
        "datasource_fixture",
        [
            pytest.param("jira_datasource", marks=pytest.mark.requires_setting("jira")),
            pytest.param(
                "confluence_datasource",
                marks=pytest.mark.requires_setting("confluence"),
            ),
            pytest.param(
                "code_datasource",
                marks=pytest.mark.requires_setting("gitlab", "github"),
            ),
            pytest.param(
                "xwiki_datasource",
                marks=[
                    pytest.mark.xwiki,
                    pytest.mark.skip(reason="No xwiki test environment configured"),
                ],
            ),
        ],
    )
    def test_scheduler_with_datasource(
        self,
        request,
        datasource_fixture,
        scheduler_integration,
        datasource_utils,
    ):
        """Test scheduler can be created with datasource resource type.

        This test verifies:
        1. Scheduler integration can be created with different datasource types
        2. Integration stores correct configuration
        3. Datasource indexing can be triggered manually to verify the resource is valid

        Test is parametrized to work with different datasource types:
        - jira_datasource
        - confluence_datasource
        - code_datasource
        - xwiki_datasource — cron/scheduler-triggered reindex is supported for xWiki
          (only "knowledge_base_file" is in UNSUPPORTED_SCHEDULER_DATASOURCE_TYPES,
          settings_request_validator.py:51); contrast with webhook triggering, which
          xWiki does not support (test_webhook_with_datasource).
        """
        # Get the datasource from the fixture
        datasource = request.getfixturevalue(datasource_fixture)
        scheduler_alias = get_random_name()

        triggered_datasource = datasource_utils.get_datasource(datasource.id)

        # Create scheduler integration with datasource
        scheduler_integration(
            alias=scheduler_alias,
            resource_type="datasource",
            resource_id=datasource.id,
            is_enabled=True,
        )

        # Verify datasource exists and check its status (indexing should be in progress)
        triggered_datasource = datasource_utils.wait_for_update_date_change(
            datasource_id=datasource.id,
            initial_update_date=triggered_datasource.update_date,
            timeout=180,
        )

        assert_that(triggered_datasource.id, equal_to(datasource.id))
        assert_that(triggered_datasource.name, equal_to(datasource.name))
        assert_that(
            triggered_datasource.status,
            any_of(
                equal_to(DataSourceStatus.COMPLETED),
                equal_to(DataSourceStatus.IN_PROGRESS),
                equal_to(DataSourceStatus.FETCHING),
            ),
        )


@pytest.mark.scheduler
@pytest.mark.api
class TestSchedulerInvalidIntegrations:
    """Tests for invalid scheduler integrations - verify proper error handling."""

    @pytest.mark.parametrize(
        "invalid_cron",
        [
            ("invalid_cron_expression"),
            ("* * * *"),
            ("60 0 * * *"),
            ("0 25 * * *"),
            ("0 0 32 * *"),
            ("0 0 * 13 *"),
            ("0 0 * * 8"),
            (""),
        ],
    )
    def test_scheduler_with_invalid_cron(
        self, assistant, scheduler_integration, invalid_cron
    ):
        """Test scheduler creation fails with invalid cron expressions.

        This test verifies that the system properly validates cron expressions
        and rejects invalid formats.

        Parametrized with various invalid cron expressions:
        - Completely invalid format
        - Incomplete expressions
        - Out-of-range values for each field
        - Empty expressions
        """
        scheduler_alias = get_random_name()
        created_assistant = assistant()

        with pytest.raises(HTTPError) as exc_info:
            scheduler_integration(
                alias=scheduler_alias,
                resource_type="assistant",
                resource_id=created_assistant.id,
                schedule=invalid_cron,
                prompt=scheduler_alias,
                is_enabled=True,
            )

        assert_that(exc_info.value.response.status_code, equal_to(422))
        assert_that(
            exc_info.value.response.json()["error"]["message"],
            any_of(
                equal_to("Invalid cron expression"), equal_to("Invalid schedule format")
            ),
        )

    @pytest.mark.parametrize(
        "resource_type, error",
        [
            ("assistant", "Assistant not found"),
            ("workflow", "Workflow not found"),
            ("datasource", "Datasource not found"),
        ],
    )
    def test_scheduler_with_invalid_resource_id(
        self, scheduler_integration, resource_type, error
    ):
        """Test scheduler creation with non-existent resource ID.

        This test verifies that the system handles invalid resource IDs properly,
        either by rejecting them during creation or handling them gracefully during execution.
        """
        scheduler_alias = get_random_name()
        invalid_resource_id = "invalid_resource_" + get_random_name()

        with pytest.raises(HTTPError) as exc_info:
            scheduler_integration(
                alias=scheduler_alias,
                resource_type=resource_type,
                resource_id=invalid_resource_id,
                prompt=scheduler_alias,
                is_enabled=True,
            )

        assert_that(exc_info.value.response.status_code, equal_to(404))
        assert_that(
            exc_info.value.response.json()["error"]["message"],
            equal_to(error),
        )

    def test_scheduler_with_invalid_resource_type(
        self, assistant, scheduler_integration
    ):
        """Test scheduler creation with invalid resource type.

        This test verifies that the system properly validates resource types.
        """
        scheduler_alias = get_random_name()
        created_assistant = assistant()

        with pytest.raises(HTTPError) as exc_info:
            scheduler_integration(
                alias=scheduler_alias,
                resource_type="invalid_resource_type",
                resource_id=created_assistant.id,
                prompt=scheduler_alias,
                is_enabled=True,
            )

        # Verify error has 422 status code (Unprocessable Entity)
        assert_that(exc_info.value.response.status_code, equal_to(422))
        assert_that(
            exc_info.value.response.json()["error"]["message"],
            equal_to("Invalid resource type"),
        )


@pytest.mark.scheduler
@pytest.mark.api
@pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Scheduler is disabled on sandbox environments",
)
class TestDataSourceNativeScheduler:
    """Regression tests for datasource-native scheduler re-indexing.

    Tests the path where cron_expression is set directly on the datasource
    (not via a separate Scheduler integration).
    """

    @pytest.mark.jira
    @pytest.mark.requires_capability("retrieval")
    def test_datasource_with_cron_expression_triggers_reindex(
        self,
        jira_datasource_with_schedule,
        datasource_utils,
    ):
        """Test that a Jira datasource created with cron_expression is automatically re-indexed.

        Verifies:
        1. Datasource is successfully created with a cron_expression.
        2. The scheduler triggers a re-index without any manual intervention.
        3. update_date advances after the cron fires.
        """
        datasource = jira_datasource_with_schedule

        reindexed = datasource_utils.wait_for_update_date_change(
            datasource_id=datasource.id,
            initial_update_date=datasource.update_date,
            timeout=180,
        )

        assert_that(reindexed.id, equal_to(datasource.id))
        assert_that(
            reindexed.status,
            any_of(
                equal_to(DataSourceStatus.COMPLETED),
                equal_to(DataSourceStatus.IN_PROGRESS),
                equal_to(DataSourceStatus.FETCHING),
            ),
        )
