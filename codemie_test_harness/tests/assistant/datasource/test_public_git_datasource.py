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

"""
API E2E tests: Allow creating Git datasource for public
repositories without specifying an integration.

Scenarios:
    TC-001  Create public Git datasource without integration (HTTP 201 + indexing message)
    TC-003  Health check for public Git repo without integration returns success
    TC-004  Private repo without integration is rejected at creation (HTTP 422)
    TC-005  Health check for authenticated Git repo (with integration) returns success
    TC-006  Health check for private repo without integration returns error response
"""

import json

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    greater_than_or_equal_to,
    is_not,
    none,
)
from requests import HTTPError

from codemie_sdk.models.datasource import CodeDataSourceRequest, CodeDataSourceType
from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.utils.base_utils import (
    assert_response,
    get_random_name,
    wait_for_entity,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def public_git_datasource(request, client, default_embedding_llm):
    """TC-001: Create a public Git datasource without integration.

    Yields:
        tuple[dict, DataSource]: The raw create-response dict and the created
        datasource entity retrieved from the list endpoint.

    Cleanup is registered via request.addfinalizer immediately after creation so
    the datasource is always deleted even if wait_for_entity raises before yield.
    """
    datasource_name = get_random_name()
    ds_request = CodeDataSourceRequest(
        project_name=PROJECT,
        link=CredentialsManager.get_parameter("GITHUB_PUBLIC_PROJECT"),
        branch="main",
        index_type=CodeDataSourceType.CODE,
        embeddings_model=default_embedding_llm.base_name,
        description=get_random_name(),
        name=datasource_name,
        # setting_id intentionally omitted — public repo, no integration needed
    )
    create_response = client.datasources.create(ds_request)

    # Register cleanup before wait_for_entity so teardown always runs.
    def _cleanup():
        try:
            datasources = client.datasources.list(per_page=200)
            ds = next((d for d in datasources if d.name == datasource_name), None)
            if ds:
                client.datasources.delete(ds.id)
        except Exception:
            pass

    request.addfinalizer(_cleanup)

    datasource = wait_for_entity(
        lambda: client.datasources.list(per_page=200),
        entity_name=datasource_name,
    )
    yield create_response, datasource


# ---------------------------------------------------------------------------
# TC-001 — Create public Git datasource without integration (API)
# ---------------------------------------------------------------------------


@pytest.mark.datasource
@pytest.mark.git
@pytest.mark.api
@pytest.mark.not_for_parallel_run
def test_create_public_git_datasource_without_integration(public_git_datasource):
    """HTTP 201; response contains indexing-started message; setting_id is None."""
    create_response, datasource = public_git_datasource

    assert_that(
        create_response.get("message", ""),
        contains_string("Indexing of datasource"),
        "Create response should confirm indexing has started",
    )
    assert_that(
        datasource.setting_id,
        none(),
        "Public Git datasource should have no integration (setting_id is None)",
    )


# ---------------------------------------------------------------------------
# TC-003 — Health check: public repo without integration returns success
# ---------------------------------------------------------------------------


@pytest.mark.datasource
@pytest.mark.git
@pytest.mark.api
def test_health_check_public_git_repo_returns_success(client):
    """POST /v1/index/health with public URL and no setting_id → error is None."""
    response = client.datasources.health_check(
        index_type="git",
        git_url=CredentialsManager.get_parameter("GITHUB_PUBLIC_PROJECT"),
        project_name="",
    )

    assert_that(
        response.get("error"),
        none(),
        "Health check for public repo should return no error",
    )
    assert_that(
        response.get("documents_count"),
        greater_than_or_equal_to(0),
        "Health check documents_count should be 0 or greater (probe only, no indexing)",
    )


# ---------------------------------------------------------------------------
# TC-004 — Private repo without integration is rejected at creation (HTTP 422)
# ---------------------------------------------------------------------------


@pytest.mark.gitlab
@pytest.mark.datasource
@pytest.mark.git
@pytest.mark.api
@pytest.mark.not_for_parallel_run
def test_create_private_git_datasource_without_integration_rejected_422(
    client, default_embedding_llm
):
    """POST /v1/application/{name}/index with private URL, no setting_id → HTTP 422."""
    request = CodeDataSourceRequest(
        project_name=PROJECT,
        link=CredentialsManager.get_parameter("GITLAB_PROJECT"),
        branch="main",
        index_type=CodeDataSourceType.CODE,
        embeddings_model=default_embedding_llm.base_name,
        description=get_random_name(),
        name=get_random_name(),
        # setting_id intentionally omitted — private repo, no integration
    )

    with pytest.raises(HTTPError) as exc_info:
        client.datasources.create(request)

    response = exc_info.value.response
    assert_response(response, 422)
    error_body = json.loads(response.content).get("error", {})
    assert_that(
        error_body.get("message", ""),
        equal_to("Repository Not Publicly Accessible"),
        "Error message should identify the repository as not publicly accessible",
    )
    assert_that(
        error_body.get("details", ""),
        contains_string("Please select a Git integration"),
        "Error details should direct the user to select a Git integration",
    )


# ---------------------------------------------------------------------------
# TC-005 — Health check: authenticated repo with integration returns success
# ---------------------------------------------------------------------------


@pytest.mark.gitlab
@pytest.mark.datasource
@pytest.mark.git
@pytest.mark.api
def test_health_check_authenticated_git_repo_with_integration_returns_success(
    client, gitlab_integration
):
    """POST /v1/index/health with private URL + setting_id → error is None."""
    response = client.datasources.health_check(
        index_type="git",
        git_url=CredentialsManager.get_parameter("GITLAB_PROJECT"),
        setting_id=gitlab_integration.id,
        project_name="",
    )

    assert_that(
        response.get("error"),
        none(),
        "Health check for authenticated repo should return no error",
    )
    assert_that(
        response.get("documents_count"),
        greater_than_or_equal_to(0),
        "Health check documents_count should be 0 or greater (probe only, no indexing)",
    )


# ---------------------------------------------------------------------------
# TC-006 — Health check: private repo without integration returns error body
# ---------------------------------------------------------------------------


@pytest.mark.gitlab
@pytest.mark.datasource
@pytest.mark.git
@pytest.mark.api
def test_health_check_private_git_repo_without_integration_returns_error_response(
    client,
):
    """POST /v1/index/health with private URL, no setting_id → HTTP 200 + error set.

    Distinct from TC-004: the health-check endpoint (POST /index/health) returns
    HTTP 200 with an error payload, whereas the creation endpoint (POST
    /application/{name}/index) raises HTTP 422.
    """
    response = client.datasources.health_check(
        index_type="git",
        git_url=CredentialsManager.get_parameter("GITLAB_PROJECT"),
        project_name="",
    )

    assert_that(
        response.get("error"),
        is_not(none()),
        "Health check for private repo without integration should set error field",
    )
