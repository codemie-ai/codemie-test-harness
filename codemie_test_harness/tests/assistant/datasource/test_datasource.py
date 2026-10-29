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
from codemie_sdk.models.datasource import DataSourceType
from hamcrest import (
    assert_that,
    instance_of,
    all_of,
    has_length,
    greater_than,
    is_in,
    has_property,
    is_not,
    equal_to,
    is_,
)


@pytest.mark.datasource
@pytest.mark.api
def test_list_datasources(search_utils):
    datasource_types = [DataSourceType.CODE, DataSourceType.CONFLUENCE]
    datasource_models = search_utils.list_data_sources(
        datasource_types=datasource_types
    )
    assert_that(
        datasource_models, all_of(instance_of(list), has_length(greater_than(0)))
    )
    for model in datasource_models:
        assert_that(model.type, is_in(datasource_types))


@pytest.mark.datasource
@pytest.mark.api
@pytest.mark.parametrize(
    "datasource_type",
    [
        DataSourceType.CODE,
        DataSourceType.CONFLUENCE,
        DataSourceType.FILE,
        DataSourceType.JIRA,
        DataSourceType.GOOGLE,
    ],
)
def test_get_datasource_by_id(datasource_utils, datasource_type, search_utils):
    datasources = search_utils.list_data_sources(
        datasource_types=datasource_type, per_page=50
    )
    assert_that(datasources, all_of(instance_of(list), has_length(greater_than(0))))

    original_datasource = datasources[0]
    datasource_id = original_datasource.id
    retrieved_datasource = datasource_utils.get_datasource(datasource_id)

    # Compare full objects (they should be identical)
    assert_that(
        retrieved_datasource,
        all_of(
            is_not(None),
        ),
    )
    assert_that(retrieved_datasource.id, equal_to(original_datasource.id))
    assert_that(retrieved_datasource.name, equal_to(original_datasource.name))
    assert_that(
        retrieved_datasource.project_name,
        equal_to(original_datasource.project_name),
    )
    assert_that(
        retrieved_datasource.created_by,
        equal_to(original_datasource.created_by),
    )
    assert_that(
        retrieved_datasource.shared_with_project,
        equal_to(original_datasource.shared_with_project),
    )
    assert_that(
        retrieved_datasource.created_date,
        equal_to(original_datasource.created_date),
    )
    assert_that(
        retrieved_datasource.error_message,
        equal_to(original_datasource.error_message),
    )
    assert_that(
        retrieved_datasource.processing_info.processed_documents_count,
        is_not(None),
    )

    if datasource_type == DataSourceType.CODE:
        assert_that(original_datasource.description, is_(None))
        assert_that(
            retrieved_datasource,
            all_of(
                has_property("confluence", None),
                has_property("jira", None),
                # has_property("tokens_usage", is_not(None)),
                has_property("code"),
            ),
        )
        assert_that(
            retrieved_datasource.code.link,
            equal_to(original_datasource.code.link),
        )
        assert_that(retrieved_datasource.code.branch, is_not(None))
    elif datasource_type == DataSourceType.CONFLUENCE:
        assert_that(
            retrieved_datasource,
            all_of(
                has_property("code", None),
                has_property("jira", None),
                has_property("tokens_usage", is_not(None)),
                has_property("confluence", is_not(None)),
            ),
        )
        assert_that(retrieved_datasource.confluence.cql, is_not(None))
    elif datasource_type == DataSourceType.JIRA:
        assert_that(
            retrieved_datasource,
            all_of(
                has_property("code", None),
                has_property("confluence", None),
                has_property("jira", is_not(None)),
            ),
        )
        assert_that(retrieved_datasource.jira.jql, is_not(None))
    elif datasource_type == DataSourceType.GOOGLE:
        assert_that(
            retrieved_datasource,
            all_of(
                has_property("code", None),
                has_property("confluence", None),
                has_property("jira", None),
                has_property("google_doc_link", is_not(None)),
            ),
        )
