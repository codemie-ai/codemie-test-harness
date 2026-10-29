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

from codemie_test_harness.tests.enums.integrations import DataBaseDialect
from codemie_test_harness.tests.enums.tools import DataManagementTool, Toolkit
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver

ELASTIC_TOOL_TASK = {
    "index": "_all",
    "query": '{"query": {"prefix": {"_index": "codemie"}}, "_source": {"excludes": ["vector"]}}',
}


def _configured_tables(key: str) -> list[str]:
    """Table names from a comma-separated config value; empty when unset."""
    value = CredentialsManager.get_parameter(key) or ""
    return [name.strip() for name in value.split(",") if name.strip()]


# The list-tables tests expect these tables to already exist in the sandbox databases.
# Their names come from config (SANDBOX_<DIALECT>_TABLES) instead of being hardcoded.
# Nothing is created here: a missing table still fails its test, and an unset value
# skips that dialect's test.
MYSQL_TABLES = _configured_tables("SANDBOX_MYSQL_TABLES")
POSTGRES_TABLES = _configured_tables("SANDBOX_POSTGRES_TABLES")
MSSQL_TABLES = _configured_tables("SANDBOX_MSSQL_TABLES")
MYSQL_DATABASE_NAME = CredentialsManager.get_parameter("SANDBOX_MYSQL_DATABASE_NAME")
MSSQL_DATABASE_NAME = CredentialsManager.get_parameter("SANDBOX_MSSQL_DATABASE_NAME")

sql_tools_test_data = [
    pytest.param(
        Toolkit.DATA_MANAGEMENT,
        DataManagementTool.SQL,
        DataBaseDialect.MY_SQL,
        {"sql_query": "SHOW TABLES"},
        [{f"Tables_in_{MYSQL_DATABASE_NAME}": table} for table in MYSQL_TABLES],
        marks=pytest.mark.skipif(
            not MYSQL_TABLES, reason="SANDBOX_MYSQL_TABLES is not set"
        ),
    ),
    pytest.param(
        Toolkit.DATA_MANAGEMENT,
        DataManagementTool.SQL,
        DataBaseDialect.POSTGRES,
        {
            "sql_query": "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
        },
        [{"table_name": table} for table in POSTGRES_TABLES],
        marks=pytest.mark.skipif(
            not POSTGRES_TABLES, reason="SANDBOX_POSTGRES_TABLES is not set"
        ),
    ),
    pytest.param(
        Toolkit.DATA_MANAGEMENT,
        DataManagementTool.SQL,
        DataBaseDialect.MS_SQL,
        {
            "sql_query": f"""SELECT table_name
                            FROM
                            information_schema.tables
                            WHERE
                            table_type = 'BASE TABLE'
                            AND
                            table_catalog = '{MSSQL_DATABASE_NAME}'
                            AND
                            table_schema = 'dbo';
                            """
        },
        [{"table_name": table} for table in MSSQL_TABLES],
        marks=[
            pytest.mark.skipif(
                not EnvironmentResolver.is_sandbox(),
                reason="MS SQL is only available in sandbox environments",
            ),
            pytest.mark.skipif(
                not MSSQL_TABLES, reason="SANDBOX_MSSQL_TABLES is not set"
            ),
        ],
        id=DataBaseDialect.MS_SQL,
    ),
]
