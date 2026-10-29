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

"""Customer config utilities.

Thin wrapper over CustomerConfigService and DynamicConfigService — the sole
entry point tests should use for customer-config reads/writes instead of
calling ``client.customer_config``/``client.dynamic_config`` directly.
"""

from codemie_sdk import CodeMieClient

from codemie_test_harness.tests.utils.base_utils import BaseUtils


class CustomerConfigUtils(BaseUtils):
    """Utilities for customer config reads, writes, and teardown."""

    def __init__(self, client: CodeMieClient):
        super().__init__(client)

    def reset_setting(self, component_id: str) -> None:
        """Reset a component setting to its YAML default.

        Idempotent — safe to call even when no override row exists.

        Args:
            component_id: Component identifier, e.g. ``"chatDisclaimer"``.
        """
        self.client.customer_config.reset_setting(component_id)

    def save_setting(self, component_id: str, settings: dict) -> dict:
        """Persist a settings override for a component.

        Args:
            component_id: Component identifier, e.g. ``"chatDisclaimer"``.
            settings: Key/value map of field names to new values.

        Returns:
            Response dict with ``component_id`` and ``settings``.
        """
        return self.client.customer_config.save_setting(component_id, settings)

    def get_config(self) -> list[dict]:
        """Return the resolved component list from ``GET /v1/config``."""
        return self.client.customer_config.get_config()

    def get_config_component(self, component_id: str) -> dict | None:
        """Return the ``GET /v1/config`` entry for ``component_id``, or ``None``
        when the component is absent (e.g. resolved ``enabled=False``)."""
        return next((c for c in self.get_config() if c.get("id") == component_id), None)

    def list_declarations(self) -> list[dict]:
        """Return all entries from ``GET /v1/config/declarations``."""
        return self.client.customer_config.list_declarations()

    def get_declaration(self, component_id: str) -> dict:
        """Return the declaration entry for ``component_id``.

        Raises:
            StopIteration: If ``component_id`` is not a registered declaration.
        """
        return next(
            d for d in self.list_declarations() if d["component_id"] == component_id
        )

    def write_raw_override(self, key: str, value: str) -> dict:
        """Write a dynamic-config value directly, bypassing declared-field
        validation — the only way to produce an override row missing a
        currently-declared field.

        Args:
            key: Dynamic-config key backing a customer-config component,
                e.g. ``"CUSTOMER_CONFIG__CHAT_DISCLAIMER"``.
            value: Raw string value (e.g. a JSON-encoded partial override).

        Returns:
            Response dict from the admin endpoint.
        """
        return self.client.dynamic_config.set(key, value)
