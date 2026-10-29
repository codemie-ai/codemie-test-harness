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

"""API tests for Dynamic Customer Configuration.

Covers:
  SC-01 — Customer config CRUD lifecycle (AC-3, 13, 14, 16, 17, 20)
  SC-02 — Declarations endpoint structure and namespace (AC-4, 9, 12)
  SC-03 — Activity log records config change (AC-22)
  SC-06 — Non-admin write rejected with 403 (AC-21)

All tests are marked ``not_for_parallel_run`` when they mutate shared
deployment state (customer config overrides).
"""

from __future__ import annotations

import pytest
from hamcrest import (
    all_of,
    assert_that,
    equal_to,
    greater_than,
    has_entry,
    has_item,
    has_key,
    has_length,
    instance_of,
    is_not,
    none,
    only_contains,
)
from requests import HTTPError

from codemie_test_harness.tests import CredentialsManager
from codemie_test_harness.tests.test_data.customer_config_test_data import (
    get_disclaimer_settings_data,
)
from codemie_test_harness.tests.utils.base_utils import poll_until
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.customer_config_utils import CustomerConfigUtils
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver

# ── Constants ─────────────────────────────────────────────────────────────────

_COMPONENT_ID = "chatDisclaimer"
_ACTIVITY_DOMAIN = "customer_config"
_ACTIVITY_ENTITY_TYPE = "customer_config_setting"
_ACTIVITY_EVENT_UPDATED = "customer_config.setting.updated"
_ACTIVITY_EVENT_RESET = "customer_config.setting.reset"

_PREVIEW_ONLY_REASON = (
    "Non-admin test users (project and default) are only provisioned on "
    "the preview environment"
)

# ── Credentials for multi-role tests ─────────────────────────────────────────

_PROJECT_USER = {
    "username": CredentialsManager.get_parameter("AUTH_USERNAME_PROJECT"),
    "password": CredentialsManager.get_parameter("AUTH_PASSWORD_PROJECT"),
}

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def saved_disclaimer(customer_config_utils):
    """Write a test disclaimer override and reset it in teardown.

    Yields the settings dict that was saved.
    """
    settings_data = get_disclaimer_settings_data()
    customer_config_utils.save_setting(_COMPONENT_ID, settings_data.as_settings)
    yield settings_data
    try:
        customer_config_utils.reset_setting(_COMPONENT_ID)
    except Exception:
        pass


@pytest.fixture(scope="function")
def project_client():
    """CodeMieClient authenticated as the project-admin user (non-platform-admin)."""
    return get_client(
        username=_PROJECT_USER["username"],
        password=_PROJECT_USER["password"],
    )


@pytest.fixture(scope="function")
def project_customer_config_utils(project_client):
    """CustomerConfigUtils bound to the project-admin (non-platform-admin) client."""
    return CustomerConfigUtils(project_client)


@pytest.fixture(scope="function")
def ensure_disclaimer_reset(customer_config_utils):
    """Guarantee chatDisclaimer is reset to YAML default in teardown.

    Used alongside SC-01 so that cleanup happens even when an assertion fails
    mid-test.  The reset call in the test body verifies AC-16 behaviour; this
    fixture is the safety net only.
    """
    yield
    try:
        customer_config_utils.reset_setting(_COMPONENT_ID)
    except Exception:
        pass


# ── SC-01: CRUD lifecycle ─────────────────────────────────────────────────────


@pytest.mark.customer_configuration
@pytest.mark.api
def test_customer_config_crud_lifecycle(customer_config_utils, ensure_disclaimer_reset):
    """SC-01: Admin can write a disclaimer override, /v1/config reflects it,
    and resetting restores the YAML default.

    Covers AC-3, 13, 14, 16, 17, 20.
    """
    settings_data = get_disclaimer_settings_data()

    # ── Baseline: declarations show no override ──────────────────────────────
    chat_decl_before = customer_config_utils.get_declaration(_COMPONENT_ID)
    assert_that(
        chat_decl_before["overridden"],
        equal_to(False),
        "chatDisclaimer should not be overridden at test start",
    )

    # ── Write override ───────────────────────────────────────────────────────
    save_response = customer_config_utils.save_setting(
        _COMPONENT_ID, settings_data.as_settings
    )
    assert_that(
        save_response["component_id"],
        equal_to(_COMPONENT_ID),
        "save response must include component_id",
    )
    assert_that(
        save_response["settings"]["enabled"],
        equal_to(True),
        "saved settings must reflect enabled=True",
    )
    assert_that(
        save_response["settings"]["text"],
        equal_to(settings_data.text),
        "saved settings must reflect the disclaimer text",
    )

    # ── GET /v1/config reflects the write within the cache staleness window
    #    (AC-20) ──────────────────────────────────────────────────────────────
    # A read landing on a different pod than the one that served the write can
    # lag by up to the documented cache TTL in this shared, multi-instance
    # environment (see CustomerConfigService.get_config /
    # resolve_components/refresh_overrides); poll_until absorbs that bounded
    # lag without changing what is asserted.
    chat_component = poll_until(
        fetch=lambda: customer_config_utils.get_config_component(_COMPONENT_ID),
        predicate=lambda component: component is not None
        and component["settings"]["text"] == settings_data.text,
    )
    assert_that(
        chat_component,
        is_not(none()),
        "chatDisclaimer must appear in /v1/config after being enabled",
    )
    assert_that(
        chat_component["settings"]["enabled"],
        equal_to(True),
        "/v1/config must show the override value (AC-20)",
    )
    assert_that(
        chat_component["settings"]["text"],
        equal_to(settings_data.text),
        "/v1/config must reflect the saved disclaimer text",
    )

    # ── AC-3: existing /v1/config fields unchanged ────────────────────────────
    config_ids = {c["id"] for c in customer_config_utils.get_config()}
    assert_that(
        config_ids,
        has_item("videoPortal"),
        "pre-existing config components must remain in /v1/config (AC-3)",
    )

    # ── Declarations show overridden=True ─────────────────────────────────────
    chat_decl_after = customer_config_utils.get_declaration(_COMPONENT_ID)
    assert_that(
        chat_decl_after["overridden"],
        equal_to(True),
        "declaration must show overridden=True after saving",
    )
    assert_that(
        chat_decl_after["value"]["enabled"],
        equal_to(True),
        "declaration value must reflect the saved enabled flag",
    )
    assert_that(
        chat_decl_after["value"]["text"],
        equal_to(settings_data.text),
        "declaration value must reflect the saved text",
    )

    # ── Reset to YAML default (AC-16) ─────────────────────────────────────────
    customer_config_utils.reset_setting(_COMPONENT_ID)

    # ── Declarations show overridden=False and YAML default values ────────────
    chat_decl_reset = customer_config_utils.get_declaration(_COMPONENT_ID)
    assert_that(
        chat_decl_reset["overridden"],
        equal_to(False),
        "declaration must show overridden=False after reset",
    )
    assert_that(
        chat_decl_reset["value"]["enabled"],
        equal_to(False),
        "declaration value must be the YAML default (enabled=False) after reset",
    )


# ── SC-02: Declarations structure and namespace ───────────────────────────────


@pytest.mark.customer_configuration
@pytest.mark.api
def test_declarations_endpoint_structure_and_namespace(customer_config_utils):
    """SC-02: GET /v1/config/declarations returns well-structured entries with
    the expected field metadata; YAML-only config keys are absent (AC-4, 9, 12).
    """
    declarations = customer_config_utils.list_declarations()

    # Response is a non-empty list
    assert_that(
        declarations,
        has_length(greater_than(0)),
        "declarations list must be non-empty",
    )

    # chatDisclaimer is registered
    component_ids = [d["component_id"] for d in declarations]
    assert_that(
        component_ids,
        has_item(_COMPONENT_ID),
        "chatDisclaimer must be in the declarations registry",
    )

    # Each declaration has required top-level fields and a list-typed 'fields' key
    required_fields_matcher = all_of(
        has_key("component_id"),
        has_key("label"),
        has_key("description"),
        has_key("overridden"),
        has_key("value"),
        has_entry("fields", instance_of(list)),
    )
    assert_that(
        declarations,
        only_contains(required_fields_matcher),
        "every declaration must carry the required top-level structure",
    )

    # chatDisclaimer field metadata: switch (enabled) and textarea (text)
    chat_decl = next(d for d in declarations if d["component_id"] == _COMPONENT_ID)
    field_names = {f["name"] for f in chat_decl["fields"]}
    assert_that(
        field_names,
        has_item("enabled"),
        "chatDisclaimer must declare an 'enabled' field",
    )
    assert_that(
        field_names,
        has_item("text"),
        "chatDisclaimer must declare a 'text' field",
    )

    # Field type and constraints
    text_field = next(f for f in chat_decl["fields"] if f["name"] == "text")
    assert_that(
        text_field["type"],
        equal_to("textarea"),
        "text field must be of type 'textarea' (AC-9)",
    )
    assert_that(
        text_field["max_length"],
        equal_to(1000),
        "text field must declare a max_length constraint (AC-9)",
    )
    assert_that(
        text_field["markup"],
        equal_to("markdown"),
        "text field must declare markup='markdown' (AC-9)",
    )

    enabled_field = next(f for f in chat_decl["fields"] if f["name"] == "enabled")
    assert_that(
        enabled_field["type"],
        equal_to("switch"),
        "enabled field must be of type 'switch'",
    )

    # AC-12: YAML-only config component IDs must NOT appear in declarations.
    # features:webSearch is deliberately excluded from this list:
    # migrated it to the dynamic-configuration registry, so it is now expected
    # to appear in declarations rather than being YAML-only.
    yaml_only_ids = {
        "videoPortal",
        "skills",
        "idpProvider",
        "mcpAuthOrigin",
    }
    assert_that(
        yaml_only_ids.intersection(component_ids),
        equal_to(set()),
        "YAML-only component IDs must not appear in declarations (AC-12)",
    )


# ── SC-03: Activity log records config change ─────────────────────────────────


@pytest.mark.customer_configuration
@pytest.mark.api
def test_activity_log_records_config_change(client, saved_disclaimer):
    """SC-03: Writing a disclaimer override emits an activity log entry with
    the correct domain, actor, and key attributes (AC-22).
    """
    # Query activity events for the customer_config domain
    events_response = client.activity_events.list_events(
        domain=[_ACTIVITY_DOMAIN],
        entity_type=[_ACTIVITY_ENTITY_TYPE],
        event_type=[_ACTIVITY_EVENT_UPDATED],
        sort_dir="desc",
        limit=10,
    )

    events = events_response.data
    assert_that(
        len(events),
        greater_than(0),
        f"at least one {_ACTIVITY_EVENT_UPDATED} event must be present (AC-22)",
    )

    # The most recent update event corresponds to our saved disclaimer
    latest_event = events[0]
    assert_that(
        latest_event.domain,
        equal_to(_ACTIVITY_DOMAIN),
        "activity event domain must be 'customer_config'",
    )
    assert_that(
        latest_event.event_type,
        equal_to(_ACTIVITY_EVENT_UPDATED),
        "activity event type must be 'customer_config.setting.updated'",
    )
    assert_that(
        latest_event.entity_type,
        equal_to(_ACTIVITY_ENTITY_TYPE),
        "activity event entity_type must be 'customer_config_setting'",
    )
    assert_that(
        latest_event.entity_id,
        equal_to(_COMPONENT_ID),
        "activity event entity_id must be 'chatDisclaimer'",
    )
    assert_that(
        latest_event.actor_id,
        is_not(none()),
        "activity event must record the actor_id",
    )
    assert_that(
        latest_event.created_at,
        is_not(none()),
        "activity event must have a created_at timestamp",
    )

    # Attributes contain the key with CUSTOMER_CONFIG__ prefix (AC-4)
    attributes = latest_event.attributes or {}
    assert_that(
        attributes,
        has_key("key"),
        "activity event attributes must contain 'key'",
    )
    assert_that(
        attributes["key"].startswith("CUSTOMER_CONFIG__"),
        equal_to(True),
        "activity event key must start with 'CUSTOMER_CONFIG__' prefix (AC-4)",
    )
    assert_that(
        attributes,
        has_key("new_value"),
        "activity event attributes must contain 'new_value'",
    )


# ── SC-06: Non-admin write rejected with 403 ─────────────────────────────────


@pytest.mark.customer_configuration
@pytest.mark.skipif(
    not EnvironmentResolver.is_preview(),
    reason=_PREVIEW_ONLY_REASON,
)
@pytest.mark.api
def test_non_admin_write_rejected_with_403(
    project_customer_config_utils, customer_config_utils
):
    """SC-06: A non-platform-admin user attempting a settings override receives
    HTTP 403 and the existing config value is unchanged (AC-21).
    """
    settings_data = get_disclaimer_settings_data()

    # Read baseline value from declarations before the rejected attempt
    chat_decl_before = customer_config_utils.get_declaration(_COMPONENT_ID)
    overridden_before = chat_decl_before["overridden"]

    # Non-admin attempt must raise HTTPError with status 403
    with pytest.raises(HTTPError) as exc_info:
        project_customer_config_utils.save_setting(
            _COMPONENT_ID, settings_data.as_settings
        )
    assert_that(
        exc_info.value.response.status_code,
        equal_to(403),
        "project-admin user must receive HTTP 403 on save_setting",
    )

    # Config value must be unchanged
    chat_decl_after = customer_config_utils.get_declaration(_COMPONENT_ID)
    assert_that(
        chat_decl_after["overridden"],
        equal_to(overridden_before),
        "config override state must be unchanged after rejected write (AC-21)",
    )
