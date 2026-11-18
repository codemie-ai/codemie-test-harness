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

"""Creates integrations for a test and removes them again, whichever scope they belong to."""

from typing import List, Optional

from codemie_sdk.models.integration import (
    CredentialTypes,
    CredentialValues,
    Integration,
    IntegrationType,
)
from codemie_test_harness.tests.test_data.unified_integrations_list_test_data import (
    jira_placeholder_credentials,
)
from codemie_test_harness.tests.utils.integration_utils import IntegrationUtils
from codemie_test_harness.tests.utils.logger_util import setup_logger

logger = setup_logger(__name__)


class ScopedIntegrationFactory:
    """Creates user and project integrations as any client and deletes them on `delete_all`.

    The `scoped_integrations` fixture yields one and calls `delete_all` after the test, so a
    failing test still leaves nothing behind. Rows a UI flow creates are registered with
    `track_alias`; their scope and id are only known by listing.
    """

    def __init__(self):
        self._created: list[tuple[IntegrationUtils, Integration]] = []
        self._aliases: list[tuple[IntegrationUtils, str]] = []

    def create(
        self,
        utils: IntegrationUtils,
        setting_type: IntegrationType,
        project_name: str,
        alias: str,
        credential_type: CredentialTypes = CredentialTypes.JIRA,
        credential_values: Optional[List[CredentialValues]] = None,
        is_global: bool = False,
    ) -> Integration:
        integration = utils.create_integration(
            credential_type=credential_type,
            credential_values=credential_values or jira_placeholder_credentials(),
            setting_type=setting_type,
            project_name=project_name,
            integration_alias=alias,
            is_global=is_global,
        )
        self._created.append((utils, integration))
        return integration

    def track_alias(self, utils: IntegrationUtils, alias: str) -> str:
        """Register an alias a UI flow will create, so `delete_all` removes it in either scope."""
        self._aliases.append((utils, alias))
        return alias

    def delete_all(self) -> None:
        for utils, integration in reversed(self._created):
            self._delete_quietly(
                lambda: utils.delete_integration_if_exists(integration)
            )
        for utils, alias in reversed(self._aliases):
            self._delete_quietly(lambda: utils.delete_integrations_by_alias(alias))

    @staticmethod
    def _delete_quietly(delete) -> None:
        try:
            delete()
        except Exception as error:
            logger.warning(f"Failed to delete a test integration: {error}")
