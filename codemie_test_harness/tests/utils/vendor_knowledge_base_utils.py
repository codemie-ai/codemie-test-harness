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

"""Utility class for managing vendor knowledge bases (AWS Bedrock, Azure, GCP)."""

from typing import Optional, List
from codemie_sdk.models.vendor_assistant import VendorType
from codemie_sdk.models.vendor_knowledgebase import (
    VendorKnowledgeBaseSettingsResponse,
    VendorKnowledgeBasesResponse,
    VendorKnowledgeBase,
    VendorKnowledgeBaseDetail,
    VendorKnowledgeBaseInstallRequest,
    VendorKnowledgeBaseInstallResponse,
    VendorKnowledgeBaseUninstallResponse,
    VendorKnowledgeBaseStatus,
)
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.logger_util import setup_logger

logger = setup_logger(__name__)


class VendorKnowledgeBaseUtils:
    """Utility class for vendor knowledge base operations."""

    def __init__(self):
        """Initialize VendorKnowledgeBaseUtils with CodeMie client."""
        self.client = get_client()
        self.vendor_kb_service = self.client.vendor_knowledgebases

    def get_knowledgebase_settings(
        self,
        vendor: VendorType,
        page: int = 0,
        per_page: int = 10,
    ) -> VendorKnowledgeBaseSettingsResponse:
        """Get knowledge base settings for a specific cloud vendor.

        Args:
            vendor: Cloud vendor type (AWS, AZURE, GCP)
            page: Page number for pagination
            per_page: Number of items per page

        Returns:
            VendorKnowledgeBaseSettingsResponse containing list of settings
        """
        logger.info(
            f"Getting KB settings for {vendor.value} (page={page}, per_page={per_page})"
        )
        settings = self.vendor_kb_service.get_knowledgebase_settings(
            vendor=vendor, page=page, per_page=per_page
        )
        logger.info(
            f"Retrieved {len(settings.data)} KB settings for {vendor.value} (total: {settings.pagination.total})"
        )
        return settings

    def get_knowledgebases(
        self,
        vendor: VendorType,
        setting_id: str,
        per_page: int = 10,
        next_token: Optional[str] = None,
    ) -> VendorKnowledgeBasesResponse:
        """Get knowledge bases for a specific vendor setting.

        Args:
            vendor: Cloud vendor type
            setting_id: ID of the vendor setting
            per_page: Number of items per page
            next_token: Token for pagination

        Returns:
            VendorKnowledgeBasesResponse containing list of knowledge bases
        """
        logger.info(
            f"Getting knowledge bases for {vendor.value} setting {setting_id} (per_page={per_page})"
        )
        kbs = self.vendor_kb_service.get_knowledgebases(
            vendor=vendor,
            setting_id=setting_id,
            per_page=per_page,
            next_token=next_token,
        )
        logger.info(
            f"Retrieved {len(kbs.data)} knowledge bases for setting {setting_id}"
        )
        return kbs

    def get_knowledgebase(
        self,
        vendor: VendorType,
        knowledgebase_id: str,
        setting_id: str,
    ) -> VendorKnowledgeBaseDetail:
        """Get a specific knowledge base by ID.

        Args:
            vendor: Cloud vendor type
            knowledgebase_id: ID of the knowledge base
            setting_id: ID of the vendor setting

        Returns:
            VendorKnowledgeBaseDetail with knowledge base details
        """
        logger.info(
            f"Getting knowledge base {knowledgebase_id} for {vendor.value} setting {setting_id}"
        )
        kb = self.vendor_kb_service.get_knowledgebase(
            vendor=vendor, knowledgebase_id=knowledgebase_id, setting_id=setting_id
        )
        logger.info(f"Retrieved knowledge base: {kb.name} (status: {kb.status})")
        return kb

    def install_knowledgebases(
        self,
        vendor: VendorType,
        knowledgebases: List[VendorKnowledgeBaseInstallRequest],
    ) -> VendorKnowledgeBaseInstallResponse:
        """Install/activate vendor knowledge bases.

        Args:
            vendor: Cloud vendor type
            knowledgebases: List of knowledge base installation requests

        Returns:
            VendorKnowledgeBaseInstallResponse containing installation summary
        """
        logger.info(
            f"Installing {len(knowledgebases)} knowledge base(s) for {vendor.value}"
        )
        response = self.vendor_kb_service.install_knowledgebases(
            vendor=vendor, knowledgebases=knowledgebases
        )
        for item in response.summary:
            logger.info(
                f"Installed KB {item.knowledgeBaseId} -> CodeMie ID: {item.aiRunId}"
            )
        return response

    def uninstall_knowledgebase(
        self,
        vendor: VendorType,
        codemie_id: str,
    ) -> VendorKnowledgeBaseUninstallResponse:
        """Uninstall/deactivate a vendor knowledge base.

        Args:
            vendor: Cloud vendor type
            codemie_id: CodeMie ID from installation

        Returns:
            VendorKnowledgeBaseUninstallResponse with success status
        """
        logger.info(f"Uninstalling knowledge base with CodeMie ID: {codemie_id}")
        response = self.vendor_kb_service.uninstall_knowledgebase(
            vendor=vendor, ai_run_id=codemie_id
        )
        if response.success:
            logger.info(f"Successfully uninstalled knowledge base {codemie_id}")
        else:
            logger.warning(f"Failed to uninstall knowledge base {codemie_id}")
        return response

    def get_available_knowledge_base(
        self,
        knowledge_bases: List[VendorKnowledgeBase],
    ) -> Optional[VendorKnowledgeBase]:
        """Get first PREPARED knowledge base from the list.

        Args:
            knowledge_bases: List of vendor knowledge bases

        Returns:
            First PREPARED knowledge base or first KB if none are PREPARED
        """
        return next(
            (
                kb
                for kb in knowledge_bases
                if kb.status == VendorKnowledgeBaseStatus.PREPARED
            ),
            knowledge_bases[0] if knowledge_bases else None,
        )

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
            VendorKnowledgeBaseSetting or None if not found
        """
        page = 0
        per_page = 50

        while True:
            settings_response = self.get_knowledgebase_settings(
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

    def find_knowledge_base_by_name(
        self,
        vendor: VendorType,
        setting_id: str,
        kb_name: str,
    ) -> Optional[VendorKnowledgeBase]:
        """Find a knowledge base by name.

        Args:
            vendor: Cloud vendor type
            setting_id: ID of the vendor setting
            kb_name: Name of the knowledge base to find

        Returns:
            VendorKnowledgeBase or None if knowledge base not found
        """
        logger.info(
            f"Searching for knowledge base '{kb_name}' in {vendor.value} setting {setting_id}"
        )
        kbs_response = self.get_knowledgebases(vendor=vendor, setting_id=setting_id)

        for kb in kbs_response.data:
            if kb.name == kb_name and kb.status == VendorKnowledgeBaseStatus.PREPARED:
                logger.info(f"Found knowledge base: {kb.name} (ID: {kb.id})")
                return kb

        logger.warning(
            f"Knowledge base '{kb_name}' not found for {vendor.value} setting {setting_id}"
        )
        return None

    def find_first_available_knowledge_base(
        self,
        vendor: VendorType,
        setting_id: str,
    ) -> Optional[VendorKnowledgeBase]:
        """Find the first prepared knowledge base.

        Args:
            vendor: Cloud vendor type
            setting_id: ID of the vendor setting

        Returns:
            VendorKnowledgeBase or None if no prepared knowledge base found
        """
        logger.info(
            f"Searching for prepared knowledge base in {vendor.value} setting {setting_id}"
        )
        kbs_response = self.get_knowledgebases(vendor=vendor, setting_id=setting_id)

        for kb in kbs_response.data:
            if kb.status == VendorKnowledgeBaseStatus.PREPARED:
                logger.info(f"Found prepared knowledge base: {kb.name} (ID: {kb.id})")
                return kb

        logger.warning(
            f"No prepared knowledge base found for {vendor.value} setting {setting_id}"
        )
        return None

    def install_knowledge_base_by_name(
        self,
        vendor: VendorType,
        setting_id: str,
        kb_name: str,
    ) -> Optional[str]:
        """Find and install a knowledge base by name.

        Args:
            vendor: Cloud vendor type
            setting_id: ID of the vendor setting
            kb_name: Name of the knowledge base to install

        Returns:
            CodeMie ID of the installed knowledge base or None if not found
        """
        kb = self.find_knowledge_base_by_name(
            vendor=vendor, setting_id=setting_id, kb_name=kb_name
        )
        if not kb:
            return None

        install_request = VendorKnowledgeBaseInstallRequest(
            id=kb.id,
            setting_id=setting_id,
        )

        install_response = self.install_knowledgebases(
            vendor=vendor, knowledgebases=[install_request]
        )

        if install_response.summary:
            return install_response.summary[0].aiRunId

        return None

    def install_first_available_knowledge_base(
        self,
        vendor: VendorType,
        setting_id: str,
    ) -> Optional[str]:
        """Find and install the first available knowledge base.

        Args:
            vendor: Cloud vendor type
            setting_id: ID of the vendor setting

        Returns:
            CodeMie ID of the installed knowledge base or None if not available
        """
        kb = self.find_first_available_knowledge_base(
            vendor=vendor, setting_id=setting_id
        )
        if not kb:
            return None

        install_request = VendorKnowledgeBaseInstallRequest(
            id=kb.id,
            setting_id=setting_id,
        )

        install_response = self.install_knowledgebases(
            vendor=vendor, knowledgebases=[install_request]
        )

        if install_response.summary:
            return install_response.summary[0].aiRunId

        return None
