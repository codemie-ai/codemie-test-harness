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
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver
from codemie_test_harness.tests.utils.influxdb_seed import (
    INFLUXDB_SEED,
    SEED_QUERY_RANGE,
)
from codemie_test_harness.tests.utils.jira_seed import Seeded

ELASTIC_TOOL_TASK = """
    send the query to Elastic:
    {'index': 'codemie-*', 'query': {'size': 0, 'aggs': {'indices': {'terms': {'field': '_index', 'size': 5, 'order': {'_count': 'asc'}}}}}}
    return the number of failed from _shards node.
"""

RESPONSE_FOR_ELASTIC = """
    The query was executed successfully: ('0', ['elastic']).
"""


def random_sql_table_name() -> str:
    """A unique, SQL-identifier-safe table name for the Employees fixture.

    ``get_random_name()`` is hyphenated, which is not valid in an unquoted SQL
    identifier, so hyphens are replaced with underscores. Generate this once per
    test and thread the same name through the create/insert/query/delete task
    builders below, so a fixed, shared ``Employees`` table name is never reused
    across concurrent/xdist runs or test files hitting the same database.
    """
    return get_random_name().replace("-", "_")


def sql_tool_create_table_task(table_name: str) -> str:
    return f"""
   Insert a new {table_name} table with Firstname, Lastname, Email, Department columns and fill it with 10 records

   Example for MySQL dialect:
   The first query to create table: {{'sql_query': 'CREATE TABLE {table_name} (
    EmployeeID INT AUTO_INCREMENT PRIMARY KEY,
    Firstname VARCHAR(50),
    Lastname VARCHAR(50),
    Email VARCHAR(100),
    Department VARCHAR(50)
    );'}}

    The second query to fill table: {{'sql_query': "INSERT INTO {table_name} (Firstname, Lastname, Email, Department) VALUES
    ('John', 'Doe', 'john.doe@example.com', 'Engineering'),
    ('Jane', 'Smith', 'jane.smith@example.com', 'Marketing'),
    ('Jim', 'Brown', 'jim.brown@example.com', 'Sales'),
    ('Lucy', 'Adams', 'lucy.adams@example.com', 'Finance'),
    ('Michael', 'Johnson', 'michael.johnson@example.com', 'Engineering'),
    ('Lisa', 'White', 'lisa.white@example.com', 'Human Resources'),
    ('Adam', 'Young', 'adam.young@example.com', 'IT'),
    ('Nancy', 'Green', 'nancy.green@example.com', 'Customer Support'),
    ('Frank', 'Thomas', 'frank.thomas@example.com', 'Operations'),
    ('Anna', 'King', 'anna.king@example.com', 'Research');"}}

"""


def sql_tool_insert_table_task(table_name: str) -> str:
    return (
        f"Add new Employee: Sarah Connor sarah.connor@example.com from Security department. "
        f"{table_name} table has the following columns: Firstname, Lastname, Email, Department."
    )


def sql_tool_query_table_task(table_name: str) -> str:
    return f"SELECT * FROM {table_name} WHERE department = 'Security'"


def sql_tool_delete_table_task(table_name: str) -> str:
    return f"Delete {table_name} table."


RESPONSE_FOR_SQL = """
    Here is the list of employees from the Security department:

    | First Name | Last Name | Email                   | Department |
    |------------|-----------|-------------------------|------------|
    | Sarah      | Connor    | sarah.connor@example.com  | Security   |
"""

# Define test data for SQL tools based on environment
sql_tools_test_data = [
    DataBaseDialect.MY_SQL,
    DataBaseDialect.POSTGRES,
    pytest.param(
        DataBaseDialect.MS_SQL,
        marks=pytest.mark.skipif(
            not EnvironmentResolver.is_sandbox(),
            reason="MS SQL is only available in staging environments",
        ),
        id=DataBaseDialect.MS_SQL,
    ),
]


# InfluxDB-specific task.
# Built from the harness-managed influxdb_seed_point fixture (see influxdb_seed.py /
# influxdb_utils.py) instead of a hardcoded bucket/measurement/host/timestamp/value,
# so the fixture is self-healing across sandbox resets and retention-policy expiry.
# Filtered by the seed's run_id so a concurrent or rerun session's own point for
# the same measurement/host is never mistaken for this one.
def _influxdb_query_task(seed) -> str:
    return f"""
    Execute the query:
    'from(bucket: "{seed.bucket}")
     |> range(start: {SEED_QUERY_RANGE})
     |> filter(fn: (r) => r._measurement == "{seed.measurement}" and r.hostname == "{seed.host}" and r.run_id == "{seed.run_id}")'
    Output format is a table:
    | time | host | region | cpu_load |
    Do not summarize the output!
    """


def _response_for_influxdb(seed) -> str:
    return f"""
    time | host | region | cpu_load
    {seed.time} | {seed.host} | {seed.region} | {seed.cpu_load}
    """


INFLUXDB_QUERY_MEASUREMENT_TASK = Seeded(INFLUXDB_SEED, _influxdb_query_task)
RESPONSE_FOR_INFLUXDB = Seeded(INFLUXDB_SEED, _response_for_influxdb)
