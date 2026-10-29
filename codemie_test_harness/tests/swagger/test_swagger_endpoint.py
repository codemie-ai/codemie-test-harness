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
API tests for Swagger documentation endpoint.

This module tests the health and accessibility of the Swagger/OpenAPI documentation endpoint.
"""

import pytest
import requests
from hamcrest import assert_that, equal_to, is_in, less_than


@pytest.mark.api
@pytest.mark.swagger
@pytest.mark.smoke
@pytest.mark.sanity
def test_swagger_endpoint_is_accessible(swagger_utils):
    """
    Test that the Swagger documentation endpoint is accessible and returns a successful response.

    The test verifies:
    1. The endpoint responds with HTTP 200 status code
    2. The endpoint is reachable and healthy
    """
    response = swagger_utils.get_swagger_page()

    assert_that(response.status_code, equal_to(200))


@pytest.mark.sanity
@pytest.mark.api
@pytest.mark.swagger
@pytest.mark.smoke
def test_swagger_endpoint_returns_html(swagger_utils):
    """
    Test that the Swagger documentation endpoint returns HTML content.

    The test verifies:
    1. The response content type is HTML
    2. The response contains expected Swagger/OpenAPI keywords
    """
    response = swagger_utils.get_swagger_page()

    assert_that(response.status_code, equal_to(200))

    content_type = response.headers.get("Content-Type", "")
    assert_that("text/html", is_in(content_type))

    # Verify the response contains Swagger/OpenAPI related content
    assert_that(swagger_utils.validate_swagger_page_content(response), equal_to(True))


@pytest.mark.api
@pytest.mark.swagger
@pytest.mark.smoke
def test_swagger_endpoint_response_time(swagger_utils):
    """
    Test that the Swagger documentation endpoint responds within acceptable time.

    The test verifies:
    1. The endpoint responds within 5 seconds
    """
    timeout = 5  # seconds

    try:
        response = swagger_utils.get_swagger_page(timeout=timeout)
        assert_that(response.status_code, equal_to(200))
        assert_that(response.elapsed.total_seconds(), less_than(timeout))
    except requests.exceptions.Timeout:
        pytest.fail(f"Swagger endpoint did not respond within {timeout} seconds")


@pytest.mark.sanity
@pytest.mark.api
@pytest.mark.swagger
@pytest.mark.smoke
def test_openapi_json_endpoint(swagger_utils):
    """
    Test that the OpenAPI JSON endpoint returns valid JSON with expected metadata.

    The test verifies:
    1. The endpoint responds with HTTP 200 status code
    2. The response is valid JSON
    3. The info.title field equals "Codemie"
    4. The info.description field equals "Smart AI assistant 'CodeMie'"
    """
    response = swagger_utils.get_openapi_json()

    assert_that(response.status_code, equal_to(200))

    # Verify response is valid JSON
    openapi_spec = response.json()

    # Verify info.title
    assert_that(openapi_spec.get("info", {}).get("title"), equal_to("Codemie"))

    # Verify info.description
    assert_that(
        openapi_spec.get("info", {}).get("description"),
        equal_to("Smart AI assistant 'CodeMie'"),
    )
