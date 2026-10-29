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

import pytest
from codemie_sdk.models.integration import CredentialTypes

from codemie_test_harness.tests.enums.integrations import DataBaseDialect
from codemie_test_harness.tests.enums.tools import DataManagementTool
from codemie_test_harness.tests.test_data.data_management_tools_test_data import (
    ELASTIC_TOOL_TASK,
    RESPONSE_FOR_ELASTIC,
    sql_tools_test_data,
    random_sql_table_name,
    sql_tool_create_table_task,
    sql_tool_delete_table_task,
    sql_tool_insert_table_task,
    sql_tool_query_table_task,
    RESPONSE_FOR_SQL,
    INFLUXDB_QUERY_MEASUREMENT_TASK,
    RESPONSE_FOR_INFLUXDB,
)
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    assert_tool_triggered,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver

pytestmark = pytest.mark.skipif(
    EnvironmentResolver.is_localhost(),
    reason="Skipping this tests on local environment",
)


@pytest.mark.workflow
@pytest.mark.virtual_workflow
@pytest.mark.elastic
@pytest.mark.api
def test_workflow_with_elastic_tools(
    workflow_with_virtual_assistant,
    workflow_utils,
    integration_utils,
    similarity_check,
):
    """Test workflow execution with Elastic tools."""
    assistant_and_state_name = get_random_name()
    credential_values = CredentialsManager.elasticsearch_credentials()
    integration = integration_utils.create_integration(
        CredentialTypes.ELASTIC, credential_values
    )

    test_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        DataManagementTool.ELASTIC,
        integration=integration,
        task=ELASTIC_TOOL_TASK,
    )
    response = workflow_utils.execute_workflow(
        test_workflow.id, assistant_and_state_name
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )
    assert_tool_triggered(DataManagementTool.ELASTIC, triggered_tools)
    similarity_check.check_similarity(response, RESPONSE_FOR_ELASTIC)


@pytest.mark.workflow
@pytest.mark.virtual_workflow
@pytest.mark.sql
@pytest.mark.api
@pytest.mark.parametrize(
    "db_dialect",
    sql_tools_test_data,
)
def test_workflow_with_sql_tools(
    workflow_with_virtual_assistant,
    workflow_utils,
    integration_utils,
    similarity_check,
    db_dialect,
):
    """Test workflow execution with SQL data management tools (various dialects)."""
    assistant_and_state_name = get_random_name()
    credential_values = CredentialsManager.sql_credentials(db_dialect)
    integration = integration_utils.create_integration(
        CredentialTypes.SQL, credential_values
    )

    test_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        DataManagementTool.SQL,
        integration=integration,
        task=f"DB dialect is {db_dialect.value}. Run SQL tool and execute SQL queries to perform user requests.",
    )

    table_name = random_sql_table_name()

    # Step 1: Create table
    workflow_utils.execute_workflow(
        test_workflow.id,
        assistant_and_state_name,
        sql_tool_create_table_task(table_name),
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )
    assert_tool_triggered(DataManagementTool.SQL, triggered_tools)

    # Step 2: Insert data
    workflow_utils.execute_workflow(
        test_workflow.id,
        assistant_and_state_name,
        sql_tool_insert_table_task(table_name),
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )
    assert_tool_triggered(DataManagementTool.SQL, triggered_tools)

    # Step 3: Query data
    response = workflow_utils.execute_workflow(
        test_workflow.id,
        assistant_and_state_name,
        sql_tool_query_table_task(table_name),
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )
    assert_tool_triggered(DataManagementTool.SQL, triggered_tools)

    # Step 4: Delete table
    workflow_utils.execute_workflow(
        test_workflow.id,
        assistant_and_state_name,
        sql_tool_delete_table_task(table_name),
    )
    triggered_tools = workflow_utils.extract_triggered_tools_from_execution(
        test_workflow
    )
    assert_tool_triggered(DataManagementTool.SQL, triggered_tools)

    similarity_check.check_similarity(response, RESPONSE_FOR_SQL)


@pytest.mark.workflow
@pytest.mark.virtual_workflow
@pytest.mark.influx
@pytest.mark.api
@pytest.mark.skipif(
    not EnvironmentResolver.is_sandbox(),
    reason="InfluxDB is only available in sandbox environments",
)
def test_workflow_with_influxdb_tools(
    workflow_with_virtual_assistant,
    workflow_utils,
    integration_utils,
    similarity_check,
    seeded,
):
    """Test workflow execution with InfluxDB tools."""

    assistant_and_state_name = get_random_name()
    credential_values = CredentialsManager.sql_credentials(DataBaseDialect.INFLUX)
    integration = integration_utils.create_integration(
        CredentialTypes.SQL, credential_values
    )

    test_workflow = workflow_with_virtual_assistant(
        assistant_and_state_name,
        DataManagementTool.SQL,
        integration=integration,
        task=f"DB dialect is {DataBaseDialect.INFLUX.value}. Run SQL tool and execute InfluxQL queries to perform user requests.",
    )

    # Query the measurement
    response = workflow_utils.execute_workflow(
        test_workflow.id,
        assistant_and_state_name,
        seeded(INFLUXDB_QUERY_MEASUREMENT_TASK),
    )

    similarity_check.check_similarity(response, seeded(RESPONSE_FOR_INFLUXDB))
