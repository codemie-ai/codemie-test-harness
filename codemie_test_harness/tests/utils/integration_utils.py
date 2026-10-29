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

from typing import Any, Optional, Dict

from codemie_sdk.models.integration import (
    Integration,
    CredentialTypes,
    CredentialValues,
    IntegrationType,
    IntegrationTestRequest,
    TypeOfIntegration,
)
from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.utils.constants import test_project_name
from codemie_test_harness.tests.utils.base_utils import (
    BaseUtils,
    wait_for_entity,
    get_random_name,
)


class IntegrationUtils(BaseUtils):
    def create_integration(
        self,
        credential_type: CredentialTypes,
        credential_values: list[CredentialValues],
        setting_type: IntegrationType = None,
        project_name: str = None,
        integration_alias: str = None,
        is_global: bool = False,
    ):
        setting_type = IntegrationType.PROJECT if setting_type is None else setting_type
        integration_alias = (
            get_random_name() if integration_alias is None else integration_alias
        )
        project_name = PROJECT if project_name is None else project_name

        create_request = Integration(
            project_name=project_name,
            credential_type=credential_type,
            credential_values=credential_values,
            alias=integration_alias,
            setting_type=setting_type,
            is_global=is_global,
        )

        self.client.integrations.create(create_request)

        return wait_for_entity(
            lambda: self.client.integrations.list(setting_type, per_page=200),
            entity_name=integration_alias,
        )

    def get_integration_by_alias(
        self, integration_alias: str, integration_type: IntegrationType
    ):
        return self.client.integrations.get_by_alias(
            setting_type=integration_type, alias=integration_alias
        )

    def test_integration(
        self, integration: IntegrationTestRequest, response_type: Any = None
    ):
        if response_type is None:
            response_type = dict
        return self.client.integrations.test(integration, response_type=response_type)

    def update_integration(self, integration: Integration):
        return self.client.integrations.update(
            setting_id=integration.id, settings=integration
        )

    def send_create_integration_request(self, integration: Integration):
        return self.client.integrations.create(settings=integration)

    def get_integration_by_id(
        self, integration_id: str, setting_type: IntegrationType
    ) -> Optional[Integration]:
        """Return the integration with this id, or None when no listed row has it.

        Unlike ``client.integrations.get`` this does not raise when the row is
        absent and reads a larger page, so tests can assert on absence too.
        """
        return next(
            (
                row
                for row in self.client.integrations.list(setting_type, per_page=200)
                if row.id == integration_id
            ),
            None,
        )

    def get_integration_by_project_and_alias(
        self, project_name: str, alias: str, setting_type: IntegrationType
    ) -> Optional[Integration]:
        """Return the integration matching both project and alias, or None.

        ``get_integration_by_alias`` is ambiguous once two projects hold an
        integration with the same alias; scoping by project removes that.
        """
        return next(
            (
                row
                for row in self.client.integrations.list(setting_type, per_page=200)
                if row.project_name == project_name and row.alias == alias
            ),
            None,
        )

    def list_integration_ids_in_project(
        self, project_name: str, setting_type: IntegrationType
    ) -> list[str]:
        """Ids of every listed integration of this scope that belongs to the project."""
        return [
            row.id
            for row in self.client.integrations.list(setting_type, per_page=200)
            if row.project_name == project_name
        ]

    def delete_integration_by_id(
        self, integration_id: str, setting_type: IntegrationType
    ):
        return self.client.integrations.delete(
            setting_id=integration_id, setting_type=setting_type
        )

    def delete_integration(self, integration: Integration):
        return self.client.integrations.delete(
            setting_id=integration.id, setting_type=integration.setting_type
        )

    def delete_integrations_by_type(
        self,
        integration_type: IntegrationType,
        credential_type: CredentialTypes,
        project: str = None,
    ):
        test_projects = [PROJECT, test_project_name]

        integrations = self.client.integrations.list(
            setting_type=integration_type,
            per_page=100,
            filters={"type": credential_type.value, "search": project}
            if project
            else {"type": credential_type.value},
        )

        for integration in integrations:
            should_delete = False

            if integration_type == IntegrationType.PROJECT:
                should_delete = True
            elif integration_type == IntegrationType.USER:
                if integration.project_name in test_projects:
                    should_delete = True
                elif integration.is_global:
                    should_delete = True

            if should_delete:
                self.client.integrations.delete(
                    setting_id=integration.id, setting_type=integration_type
                )

    def create_user_integration(
        self,
        credential_type: CredentialTypes,
        credentials: list[CredentialValues],
        project_name: str = None,
        is_global: bool = False,
    ):
        return self.create_integration(
            credential_type=credential_type,
            credential_values=credentials,
            setting_type=IntegrationType.USER,
            project_name=project_name,
            is_global=is_global,
        )

    def create_global_integration(
        self,
        credential_type: CredentialTypes,
        credentials: list[CredentialValues],
        project_name: str = None,
    ):
        return self.create_integration(
            credential_type=credential_type,
            credential_values=credentials,
            setting_type=IntegrationType.USER,
            project_name=project_name,
            is_global=True,
        )

    def create_project_integration(
        self,
        credential_type: CredentialTypes,
        credentials: list[CredentialValues],
        project_name: str = None,
    ):
        return self.create_integration(
            credential_type=credential_type,
            credential_values=credentials,
            setting_type=IntegrationType.PROJECT,
            project_name=project_name,
            is_global=False,
        )

    def list_integrations(
        self,
        setting_type: IntegrationType,
        page: int = 0,
        per_page: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ):
        return self.client.integrations.list(setting_type, page, per_page, filters)

    def transfer_settings(
        self,
        source_project_name: str,
        target_project_name: str,
        mode,
        type_of_integration: TypeOfIntegration | dict[str, bool] | None = None,
        integrations_list: list[str] | None = None,
    ):
        """Move or copy every transferable integration between two projects.

        Thin wrapper around ``client.integrations.transfer`` (POST
        /v1/settings/transfer), following this module's convention of never
        calling the SDK client directly from test code.
        """
        return self.client.integrations.transfer(
            source_project_name=source_project_name,
            target_project_name=target_project_name,
            mode=mode,
            type_of_integration=type_of_integration,
            integrations_list=integrations_list,
        )
