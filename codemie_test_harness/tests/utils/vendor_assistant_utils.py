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

"""Utility class for managing vendor assistants (AWS Bedrock, Azure, GCP)."""

from typing import Optional, List
from codemie_sdk.models.vendor_assistant import (
    VendorType,
    VendorAssistantSettingsResponse,
    VendorAssistantsResponse,
    VendorAssistant,
    VendorAssistantAliasesResponse,
    VendorAssistantInstallRequest,
    VendorAssistantInstallResponse,
    VendorAssistantUninstallResponse,
    VendorAssistantStatus,
)
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.logger_util import setup_logger

logger = setup_logger(__name__)

DRAFT_VERSION = "DRAFT"


class VendorAssistantUtils:
    """Utility class for vendor assistant operations."""

    def __init__(self):
        """Initialize VendorUtils with CodeMie client."""
        self.client = get_client()
        self.vendor_assistant_service = self.client.vendor_assistants

    def get_assistant_settings(
        self,
        vendor: VendorType,
        page: int = 0,
        per_page: int = 10,
    ) -> VendorAssistantSettingsResponse:
        """Get assistant settings for a specific cloud vendor.

        Args:
            vendor: Cloud vendor type (AWS, AZURE, GCP)
            page: Page number for pagination
            per_page: Number of items per page

        Returns:
            VendorAssistantSettingsResponse containing list of settings
        """
        logger.info(
            f"Getting assistant settings for {vendor.value} (page={page}, per_page={per_page})"
        )
        settings = self.vendor_assistant_service.get_assistant_settings(
            vendor=vendor, page=page, per_page=per_page
        )
        logger.info(
            f"Retrieved {len(settings.data)} settings for {vendor.value} (total: {settings.pagination.total})"
        )
        return settings

    def get_assistants(
        self,
        vendor: VendorType,
        setting_id: str,
        per_page: int = 10,
        next_token: Optional[str] = None,
    ) -> VendorAssistantsResponse:
        """Get assistants for a specific vendor setting.

        Args:
            vendor: Cloud vendor type
            setting_id: ID of the vendor setting
            per_page: Number of items per page
            next_token: Token for pagination

        Returns:
            VendorAssistantsResponse containing list of assistants
        """
        logger.info(
            f"Getting assistants for {vendor.value} setting {setting_id} (per_page={per_page})"
        )
        assistants = self.vendor_assistant_service.get_assistants(
            vendor=vendor,
            setting_id=setting_id,
            per_page=per_page,
            next_token=next_token,
        )
        logger.info(
            f"Retrieved {len(assistants.data)} assistants for setting {setting_id}"
        )
        return assistants

    def get_assistant(
        self,
        vendor: VendorType,
        assistant_id: str,
        setting_id: str,
    ) -> VendorAssistant:
        """Get a specific assistant by ID.

        Args:
            vendor: Cloud vendor type
            assistant_id: ID of the assistant
            setting_id: ID of the vendor setting

        Returns:
            VendorAssistant with assistant details
        """
        logger.info(
            f"Getting assistant {assistant_id} for {vendor.value} setting {setting_id}"
        )
        assistant = self.vendor_assistant_service.get_assistant(
            vendor=vendor, assistant_id=assistant_id, setting_id=setting_id
        )
        logger.info(
            f"Retrieved assistant: {assistant.name} (status: {assistant.status})"
        )
        return assistant

    def get_assistant_aliases(
        self,
        vendor: VendorType,
        assistant_id: str,
        setting_id: str,
        per_page: int = 10,
        next_token: Optional[str] = None,
    ) -> VendorAssistantAliasesResponse:
        """Get aliases for a specific vendor assistant.

        Args:
            vendor: Cloud vendor type
            assistant_id: ID of the assistant
            setting_id: ID of the vendor setting
            per_page: Number of items per page
            next_token: Token for pagination

        Returns:
            VendorAssistantAliasesResponse containing list of aliases
        """
        logger.info(
            f"Getting aliases for assistant {assistant_id} in {vendor.value} setting {setting_id}"
        )
        aliases = self.vendor_assistant_service.get_assistant_aliases(
            vendor=vendor,
            assistant_id=assistant_id,
            setting_id=setting_id,
            per_page=per_page,
            next_token=next_token,
        )
        logger.info(
            f"Retrieved {len(aliases.data)} aliases for assistant {assistant_id}"
        )
        return aliases

    def install_assistants(
        self,
        vendor: VendorType,
        assistants: List[VendorAssistantInstallRequest],
    ) -> VendorAssistantInstallResponse:
        """Install/activate vendor assistants.

        Args:
            vendor: Cloud vendor type
            assistants: List of assistant installation requests

        Returns:
            VendorAssistantInstallResponse containing installation summary with CodeMie IDs
        """
        logger.info(f"Installing {len(assistants)} assistant(s) for {vendor.value}")
        response = self.vendor_assistant_service.install_assistants(
            vendor=vendor, assistants=assistants
        )
        for item in response.summary:
            logger.info(
                f"Installed assistant {item.agentId} (alias: {item.agentAliasId}) -> CodeMie ID: {item.aiRunId}"
            )
        return response

    def uninstall_assistant(
        self,
        vendor: VendorType,
        codemie_id: str,
    ) -> VendorAssistantUninstallResponse:
        """Uninstall/deactivate a vendor assistant.

        Args:
            vendor: Cloud vendor type
            codemie_id: CodeMie assistant ID from installation

        Returns:
            VendorAssistantUninstallResponse with success status
        """
        logger.info(f"Uninstalling assistant with CodeMie ID: {codemie_id}")
        response = self.vendor_assistant_service.uninstall_assistant(
            vendor=vendor, ai_run_id=codemie_id
        )
        if response.success:
            logger.info(f"Successfully uninstalled assistant {codemie_id}")
        else:
            logger.warning(f"Failed to uninstall assistant {codemie_id}")
        return response

    def get_prepared_assistant(
        self,
        assistants: List[VendorAssistant],
    ) -> Optional[VendorAssistant]:
        """Get first PREPARED assistant from the list.

        Args:
            assistants: List of vendor assistants

        Returns:
            First PREPARED assistant or first assistant if none are PREPARED
        """
        return next(
            (a for a in assistants if a.status == VendorAssistantStatus.PREPARED),
            assistants[0] if assistants else None,
        )

    def get_non_draft_alias(
        self,
        aliases: List,
    ) -> Optional:
        """Get first non-DRAFT alias from the list.

        Args:
            aliases: List of vendor assistant aliases

        Returns:
            First non-DRAFT alias or first alias if all are DRAFT
        """
        return next(
            (a for a in aliases if a.version != DRAFT_VERSION),
            aliases[0] if aliases else None,
        )

    def find_assistant_by_name(
        self,
        vendor: VendorType,
        setting_id: str,
        assistant_name: str,
    ) -> Optional[tuple[VendorAssistant, str]]:
        """Find an assistant by name and return it with an alias.

        Args:
            vendor: Cloud vendor type
            setting_id: ID of the vendor setting
            assistant_name: Name of the assistant to find

        Returns:
            Tuple of (VendorAssistant, alias_id) or None if assistant not found
        """
        logger.info(
            f"Searching for assistant '{assistant_name}' in {vendor.value} setting {setting_id}"
        )
        assistants_response = self.get_assistants(vendor=vendor, setting_id=setting_id)

        for assistant in assistants_response.data:
            if (
                assistant.name == assistant_name
                and assistant.status == VendorAssistantStatus.PREPARED
            ):
                aliases_response = self.get_assistant_aliases(
                    vendor=vendor, assistant_id=assistant.id, setting_id=setting_id
                )
                if aliases_response.data:
                    non_draft_alias = self.get_non_draft_alias(aliases_response.data)
                    if non_draft_alias:
                        logger.info(
                            f"Found assistant: {assistant.name} (ID: {assistant.id}, Alias: {non_draft_alias.id})"
                        )
                        return assistant, non_draft_alias.id

        logger.warning(
            f"Assistant '{assistant_name}' not found for {vendor.value} setting {setting_id}"
        )
        return None

    def find_first_available_assistant(
        self,
        vendor: VendorType,
        setting_id: str,
    ) -> Optional[tuple[VendorAssistant, str]]:
        """Find the first available (PREPARED) assistant with an alias.

        Args:
            vendor: Cloud vendor type
            setting_id: ID of the vendor setting

        Returns:
            Tuple of (VendorAssistant, alias_id) or None if no available assistant found
        """
        logger.info(
            f"Searching for available assistant in {vendor.value} setting {setting_id}"
        )
        assistants_response = self.get_assistants(vendor=vendor, setting_id=setting_id)

        for assistant in assistants_response.data:
            if assistant.status.value == "PREPARED":
                aliases_response = self.get_assistant_aliases(
                    vendor=vendor, assistant_id=assistant.id, setting_id=setting_id
                )
                if aliases_response.data:
                    first_alias = aliases_response.data[0]
                    logger.info(
                        f"Found available assistant: {assistant.name} (ID: {assistant.id}, Alias: {first_alias.id})"
                    )
                    return assistant, first_alias.id

        logger.warning(
            f"No available assistant found for {vendor.value} setting {setting_id}"
        )
        return None

    def install_assistant_by_name(
        self,
        vendor: VendorType,
        setting_id: str,
        assistant_name: str,
    ) -> Optional[str]:
        """Find and install an assistant by name.

        Args:
            vendor: Cloud vendor type
            setting_id: ID of the vendor setting
            assistant_name: Name of the assistant to install

        Returns:
            CodeMie ID of the installed assistant or None if assistant not found
        """
        result = self.find_assistant_by_name(
            vendor=vendor, setting_id=setting_id, assistant_name=assistant_name
        )
        if not result:
            return None

        assistant, alias_id = result
        install_request = VendorAssistantInstallRequest(
            id=assistant.id,
            agentAliasId=alias_id,
            setting_id=setting_id,
        )

        install_response = self.install_assistants(
            vendor=vendor, assistants=[install_request]
        )

        if install_response.summary:
            return install_response.summary[0].aiRunId

        return None

    def install_first_available_assistant(
        self,
        vendor: VendorType,
        setting_id: str,
    ) -> Optional[str]:
        """Find and install the first available assistant.

        Args:
            vendor: Cloud vendor type
            setting_id: ID of the vendor setting

        Returns:
            CodeMie ID of the installed assistant or None if no assistant available
        """
        result = self.find_first_available_assistant(
            vendor=vendor, setting_id=setting_id
        )
        if not result:
            return None

        assistant, alias_id = result
        install_request = VendorAssistantInstallRequest(
            id=assistant.id,
            agentAliasId=alias_id,
            setting_id=setting_id,
        )

        install_response = self.install_assistants(
            vendor=vendor, assistants=[install_request]
        )

        if install_response.summary:
            return install_response.summary[0].aiRunId

        return None

    def find_setting_for_integration(
        self,
        vendor: VendorType,
        integration_id: str,
    ):
        """Find setting for an integration by paginating through all settings.

        Args:
            vendor: Type of vendor (AWS, AZURE, GCP)
            integration_id: ID of the integration to find (searches by setting_id)

        Returns:
            VendorAssistantSetting or None if not found
        """
        page = 0
        per_page = 50

        while True:
            settings_response = self.get_assistant_settings(
                vendor=vendor,
                page=page,
                per_page=per_page,
            )

            # Find the setting for our integration by setting_id
            for s in settings_response.data:
                if s.setting_id == integration_id:
                    return s

            # Check if there are more pages
            if page >= settings_response.pagination.pages - 1:
                break

            page += 1

        logger.warning(f"Setting not found for integration ID '{integration_id}'")
        return None
