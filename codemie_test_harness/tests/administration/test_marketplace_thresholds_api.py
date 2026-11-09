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

"""API tests for the marketplace active-usage thresholds customer config.

Covers the ``marketplaceThresholds`` declaration served by
``/v1/config/declarations``: the five fields and their deployment defaults,
the save / reset lifecycle, and value validation.

Validation follows the shipped backend: any positive integer is accepted
(pattern ``^[1-9][0-9]*$``, no upper bound); non-numeric, negative and zero
values are rejected.

``marketplaceThresholds`` is a customer-wide singleton, so these tests cannot
run concurrently with each other without racing on the same row. They carry
``xdist_group(name="marketplace_thresholds")`` instead of excluding them from
parallel runs: pytest-xdist pins the whole group to one worker (serial among
themselves) while every other worker still runs the rest of the suite. This
only takes effect with ``--dist=loadgroup`` (see strategy.md); without it the
group is a no-op and these tests go back to being scattered across workers.
"""

from __future__ import annotations

import pytest
from hamcrest import assert_that, contains_string, equal_to
from requests import HTTPError

from codemie_test_harness.tests.test_data.marketplace_thresholds_test_data import (
    ACCEPTED_THRESHOLD_VALUES,
    DEFAULT_THRESHOLDS,
    MALFORMED_PAYLOADS,
    MARKETPLACE_THRESHOLDS_COMPONENT_ID,
    POSITIVE_INTEGER_MESSAGE,
    REJECTED_THRESHOLD_VALUES,
    THRESHOLD_FIELD_NAMES,
    build_malformed_payload,
    get_marketplace_thresholds_data,
)

_COMPONENT_ID = MARKETPLACE_THRESHOLDS_COMPONENT_ID


@pytest.mark.xdist_group(name="marketplace_thresholds")
@pytest.mark.customer_configuration
@pytest.mark.api
def test_marketplace_thresholds_declaration_exposes_defaults_without_override(
    customer_config_utils, clean_marketplace_thresholds
):
    """Declaration lists exactly five fields at hot 50, warm 7, cold 3, grace 60,
    archive 30 with overridden=False."""
    declaration = customer_config_utils.get_declaration(_COMPONENT_ID)

    field_names = {f["name"] for f in declaration["fields"]}
    assert_that(
        field_names,
        equal_to(THRESHOLD_FIELD_NAMES),
        "marketplaceThresholds must declare exactly the five threshold fields",
    )
    assert_that(
        declaration["value"],
        equal_to(DEFAULT_THRESHOLDS),
        "with no override the declaration must resolve to the five deployment defaults",
    )
    assert_that(
        declaration["overridden"],
        equal_to(False),
        "overridden must be False when no override row exists",
    )


@pytest.mark.xdist_group(name="marketplace_thresholds")
@pytest.mark.customer_configuration
@pytest.mark.api
def test_marketplace_thresholds_save_then_reset_restores_defaults(
    customer_config_utils, clean_marketplace_thresholds
):
    """Saved override is returned with overridden=True; reset restores defaults."""
    settings = get_marketplace_thresholds_data().as_settings

    save_response = customer_config_utils.save_setting(_COMPONENT_ID, settings)
    assert_that(
        save_response["component_id"],
        equal_to(_COMPONENT_ID),
        "save response must include component_id",
    )
    assert_that(
        save_response["settings"],
        equal_to(settings),
        "save response must echo the persisted settings",
    )

    declaration_after_save = customer_config_utils.get_declaration(_COMPONENT_ID)
    assert_that(
        declaration_after_save["value"],
        equal_to(settings),
        "declaration value must equal the saved fields",
    )
    assert_that(
        declaration_after_save["overridden"],
        equal_to(True),
        "overridden must be True after saving",
    )

    customer_config_utils.reset_setting(_COMPONENT_ID)

    declaration_after_reset = customer_config_utils.get_declaration(_COMPONENT_ID)
    assert_that(
        declaration_after_reset["value"],
        equal_to(DEFAULT_THRESHOLDS),
        "declaration value must return to the five deployment defaults after reset",
    )
    assert_that(
        declaration_after_reset["overridden"],
        equal_to(False),
        "overridden must be False after reset (defaults are not copied to the DB)",
    )


@pytest.mark.xdist_group(name="marketplace_thresholds")
@pytest.mark.customer_configuration
@pytest.mark.api
@pytest.mark.parametrize("mutation, expected_message", MALFORMED_PAYLOADS)
def test_marketplace_thresholds_save_rejects_incomplete_or_undeclared_payload(
    customer_config_utils, clean_marketplace_thresholds, mutation, expected_message
):
    """A payload missing a declared field or carrying an undeclared one gets 400."""
    payload = build_malformed_payload(
        get_marketplace_thresholds_data().as_settings, mutation
    )

    with pytest.raises(HTTPError) as exc_info:
        customer_config_utils.save_setting(_COMPONENT_ID, payload)

    assert_that(
        exc_info.value.response.status_code,
        equal_to(400),
        "malformed threshold payload must be rejected with 400",
    )
    assert_that(
        exc_info.value.response.text,
        contains_string(expected_message),
        "400 response must name the validation failure",
    )
    assert_that(
        customer_config_utils.get_declaration(_COMPONENT_ID)["overridden"],
        equal_to(False),
        "a rejected save must not create an override",
    )


@pytest.mark.xdist_group(name="marketplace_thresholds")
@pytest.mark.customer_configuration
@pytest.mark.api
@pytest.mark.parametrize("field, value", REJECTED_THRESHOLD_VALUES)
def test_marketplace_thresholds_save_rejects_invalid_value_and_keeps_stored_override(
    customer_config_utils, clean_marketplace_thresholds, field, value
):
    """Non-numeric, negative and zero values get 400; the earlier override stays."""
    known = get_marketplace_thresholds_data().as_settings
    customer_config_utils.save_setting(_COMPONENT_ID, known)

    with pytest.raises(HTTPError) as exc_info:
        customer_config_utils.save_setting(_COMPONENT_ID, {**known, field: value})

    assert_that(
        exc_info.value.response.status_code,
        equal_to(400),
        f"{field}={value!r} must be rejected with 400",
    )
    assert_that(
        exc_info.value.response.text,
        contains_string(POSITIVE_INTEGER_MESSAGE),
        "400 response must state the positive-integer rule",
    )

    declaration = customer_config_utils.get_declaration(_COMPONENT_ID)
    assert_that(
        declaration["value"],
        equal_to(known),
        "a rejected save must leave the earlier override unchanged",
    )
    assert_that(declaration["overridden"], equal_to(True))


@pytest.mark.xdist_group(name="marketplace_thresholds")
@pytest.mark.customer_configuration
@pytest.mark.api
@pytest.mark.parametrize("field, value", ACCEPTED_THRESHOLD_VALUES)
def test_marketplace_thresholds_save_accepts_positive_integer_above_365(
    customer_config_utils, clean_marketplace_thresholds, field, value
):
    """The pattern has no upper bound, so 400 days is stored (code is authoritative)."""
    settings = get_marketplace_thresholds_data(**{field: value}).as_settings

    save_response = customer_config_utils.save_setting(_COMPONENT_ID, settings)

    assert_that(
        save_response["settings"][field],
        equal_to(value),
        f"{field}={value!r} must be accepted and echoed",
    )
    assert_that(
        customer_config_utils.get_declaration(_COMPONENT_ID)["value"][field],
        equal_to(value),
        "the accepted value must be persisted",
    )
