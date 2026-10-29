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

"""API tests for the shared component-resolution precedence.

Covers:
  AC-3  — Overridden field wins over the YAML value for the pilot component
  AC-4  — No override present resolves to the YAML value for the pilot component
  AC-5  — Resetting the pilot component removes its override row and returns
          resolution to YAML
  AC-2  — A declared field absent from a stored override row keeps coming from
          YAML
  AC-6  — Writing an override for a runtime-computed component is rejected
"""

from __future__ import annotations

import json

import pytest
from hamcrest import assert_that, equal_to, is_not, none
from requests import HTTPError

from codemie_test_harness.tests.enums.tools import ResearchToolName, Toolkit
from codemie_test_harness.tests.test_data.customer_config_test_data import (
    get_disclaimer_dynamic_config_key,
    get_disclaimer_partial_override_text,
    get_web_search_settings_data,
)
from codemie_test_harness.tests.utils.base_utils import (
    assert_tool_triggered,
    poll_until,
)

# ── Constants ─────────────────────────────────────────────────────────────────

_WEB_SEARCH_COMPONENT_ID = "features:webSearch"
_DISCLAIMER_COMPONENT_ID = "chatDisclaimer"
_RUNTIME_COMPONENT_ID = "idpProvider"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def web_search_yaml_default(customer_config_utils):
    """Guarantee no override row exists for features:webSearch and capture the
    resulting YAML-resolved value of its 'enabled' field.

    Resetting first (idempotent) removes any leftover override, so the
    declaration read immediately afterwards reflects the YAML default
    verbatim. Restores the reset state again in teardown.
    """
    customer_config_utils.reset_setting(_WEB_SEARCH_COMPONENT_ID)
    web_search_decl = customer_config_utils.get_declaration(_WEB_SEARCH_COMPONENT_ID)
    yield web_search_decl["value"]["enabled"]
    try:
        customer_config_utils.reset_setting(_WEB_SEARCH_COMPONENT_ID)
    except Exception:
        pass


@pytest.fixture(scope="function")
def reset_disclaimer_before_and_after(customer_config_utils):
    """Guarantee chatDisclaimer has no override row before and after the test.

    ``reset_setting`` deletes the same underlying dynamic-config row regardless
    of whether it was written via ``save_setting`` or directly via
    ``customer_config_utils.write_raw_override`` (both target the same
    ``CUSTOMER_CONFIG__CHAT_DISCLAIMER`` key), so this fixture also cleans up
    rows created by the raw write TC-005 uses.
    """
    customer_config_utils.reset_setting(_DISCLAIMER_COMPONENT_ID)
    yield
    try:
        customer_config_utils.reset_setting(_DISCLAIMER_COMPONENT_ID)
    except Exception:
        pass


@pytest.mark.customer_configuration
@pytest.mark.api
def test_override_field_wins_over_yaml_value(
    customer_config_utils, web_search_yaml_default
):
    """
    An override on features:webSearch wins over the YAML value — verified via
    save_setting, GET /v1/config, and list_declarations() (AC-3).

    GET /v1/config (customer_config_service.resolve_components) only lists
    components whose *resolved* 'enabled' is True — it filters out disabled
    components entirely rather than listing them with enabled=False. So the
    observable effect of overriding features:webSearch (a single-field,
    switch-only component) to enabled=False is that it disappears from
    /v1/config, not that it appears there with enabled=False.
    """
    settings = get_web_search_settings_data(enabled=False).as_settings

    save_response = customer_config_utils.save_setting(
        _WEB_SEARCH_COMPONENT_ID, settings
    )
    assert_that(
        save_response["settings"]["enabled"],
        equal_to(False),
        "save_setting response must reflect the overridden enabled=False value",
    )

    web_search_component = poll_until(
        fetch=lambda: customer_config_utils.get_config_component(
            _WEB_SEARCH_COMPONENT_ID
        ),
        predicate=lambda component: component is None,
    )
    assert_that(
        web_search_component,
        none(),
        "features:webSearch must be excluded from /v1/config once the override "
        "sets enabled=False — GET /v1/config only lists components whose "
        "resolved 'enabled' is True, so the override (not the YAML default) "
        "decides inclusion (AC-3)",
    )

    web_search_decl = customer_config_utils.get_declaration(_WEB_SEARCH_COMPONENT_ID)
    assert_that(
        web_search_decl["overridden"],
        equal_to(True),
        "declaration must show overridden=True after saving an override",
    )
    assert_that(
        web_search_decl["value"]["enabled"],
        equal_to(False),
        "declaration value must reflect the overridden enabled=False value (AC-3)",
    )


@pytest.mark.customer_configuration
@pytest.mark.api
def test_no_override_resolves_to_yaml_value(
    customer_config_utils, web_search_yaml_default
):
    """
    With no stored override row, resolution falls through to the YAML value,
    and resetting an already-clean component stays idempotent (AC-4).
    """
    yaml_default_enabled = web_search_yaml_default

    # Idempotent: resetting again with no override row present must not raise.
    customer_config_utils.reset_setting(_WEB_SEARCH_COMPONENT_ID)

    web_search_decl = customer_config_utils.get_declaration(_WEB_SEARCH_COMPONENT_ID)
    assert_that(
        web_search_decl["overridden"],
        equal_to(False),
        "declaration must show overridden=False when no override row exists (AC-4)",
    )
    assert_that(
        web_search_decl["value"]["enabled"],
        equal_to(yaml_default_enabled),
        "declaration value must match the YAML default when no override row exists (AC-4)",
    )

    web_search_component = poll_until(
        fetch=lambda: customer_config_utils.get_config_component(
            _WEB_SEARCH_COMPONENT_ID
        ),
        predicate=lambda component: component is not None
        and component["settings"]["enabled"] == yaml_default_enabled,
    )
    assert_that(
        web_search_component,
        is_not(none()),
        "features:webSearch must appear in /v1/config",
    )
    assert_that(
        web_search_component["settings"]["enabled"],
        equal_to(yaml_default_enabled),
        "/v1/config must match the YAML default when no override row exists (AC-4)",
    )


@pytest.mark.customer_configuration
@pytest.mark.api
def test_reset_removes_override_and_returns_to_yaml(
    customer_config_utils, web_search_yaml_default
):
    """
    Resetting an active override removes its row, and resolution returns to
    the YAML value immediately, without a backend restart (AC-5).
    """
    yaml_default_enabled = web_search_yaml_default
    settings = get_web_search_settings_data(enabled=False).as_settings

    save_response = customer_config_utils.save_setting(
        _WEB_SEARCH_COMPONENT_ID, settings
    )
    assert_that(
        save_response["settings"]["enabled"],
        equal_to(False),
        "override must be applied before reset",
    )
    web_search_decl_overridden = customer_config_utils.get_declaration(
        _WEB_SEARCH_COMPONENT_ID
    )
    assert_that(
        web_search_decl_overridden["overridden"],
        equal_to(True),
        "declaration must show overridden=True before reset",
    )

    customer_config_utils.reset_setting(_WEB_SEARCH_COMPONENT_ID)

    web_search_decl_reset = customer_config_utils.get_declaration(
        _WEB_SEARCH_COMPONENT_ID
    )
    assert_that(
        web_search_decl_reset["overridden"],
        equal_to(False),
        "declaration must show overridden=False immediately after reset (AC-5)",
    )
    assert_that(
        web_search_decl_reset["value"]["enabled"],
        equal_to(yaml_default_enabled),
        "declaration value must match the YAML default immediately after reset (AC-5)",
    )


@pytest.mark.customer_configuration
@pytest.mark.api
def test_field_absent_from_override_keeps_yaml_value(
    customer_config_utils, reset_disclaimer_before_and_after
):
    """
    A declared field the stored override omits keeps resolving from YAML,
    while the field supplied in the override reflects the override (AC-2).

    ``PUT /v1/config/declarations/chatDisclaimer`` (``save_setting``) rejects
    any payload missing a declared field with HTTP 400 ("Missing
    configuration field") — every write through that endpoint must carry both
    'enabled' and 'text'. A stored override row that is missing a
    currently-declared field can therefore only be produced by writing the
    underlying dynamic-config key directly, via the super-admin
    ``/v1/dynamic-config/{key}`` endpoint, which stores the raw value without
    that per-field completeness check.
    """
    chat_decl_before = customer_config_utils.get_declaration(_DISCLAIMER_COMPONENT_ID)
    yaml_default_enabled = chat_decl_before["value"]["enabled"]

    override_text = get_disclaimer_partial_override_text()
    override_key = get_disclaimer_dynamic_config_key()
    customer_config_utils.write_raw_override(
        override_key, json.dumps({"text": override_text})
    )

    chat_decl_after = customer_config_utils.get_declaration(_DISCLAIMER_COMPONENT_ID)
    assert_that(
        chat_decl_after["value"]["text"],
        equal_to(override_text),
        "the supplied 'text' field must reflect the override (AC-2)",
    )
    assert_that(
        chat_decl_after["value"]["enabled"],
        equal_to(yaml_default_enabled),
        "the omitted 'enabled' field must keep resolving from YAML, not be "
        "defaulted to null/false by omission (AC-2)",
    )


@pytest.mark.customer_configuration
@pytest.mark.api
def test_runtime_component_override_write_rejected(customer_config_utils):
    """
    Writing an override for a runtime-computed component (never declared) is
    rejected with HTTP 404 (AC-6).
    """
    with pytest.raises(HTTPError) as exc_info:
        customer_config_utils.save_setting(_RUNTIME_COMPONENT_ID, {"enabled": True})
    assert_that(
        exc_info.value.response.status_code,
        equal_to(404),
        "save_setting for a runtime-computed component id must be rejected as "
        "not declared (AC-6)",
    )


@pytest.mark.customer_configuration
@pytest.mark.research
@pytest.mark.api
def test_explicit_research_toolkit_ignores_disabled_web_search_flag(
    assistant, assistant_utils, web_search_disabled
):
    """
    Documents a known gap in the pilot migration (AC-11): the
    ``features:webSearch`` flag only gates the *dynamic* auto-injection path
    in ``toolkit_service.py``'s ``augment_toolkits_with_feature_flags``
    (``enable_web_search = request.enable_web_search is True and
    customer_config.is_feature_enabled("webSearch")``, itself gated by
    ``not has_toolkit(ToolSet.RESEARCH)``). An assistant with the Research
    toolkit *explicitly* configured never reaches that flag check at all, so
    disabling ``features:webSearch`` has no effect on it — the google-search
    tool remains triggerable.

    This is regression coverage for the documented gap, not an assertion that
    this is the intended long-term behaviour — AC-11 only requires consistent
    behaviour for the default/dynamic injection path, which this asymmetry
    falls outside of.
    """
    research_assistant = assistant(Toolkit.RESEARCH, ResearchToolName.GOOGLE_SEARCH)

    _, triggered_tools = assistant_utils.ask_assistant(
        research_assistant,
        "Run Google Search Tool and query: AI trends. "
        "Represent in JSON format with title and link",
        minimal_response=False,
    )

    assert_tool_triggered(ResearchToolName.GOOGLE_SEARCH, triggered_tools)
