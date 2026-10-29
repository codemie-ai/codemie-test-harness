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

"""Utility class for managing vendor guardrails (AWS Bedrock, Azure, GCP)."""

from typing import Optional, List, Tuple
from codemie_sdk.models.vendor_assistant import VendorType
from codemie_sdk.models.vendor_guardrail import (
    VendorGuardrailSettingsResponse,
    VendorGuardrailsResponse,
    VendorGuardrail,
    VendorGuardrailVersion,
    VendorGuardrailVersionsResponse,
    VendorGuardrailInstallRequest,
    VendorGuardrailInstallResponse,
    VendorGuardrailUninstallResponse,
    VendorGuardrailStatus,
    VendorGuardrailSetting,
)
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.logger_util import setup_logger

logger = setup_logger(__name__)

DRAFT_VERSION = "DRAFT"


class VendorGuardrailUtils:
    """Utility class for vendor guardrail operations."""

    def __init__(self):
        """Initialize VendorGuardrailUtils with CodeMie client."""
        self.client = get_client()
        self.vendor_guardrail_service = self.client.vendor_guardrails

    def get_guardrail_settings(
        self,
        vendor: VendorType,
        page: int = 0,
        per_page: int = 10,
    ) -> VendorGuardrailSettingsResponse:
        """Get guardrail settings for a specific cloud vendor.

        Args:
            vendor: Cloud vendor type (AWS, AZURE, GCP)
            page: Page number for pagination
            per_page: Number of items per page

        Returns:
            VendorGuardrailSettingsResponse containing list of settings
        """
        logger.info(
            f"Getting guardrail settings for {vendor.value} (page={page}, per_page={per_page})"
        )
        settings = self.vendor_guardrail_service.get_guardrail_settings(
            vendor=vendor, page=page, per_page=per_page
        )
        logger.info(
            f"Retrieved {len(settings.data)} settings for {vendor.value} (total: {settings.pagination.total})"
        )
        return settings

    def get_guardrails(
        self,
        vendor: VendorType,
        setting_id: str,
        per_page: int = 10,
        next_token: Optional[str] = None,
    ) -> VendorGuardrailsResponse:
        """Get guardrails for a specific vendor setting.

        Args:
            vendor: Cloud vendor type
            setting_id: ID of the vendor setting
            per_page: Number of items per page
            next_token: Token for pagination

        Returns:
            VendorGuardrailsResponse containing list of guardrails
        """
        logger.info(
            f"Getting guardrails for {vendor.value} setting {setting_id} (per_page={per_page})"
        )
        guardrails = self.vendor_guardrail_service.get_guardrails(
            vendor=vendor,
            setting_id=setting_id,
            per_page=per_page,
            next_token=next_token,
        )
        logger.info(
            f"Retrieved {len(guardrails.data)} guardrails for setting {setting_id}"
        )
        return guardrails

    def get_guardrail(
        self,
        vendor: VendorType,
        guardrail_id: str,
        setting_id: str,
    ) -> VendorGuardrail:
        """Get a specific guardrail by ID.

        Args:
            vendor: Cloud vendor type
            guardrail_id: ID of the guardrail
            setting_id: ID of the vendor setting

        Returns:
            VendorGuardrail containing guardrail details
        """
        logger.info(
            f"Getting guardrail {guardrail_id} for {vendor.value} setting {setting_id}"
        )
        guardrail = self.vendor_guardrail_service.get_guardrail(
            vendor=vendor,
            guardrail_id=guardrail_id,
            setting_id=setting_id,
        )
        logger.info(f"Retrieved guardrail {guardrail.name} (ID: {guardrail.id})")
        return guardrail

    def get_guardrail_version(
        self,
        vendor: VendorType,
        guardrail_id: str,
        version: str,
        setting_id: str,
    ) -> VendorGuardrailVersion:
        """Get a specific version of a guardrail.

        Args:
            vendor: Cloud vendor type
            guardrail_id: ID of the guardrail
            version: Version to retrieve
            setting_id: ID of the vendor setting

        Returns:
            VendorGuardrailVersion containing detailed version information
        """
        logger.info(
            f"Getting version {version} of guardrail {guardrail_id} for {vendor.value}"
        )
        version_details = self.vendor_guardrail_service.get_guardrail_version(
            vendor=vendor,
            guardrail_id=guardrail_id,
            version=version,
            setting_id=setting_id,
        )
        logger.info(
            f"Retrieved version {version_details.version} of guardrail {version_details.name}"
        )
        return version_details

    def get_guardrail_versions(
        self,
        vendor: VendorType,
        guardrail_id: str,
        setting_id: str,
        per_page: int = 10,
        next_token: Optional[str] = None,
    ) -> VendorGuardrailVersionsResponse:
        """Get versions for a specific guardrail.

        Args:
            vendor: Cloud vendor type
            guardrail_id: ID of the guardrail
            setting_id: ID of the vendor setting
            per_page: Number of items per page
            next_token: Token for pagination

        Returns:
            VendorGuardrailVersionsResponse containing list of versions
        """
        logger.info(
            f"Getting versions for guardrail {guardrail_id} (per_page={per_page})"
        )
        versions = self.vendor_guardrail_service.get_guardrail_versions(
            vendor=vendor,
            guardrail_id=guardrail_id,
            setting_id=setting_id,
            per_page=per_page,
            next_token=next_token,
        )
        logger.info(
            f"Retrieved {len(versions.data)} versions for guardrail {guardrail_id}"
        )
        return versions

    def install_guardrails(
        self,
        vendor: VendorType,
        guardrails: List[VendorGuardrailInstallRequest],
    ) -> VendorGuardrailInstallResponse:
        """Install/activate vendor guardrails.

        Args:
            vendor: Cloud vendor type
            guardrails: List of guardrail installation requests

        Returns:
            VendorGuardrailInstallResponse containing installation summary
        """
        logger.info(f"Installing {len(guardrails)} guardrail(s) for {vendor.value}")
        response = self.vendor_guardrail_service.install_guardrails(
            vendor=vendor, guardrails=guardrails
        )
        logger.info(f"Successfully installed {len(response.summary)} guardrail(s)")
        for item in response.summary:
            logger.info(
                f"  - Guardrail {item.guardrailId} version {item.version} with AI run ID: {item.aiRunId}"
            )
        return response

    def uninstall_guardrail(
        self,
        vendor: VendorType,
        ai_run_id: str,
    ) -> VendorGuardrailUninstallResponse:
        """Uninstall/deactivate a vendor guardrail.

        Args:
            vendor: Cloud vendor type
            ai_run_id: AI run ID returned from the install operation

        Returns:
            VendorGuardrailUninstallResponse with success status
        """
        logger.info(
            f"Uninstalling guardrail with AI run ID {ai_run_id} for {vendor.value}"
        )
        response = self.vendor_guardrail_service.uninstall_guardrail(
            vendor=vendor, ai_run_id=ai_run_id
        )
        if response.success:
            logger.info(
                f"Successfully uninstalled guardrail with AI run ID {ai_run_id}"
            )
        else:
            logger.warning(f"Failed to uninstall guardrail with AI run ID {ai_run_id}")
        return response

    def find_setting_for_integration(
        self,
        vendor: VendorType,
        integration_id: str,
    ) -> Optional[VendorGuardrailSetting]:
        """Find a guardrail setting associated with a specific integration.

        Args:
            vendor: Cloud vendor type
            integration_id: ID of the integration to find (searches by setting_id)

        Returns:
            VendorGuardrailSetting if found, None otherwise
        """
        logger.info(
            f"Finding guardrail setting for integration {integration_id} in {vendor.value}"
        )
        page = 0
        per_page = 50

        while True:
            settings_response = self.get_guardrail_settings(
                vendor=vendor,
                page=page,
                per_page=per_page,
            )

            # Find the setting for our integration by setting_id
            for setting in settings_response.data:
                if setting.setting_id == integration_id:
                    logger.info(f"Found setting {setting.setting_name} for integration")
                    return setting

            # Check if there are more pages
            if page >= settings_response.pagination.pages - 1:
                break

            page += 1

        logger.warning(f"No guardrail setting found for integration {integration_id}")
        return None

    def get_prepared_guardrail(
        self,
        guardrails: List[VendorGuardrail],
    ) -> Optional[VendorGuardrail]:
        """Get the first PREPARED guardrail from a list.

        Args:
            guardrails: List of guardrails to search

        Returns:
            First PREPARED guardrail if found, None otherwise
        """
        for guardrail in guardrails:
            if guardrail.status == VendorGuardrailStatus.PREPARED:
                logger.info(f"Found PREPARED guardrail: {guardrail.name}")
                return guardrail

        logger.warning("No PREPARED guardrails found in the list")
        return None

    def get_non_draft_version(
        self,
        versions: List[VendorGuardrailVersion],
    ) -> Optional[VendorGuardrailVersion]:
        """Get the first non-DRAFT version from a list.

        Args:
            versions: List of versions to search

        Returns:
            First non-DRAFT version if found, None otherwise
        """
        for version in versions:
            if version.version != DRAFT_VERSION:
                logger.info(f"Found non-DRAFT version: {version.version}")
                return version

        logger.warning("No non-DRAFT versions found in the list")
        return None

    def find_first_available_guardrail(
        self,
        vendor: VendorType,
        setting_id: str,
    ) -> Optional[Tuple[VendorGuardrail, str]]:
        """Find the first available guardrail with a non-DRAFT version.

        Args:
            vendor: Cloud vendor type
            setting_id: ID of the vendor setting

        Returns:
            Tuple of (VendorGuardrail, version_string) if found, None otherwise
        """
        logger.info(
            f"Finding first available guardrail for {vendor.value} setting {setting_id}"
        )
        guardrails_response = self.get_guardrails(
            vendor=vendor, setting_id=setting_id, per_page=50
        )

        guardrail = self.get_prepared_guardrail(guardrails_response.data)
        if not guardrail:
            logger.warning("No PREPARED guardrails found")
            return None

        versions_response = self.get_guardrail_versions(
            vendor=vendor,
            guardrail_id=guardrail.id,
            setting_id=setting_id,
            per_page=10,
        )

        version = self.get_non_draft_version(versions_response.data)
        if not version:
            logger.warning(f"No non-DRAFT versions found for guardrail {guardrail.id}")
            return None

        logger.info(
            f"Found available guardrail {guardrail.name} with version {version.version}"
        )
        return guardrail, version.version

    def install_first_available_guardrail(
        self,
        vendor: VendorType,
        setting_id: str,
    ) -> Optional[str]:
        """Find and install the first available guardrail.

        Args:
            vendor: Cloud vendor type
            setting_id: ID of the vendor setting

        Returns:
            AI run ID if installation successful, None otherwise
        """
        result = self.find_first_available_guardrail(
            vendor=vendor, setting_id=setting_id
        )
        if not result:
            logger.error("No available guardrails found to install")
            return None

        guardrail, version = result

        install_request = VendorGuardrailInstallRequest(
            id=guardrail.id,
            version=version,
            setting_id=setting_id,
        )

        install_response = self.install_guardrails(
            vendor=vendor,
            guardrails=[install_request],
        )

        if install_response.summary:
            ai_run_id = install_response.summary[0].aiRunId
            logger.info(f"Installed guardrail with AI run ID: {ai_run_id}")
            return ai_run_id

        logger.error("Installation failed - no summary returned")
        return None
