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

"""Utility class for managing vendor workflows (AWS Bedrock, Azure, GCP)."""

from typing import Optional, List
from codemie_sdk.models.vendor_assistant import VendorType
from codemie_sdk.models.vendor_workflow import (
    VendorWorkflowSettingsResponse,
    VendorWorkflowsResponse,
    VendorWorkflow,
    VendorWorkflowAliasesResponse,
    VendorWorkflowInstallRequest,
    VendorWorkflowInstallResponse,
    VendorWorkflowUninstallResponse,
    VendorWorkflowStatus,
)
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.logger_util import setup_logger

logger = setup_logger(__name__)

DRAFT_VERSION = "DRAFT"


class VendorWorkflowUtils:
    """Utility class for vendor workflow operations."""

    def __init__(self):
        """Initialize VendorWorkflowUtils with CodeMie client."""
        self.client = get_client()
        self.vendor_workflow_service = self.client.vendor_workflows

    def get_workflow_settings(
        self,
        vendor: VendorType,
        page: int = 0,
        per_page: int = 10,
    ) -> VendorWorkflowSettingsResponse:
        """Get workflow settings for a specific cloud vendor.

        Args:
            vendor: Cloud vendor type (AWS, AZURE, GCP)
            page: Page number for pagination
            per_page: Number of items per page

        Returns:
            VendorWorkflowSettingsResponse containing list of settings
        """
        logger.info(
            f"Getting workflow settings for {vendor.value} (page={page}, per_page={per_page})"
        )
        settings = self.vendor_workflow_service.get_workflow_settings(
            vendor=vendor, page=page, per_page=per_page
        )
        logger.info(
            f"Retrieved {len(settings.data)} settings for {vendor.value} (total: {settings.pagination.total})"
        )
        return settings

    def get_workflows(
        self,
        vendor: VendorType,
        setting_id: str,
        per_page: int = 10,
        next_token: Optional[str] = None,
    ) -> VendorWorkflowsResponse:
        """Get workflows for a specific vendor setting.

        Args:
            vendor: Cloud vendor type
            setting_id: ID of the vendor setting
            per_page: Number of items per page
            next_token: Token for pagination

        Returns:
            VendorWorkflowsResponse containing list of workflows
        """
        logger.info(
            f"Getting workflows for {vendor.value} setting {setting_id} (per_page={per_page})"
        )
        workflows = self.vendor_workflow_service.get_workflows(
            vendor=vendor,
            setting_id=setting_id,
            per_page=per_page,
            next_token=next_token,
        )
        logger.info(
            f"Retrieved {len(workflows.data)} workflows for setting {setting_id}"
        )
        return workflows

    def get_workflow(
        self,
        vendor: VendorType,
        workflow_id: str,
        setting_id: str,
    ) -> VendorWorkflow:
        """Get a specific workflow by ID.

        Args:
            vendor: Cloud vendor type
            workflow_id: ID of the workflow
            setting_id: ID of the vendor setting

        Returns:
            VendorWorkflow with workflow details
        """
        logger.info(
            f"Getting workflow {workflow_id} for {vendor.value} setting {setting_id}"
        )
        workflow = self.vendor_workflow_service.get_workflow(
            vendor=vendor, workflow_id=workflow_id, setting_id=setting_id
        )
        logger.info(f"Retrieved workflow: {workflow.name} (status: {workflow.status})")
        return workflow

    def get_workflow_aliases(
        self,
        vendor: VendorType,
        workflow_id: str,
        setting_id: str,
        per_page: int = 10,
        next_token: Optional[str] = None,
    ) -> VendorWorkflowAliasesResponse:
        """Get aliases for a specific vendor workflow.

        Args:
            vendor: Cloud vendor type
            workflow_id: ID of the workflow
            setting_id: ID of the vendor setting
            per_page: Number of items per page
            next_token: Token for pagination

        Returns:
            VendorWorkflowAliasesResponse containing list of aliases
        """
        logger.info(
            f"Getting aliases for workflow {workflow_id} in {vendor.value} setting {setting_id}"
        )
        aliases = self.vendor_workflow_service.get_workflow_aliases(
            vendor=vendor,
            workflow_id=workflow_id,
            setting_id=setting_id,
            per_page=per_page,
            next_token=next_token,
        )
        logger.info(f"Retrieved {len(aliases.data)} aliases for workflow {workflow_id}")
        return aliases

    def install_workflows(
        self,
        vendor: VendorType,
        workflows: List[VendorWorkflowInstallRequest],
    ) -> VendorWorkflowInstallResponse:
        """Install/activate vendor workflows.

        Args:
            vendor: Cloud vendor type
            workflows: List of workflow installation requests

        Returns:
            VendorWorkflowInstallResponse containing installation summary with CodeMie IDs
        """
        logger.info(f"Installing {len(workflows)} workflow(s) for {vendor.value}")
        response = self.vendor_workflow_service.install_workflows(
            vendor=vendor, workflows=workflows
        )
        for item in response.summary:
            logger.info(
                f"Installed workflow {item.flowId} (alias: {item.flowAliasId}) -> CodeMie ID: {item.aiRunId}"
            )
        return response

    def uninstall_workflow(
        self,
        vendor: VendorType,
        codemie_id: str,
    ) -> VendorWorkflowUninstallResponse:
        """Uninstall/deactivate a vendor workflow.

        Args:
            vendor: Cloud vendor type
            codemie_id: CodeMie workflow ID from installation

        Returns:
            VendorWorkflowUninstallResponse with success status
        """
        logger.info(f"Uninstalling workflow with CodeMie ID: {codemie_id}")
        response = self.vendor_workflow_service.uninstall_workflow(
            vendor=vendor, ai_run_id=codemie_id
        )
        if response.success:
            logger.info(f"Successfully uninstalled workflow {codemie_id}")
        else:
            logger.warning(f"Failed to uninstall workflow {codemie_id}")
        return response

    def get_prepared_workflow(
        self,
        workflows: List[VendorWorkflow],
    ) -> Optional[VendorWorkflow]:
        """Get first PREPARED workflow from the list.

        Args:
            workflows: List of vendor workflows

        Returns:
            First PREPARED workflow or first workflow if none are PREPARED
        """
        return next(
            (w for w in workflows if w.status == VendorWorkflowStatus.PREPARED),
            workflows[0] if workflows else None,
        )

    def get_non_draft_alias(
        self,
        aliases: List,
    ) -> Optional:
        """Get first non-DRAFT alias from the list.

        Args:
            aliases: List of vendor workflow aliases

        Returns:
            First non-DRAFT alias or first alias if all are DRAFT
        """
        return next(
            (a for a in aliases if a.version != DRAFT_VERSION),
            aliases[0] if aliases else None,
        )

    def find_workflow_by_name(
        self,
        vendor: VendorType,
        setting_id: str,
        workflow_name: str,
    ) -> Optional[tuple[VendorWorkflow, str]]:
        """Find a workflow by name and return it with an alias.

        Args:
            vendor: Cloud vendor type
            setting_id: ID of the vendor setting
            workflow_name: Name of the workflow to find

        Returns:
            Tuple of (VendorWorkflow, alias_id) or None if workflow not found
        """
        logger.info(
            f"Searching for workflow '{workflow_name}' in {vendor.value} setting {setting_id}"
        )
        workflows_response = self.get_workflows(vendor=vendor, setting_id=setting_id)

        for workflow in workflows_response.data:
            if (
                workflow.name == workflow_name
                and workflow.status == VendorWorkflowStatus.PREPARED
            ):
                aliases_response = self.get_workflow_aliases(
                    vendor=vendor, workflow_id=workflow.id, setting_id=setting_id
                )
                if aliases_response.data:
                    non_draft_alias = self.get_non_draft_alias(aliases_response.data)
                    if non_draft_alias:
                        logger.info(
                            f"Found workflow: {workflow.name} (ID: {workflow.id}, Alias: {non_draft_alias.id})"
                        )
                        return workflow, non_draft_alias.id

        logger.warning(
            f"Workflow '{workflow_name}' not found for {vendor.value} setting {setting_id}"
        )
        return None

    def find_first_available_workflow(
        self,
        vendor: VendorType,
        setting_id: str,
    ) -> Optional[tuple[VendorWorkflow, str]]:
        """Find the first available (PREPARED) workflow with an alias.

        Args:
            vendor: Cloud vendor type
            setting_id: ID of the vendor setting

        Returns:
            Tuple of (VendorWorkflow, alias_id) or None if no available workflow found
        """
        logger.info(
            f"Searching for available workflow in {vendor.value} setting {setting_id}"
        )
        workflows_response = self.get_workflows(vendor=vendor, setting_id=setting_id)

        for workflow in workflows_response.data:
            if workflow.status == VendorWorkflowStatus.PREPARED:
                aliases_response = self.get_workflow_aliases(
                    vendor=vendor, workflow_id=workflow.id, setting_id=setting_id
                )
                if aliases_response.data:
                    first_alias = aliases_response.data[0]
                    logger.info(
                        f"Found available workflow: {workflow.name} (ID: {workflow.id}, Alias: {first_alias.id})"
                    )
                    return workflow, first_alias.id

        logger.warning(
            f"No available workflow found for {vendor.value} setting {setting_id}"
        )
        return None

    def install_workflow_by_name(
        self,
        vendor: VendorType,
        setting_id: str,
        workflow_name: str,
    ) -> Optional[str]:
        """Find and install a workflow by name.

        Args:
            vendor: Cloud vendor type
            setting_id: ID of the vendor setting
            workflow_name: Name of the workflow to install

        Returns:
            CodeMie ID of the installed workflow or None if workflow not found
        """
        result = self.find_workflow_by_name(
            vendor=vendor, setting_id=setting_id, workflow_name=workflow_name
        )
        if not result:
            return None

        workflow, alias_id = result
        install_request = VendorWorkflowInstallRequest(
            id=workflow.id,
            flowAliasId=alias_id,
            setting_id=setting_id,
        )

        install_response = self.install_workflows(
            vendor=vendor, workflows=[install_request]
        )

        if install_response.summary:
            return install_response.summary[0].aiRunId

        return None

    def install_first_available_workflow(
        self,
        vendor: VendorType,
        setting_id: str,
    ) -> Optional[str]:
        """Find and install the first available workflow.

        Args:
            vendor: Cloud vendor type
            setting_id: ID of the vendor setting

        Returns:
            CodeMie ID of the installed workflow or None if no workflow available
        """
        result = self.find_first_available_workflow(
            vendor=vendor, setting_id=setting_id
        )
        if not result:
            return None

        workflow, alias_id = result
        install_request = VendorWorkflowInstallRequest(
            id=workflow.id,
            flowAliasId=alias_id,
            setting_id=setting_id,
        )

        install_response = self.install_workflows(
            vendor=vendor, workflows=[install_request]
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
            VendorWorkflowSetting or None if not found
        """
        page = 0
        per_page = 50

        while True:
            settings_response = self.get_workflow_settings(
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
