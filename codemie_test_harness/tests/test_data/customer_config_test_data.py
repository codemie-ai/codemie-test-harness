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

"""Test data for customer configuration API tests."""

from dataclasses import dataclass, field

from codemie_test_harness.tests.utils.base_utils import get_random_name


@dataclass
class DisclaimerSettingsData:
    """Disclaimer settings override payload for customer-config write tests."""

    text: str = field(
        default_factory=lambda: (
            f"Autotest disclaimer {get_random_name()} — see https://example.com"
        )
    )
    enabled: bool = True

    @property
    def as_settings(self) -> dict:
        """Return settings dict for PUT /v1/config/declarations/{id} body."""
        return {"enabled": self.enabled, "text": self.text}


def get_disclaimer_settings_data(
    enabled: bool = True,
    text: str | None = None,
) -> DisclaimerSettingsData:
    """Build disclaimer settings payload with a unique text value.

    Args:
        enabled: Whether the disclaimer should be enabled.  Default: True.
        text: Custom text.  When *None* a unique random text with an embedded URL
              is generated (suitable for link-rendering assertions).

    Returns:
        :class:`DisclaimerSettingsData` instance ready for use in tests.
    """
    if text is not None:
        return DisclaimerSettingsData(enabled=enabled, text=text)
    return DisclaimerSettingsData(enabled=enabled)


def get_disclaimer_partial_override_text() -> str:
    """Build a unique disclaimer 'text'-only override value (TC-005).

    Used as the sole key of a raw dynamic-config override value (see
    :func:`get_disclaimer_dynamic_config_key`), to probe that a declared field
    omitted from a stored override row keeps resolving from YAML instead of
    being defaulted to null/false.

    Returns:
        A unique text string suitable as the sole value of an override
        payload, e.g. ``{"text": <this value>}``.
    """
    return f"partial-field probe {get_random_name()}"


_DISCLAIMER_DYNAMIC_CONFIG_KEY = "CUSTOMER_CONFIG__CHAT_DISCLAIMER"


def get_disclaimer_dynamic_config_key() -> str:
    """Dynamic-config key backing the chatDisclaimer override row (TC-005).

    ``PUT /v1/config/declarations/chatDisclaimer`` (``CustomerConfigService.save_setting``)
    validates the request body via ``validate_and_sanitize``/``_validate_field``, which
    raises HTTP 400 ("Missing configuration field") for *any* declared field omitted
    from the payload — both 'enabled' and 'text' must be present on every write. A
    stored override row that is missing a currently-declared field (the scenario AC-2
    describes) can therefore never be produced through that endpoint; it can only arise
    from a legacy row that predates a declaration gaining a field.

    To probe the read-side merge behaviour black-box, this key is written to directly
    via the super-admin ``/v1/dynamic-config/{key}`` endpoint
    (``CustomerConfigUtils.write_raw_override``), which stores the raw string value
    without the declared-settings endpoint's per-field completeness check —
    reproducing a field-incomplete override row without touching the database
    directly.

    Returns:
        The dynamic-config key for chatDisclaimer,
        ``"CUSTOMER_CONFIG__CHAT_DISCLAIMER"`` (see
        ``customer_config_declarations.build_key``: ``:`` -> ``__``, camelCase
        boundaries -> ``_``, upper-cased).
    """
    return _DISCLAIMER_DYNAMIC_CONFIG_KEY


@dataclass
class WebSearchSettingsData:
    """features:webSearch settings override payload."""

    enabled: bool = False

    @property
    def as_settings(self) -> dict:
        """Return settings dict for PUT /v1/config/declarations/{id} body."""
        return {"enabled": self.enabled}


def get_web_search_settings_data(enabled: bool = False) -> WebSearchSettingsData:
    """Build a features:webSearch settings override payload.

    Args:
        enabled: Whether the web-search feature override should be enabled.
                 Default: False.

    Returns:
        :class:`WebSearchSettingsData` instance ready for use in tests.
    """
    return WebSearchSettingsData(enabled=enabled)
