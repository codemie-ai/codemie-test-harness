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
from hamcrest import (
    assert_that,
    is_,
    is_not,
    equal_to,
    has_key,
    all_of,
)

from codemie_test_harness.tests.test_data.provider_toolkit_test_data import (
    DEFAULT_GRAPHDB_PASSWORD_VALUE,
    DEFAULT_GRAPHDB_USERNAME_VALUE,
    default_value_field_test_data,
    provider_payload_with_default_value,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name, assert_response

nonexistent_id = "nonexistent-provider-id-12345"

# =============================================================================
# GET /v1/providers - List all providers
# =============================================================================


@pytest.mark.provider
@pytest.mark.api
def test_get_providers_endpoint(providers_utils):
    response = providers_utils.send_get_request_to_providers_endpoint()

    assert_that(response.status_code, equal_to(200))

    response_data = response.json()

    # Validate response structure
    assert_that(isinstance(response_data, list), is_(True))
    for provider in response_data:
        assert_that(
            provider,
            all_of(has_key("provided_toolkits"), has_key("service_location_url")),
        )


# =============================================================================
# POST /v1/providers - Create new provider
# =============================================================================


@pytest.mark.provider
@pytest.mark.api
def test_post_providers_endpoint(providers_utils):
    request_json = providers_utils.provider_request_json()
    # Ensure unique provider name to avoid conflicts
    provider_name = get_random_name()
    request_json["name"] = provider_name

    create_response = providers_utils.send_post_request_to_providers_endpoint(
        request_json
    )

    assert_that(create_response.status_code, equal_to(200))

    # get provider to verify it was created
    get_response = providers_utils.send_get_request_to_providers_endpoint()

    providers = get_response.json()
    created_provider = next((p for p in providers if p["name"] == provider_name), None)

    assert_that(
        created_provider is not None,
        is_(True),
        "Created provider should be in the list",
    )


@pytest.mark.provider
@pytest.mark.api
def test_post_providers_endpoint_validation_error(providers_utils):
    """Test POST /v1/providers with invalid provided_toolkits node"""
    request_json = providers_utils.provider_request_json()
    request_json["provided_toolkits"] = "invalid_value"

    response = providers_utils.send_post_request_to_providers_endpoint(request_json)

    assert_response(response, 422, "Input should be a valid list")


@pytest.mark.provider
@pytest.mark.api
def test_post_providers_endpoint_with_existing_name(providers_utils):
    provider_id = providers_utils.create_provider()

    provider = providers_utils.get_provider_by_id(provider_id).json()

    existing_name = provider["name"]
    request_json = providers_utils.provider_request_json()
    request_json["name"] = existing_name

    create_response = providers_utils.send_post_request_to_providers_endpoint(
        request_json
    )

    assert_that(create_response.status_code, equal_to(409))
    assert_that(
        create_response.json()["error"]["details"],
        equal_to(f"A provider with the name [{existing_name}] already exists."),
    )


# =============================================================================
# GET /v1/providers/datasource_schemas - Get datasource schemas
# =============================================================================


@pytest.mark.provider
@pytest.mark.api
def test_get_providers_datasource_schema_endpoint(providers_utils):
    response = providers_utils.send_get_request_datasource_schemas_endpoint()

    assert_that(response.status_code, equal_to(200))

    response_data = response.json()

    # Validate response structure
    assert_that(isinstance(response_data, list), is_(True))
    for provider in response_data:
        assert_that(
            provider,
            all_of(
                has_key("id"),
                has_key("provider_name"),
                has_key("name"),
                has_key("base_schema"),
                has_key("create_schema"),
            ),
        )


# =============================================================================
# GET /v1/providers/{provider_id} - Get specific provider
# =============================================================================


@pytest.mark.provider
@pytest.mark.api
def test_get_provider_by_id_endpoint(providers_utils):
    provider_id = providers_utils.create_provider()

    provider_response = providers_utils.get_provider_by_id(provider_id)

    assert_that(provider_response.status_code, equal_to(200))
    assert_that(provider_response.json()["id"], equal_to(provider_id))


@pytest.mark.provider
@pytest.mark.api
def test_get_nonexistent_provider(providers_utils):
    """Test error handling when requesting nonexistent provider."""
    response = providers_utils.get_provider_by_id(nonexistent_id)

    assert_that(response.status_code, equal_to(404))

    assert_that(
        response.json()["error"]["details"],
        equal_to(
            f"The provider with ID [{nonexistent_id}] could not be found in the system."
        ),
    )


# =============================================================================
# PUT /v1/providers/{provider_id} - Update specific provider
# =============================================================================


@pytest.mark.provider
@pytest.mark.api
def test_put_provider_endpoint(providers_utils):
    provider_id = providers_utils.create_provider()
    provider = providers_utils.get_provider_by_id(provider_id).json()

    request_json = providers_utils.provider_request_json()
    toolkits = provider["provided_toolkits"]
    toolkits[0]["name"] = "Updated toolkit name"
    toolkits[0]["description"] = "Updated toolkit description"
    request_json["provided_toolkits"] = toolkits
    request_json["name"] = f"{provider['name']} - updated"
    update_response = providers_utils.update_provider(provider_id, request_json)

    assert_that(update_response.status_code, equal_to(200))
    updated_toolkit = update_response.json()["provided_toolkits"][0]
    assert_that(updated_toolkit["name"], equal_to("Updated toolkit name"))
    assert_that(updated_toolkit["description"], equal_to("Updated toolkit description"))


@pytest.mark.provider
@pytest.mark.api
def test_put_nonexistent_provider(providers_utils):
    response = providers_utils.update_provider(nonexistent_id, {})

    assert_that(response.status_code, equal_to(404))
    assert_that(
        response.json()["error"]["details"],
        equal_to(
            f"The provider with ID [{nonexistent_id}] could not be found in the system."
        ),
    )


# =============================================================================
# DELETE /v1/providers/{provider_id} - Delete specific provider
# =============================================================================


@pytest.mark.provider
@pytest.mark.api
def test_delete_provider_endpoint(providers_utils):
    provider_id = providers_utils.create_provider()
    delete_response = providers_utils.send_delete_provider_request(provider_id)

    assert_that(delete_response.status_code, equal_to(204))

    response = providers_utils.get_provider_by_id(provider_id)

    assert_that(response.status_code, equal_to(404))

    assert_that(
        response.json()["error"]["details"],
        equal_to(
            f"The provider with ID [{provider_id}] could not be found in the system."
        ),
    )


@pytest.mark.provider
@pytest.mark.api
def test_delete_nonexistent_provider(providers_utils):
    """Test error handling when requesting nonexistent provider."""
    response = providers_utils.send_delete_provider_request(nonexistent_id)

    assert_that(response.status_code, equal_to(404))

    assert_that(
        response.json()["error"]["details"],
        equal_to(
            f"The provider with ID [{nonexistent_id}] could not be found in the system."
        ),
    )


# =============================================================================
# default_value on provider datasource parameters
# =============================================================================


@pytest.mark.provider
@pytest.mark.api
def test_update_provider_schema_field_default_value(providers_utils):
    """Updating a provider's parameter `default_value` via PUT is reflected in
    the next GET /v1/providers/datasource_schemas fetch."""
    provider_id = providers_utils.create_provider()
    provider = providers_utils.get_provider_by_id(provider_id).json()

    request_json = providers_utils.provider_request_json()
    request_json["name"] = provider["name"]
    toolkits = provider["provided_toolkits"]
    toolkits[0]["toolkit_config"]["parameters"]["graphdb_username"]["default_value"] = (
        DEFAULT_GRAPHDB_USERNAME_VALUE
    )
    request_json["provided_toolkits"] = toolkits

    update_response = providers_utils.update_provider(provider_id, request_json)
    assert_that(update_response.status_code, equal_to(200))

    schemas = providers_utils.send_get_request_datasource_schemas_endpoint().json()
    schema_entry = next(
        (s for s in schemas if s["provider_name"] == provider["name"]), None
    )
    assert_that(
        schema_entry,
        is_not(None),
        f"Provider [{provider['name']}] not found in datasource_schemas",
    )
    graphdb_username_schema_param = next(
        (
            p
            for p in schema_entry["base_schema"]["parameters"]
            if p["name"] == "graphdb_username"
        ),
        None,
    )
    assert_that(
        graphdb_username_schema_param,
        is_not(None),
        "'graphdb_username' parameter not found in provider's base_schema.parameters",
    )
    assert_that(
        graphdb_username_schema_param.get("default_value"),
        equal_to(DEFAULT_GRAPHDB_USERNAME_VALUE),
    )


@pytest.mark.provider
@pytest.mark.api
@pytest.mark.parametrize(
    "parameter_name, tool_name, default_value", default_value_field_test_data
)
def test_provider_schema_fields_default_values(
    providers_utils, parameter_name, tool_name, default_value
):
    """A provider's schema parameter `default_value` round-trips
    through GET /v1/providers/{id} and GET /v1/providers/datasource_schemas for
    every default_value-capable provider-level config parameter the AICE
    combined provider exposes (repositories, graphdb_username, graphdb_password,
    graphdb_tenant_url). create_datasource's own arguments
    (name, description) are required with no default_value concept, so they
    are not covered here — see provider_toolkit_test_data.default_value_field_test_data.
    """
    base_payload = providers_utils.provider_request_json()
    base_payload["name"] = get_random_name()
    request_json = provider_payload_with_default_value(
        base_payload, parameter_name, default_value, tool_name=tool_name
    )

    create_response = providers_utils.send_post_request_to_providers_endpoint(
        request_json
    )
    assert_that(create_response.status_code, equal_to(200))
    provider_id = create_response.json()["id"]

    provider = providers_utils.get_provider_by_id(provider_id).json()
    toolkit = provider["provided_toolkits"][0]
    if tool_name is None:
        created_param = toolkit["toolkit_config"]["parameters"][parameter_name]
    else:
        tool = next(
            (t for t in toolkit["provided_tools"] if t["name"] == tool_name), None
        )
        assert_that(
            tool, is_not(None), f"Tool [{tool_name}] not found in provided_tools"
        )
        created_param = tool["args_schema"][parameter_name]
    if default_value is None:
        assert_that(
            created_param.get("default_value"),
            equal_to(None),
            f"default_value should be None on the created provider's '{parameter_name}' parameter",
        )
    else:
        assert_that(
            created_param.get("default_value"),
            equal_to(default_value),
            f"default_value on the created provider's '{parameter_name}' parameter",
        )

    schemas = providers_utils.send_get_request_datasource_schemas_endpoint().json()
    schema_entry = next(
        (s for s in schemas if s["provider_name"] == request_json["name"]), None
    )
    assert_that(
        schema_entry,
        is_not(None),
        f"Provider [{request_json['name']}] not found in datasource_schemas",
    )
    schema_section = (
        schema_entry["base_schema"]
        if tool_name is None
        else schema_entry["create_schema"]
    )
    schema_param = next(
        (p for p in schema_section["parameters"] if p["name"] == parameter_name),
        None,
    )
    assert_that(
        schema_param,
        is_not(None),
        f"'{parameter_name}' parameter not found in provider's schema parameters",
    )
    if default_value is None:
        assert_that(
            schema_param.get("default_value"),
            equal_to(None),
            f"default_value should be None on the provider's '{parameter_name}' schema parameter",
        )
    else:
        assert_that(
            schema_param.get("default_value"),
            equal_to(default_value),
            f"default_value on the provider's '{parameter_name}' schema parameter",
        )


@pytest.mark.provider
@pytest.mark.api
def test_provider_graphdb_password_default_value_is_not_masked(providers_utils):
    """Empirically confirms that a Secret-typed
    provider parameter's `default_value` is returned in PLAINTEXT (not masked)
    everywhere in the provider API surface: the POST create response, GET
    /v1/providers/{id}, and GET /v1/providers/datasource_schemas. This is
    distinct from the per-datasource secret VALUE masking ('**********') shown
    in the UI's edit form and Details view, which applies to an actual
    configured datasource secret, not to a provider schema's configured
    default_value.
    """
    base_payload = providers_utils.provider_request_json()
    base_payload["name"] = get_random_name()
    request_json = provider_payload_with_default_value(
        base_payload, "graphdb_password", DEFAULT_GRAPHDB_PASSWORD_VALUE
    )

    create_response = providers_utils.send_post_request_to_providers_endpoint(
        request_json
    )
    assert_that(create_response.status_code, equal_to(200))
    created_graphdb_password_param = create_response.json()["provided_toolkits"][0][
        "toolkit_config"
    ]["parameters"]["graphdb_password"]
    assert_that(
        created_graphdb_password_param.get("default_value"),
        equal_to(DEFAULT_GRAPHDB_PASSWORD_VALUE),
        "graphdb_password default_value should be returned in plaintext in the POST response, not masked",
    )
    provider_id = create_response.json()["id"]

    provider = providers_utils.get_provider_by_id(provider_id).json()
    get_graphdb_password_param = provider["provided_toolkits"][0]["toolkit_config"][
        "parameters"
    ]["graphdb_password"]
    assert_that(
        get_graphdb_password_param.get("default_value"),
        equal_to(DEFAULT_GRAPHDB_PASSWORD_VALUE),
        "graphdb_password default_value should be returned in plaintext in the GET-by-id response, not masked",
    )

    schemas = providers_utils.send_get_request_datasource_schemas_endpoint().json()
    schema_entry = next(
        (s for s in schemas if s["provider_name"] == request_json["name"]), None
    )
    assert_that(
        schema_entry,
        is_not(None),
        f"Provider [{request_json['name']}] not found in datasource_schemas",
    )
    schema_graphdb_password_param = next(
        (
            p
            for p in schema_entry["base_schema"]["parameters"]
            if p["name"] == "graphdb_password"
        ),
        None,
    )
    assert_that(
        schema_graphdb_password_param,
        is_not(None),
        "'graphdb_password' parameter not found in provider's base_schema.parameters",
    )
    assert_that(
        schema_graphdb_password_param.get("default_value"),
        equal_to(DEFAULT_GRAPHDB_PASSWORD_VALUE),
        "graphdb_password default_value should be returned in plaintext in datasource_schemas, not masked",
    )
