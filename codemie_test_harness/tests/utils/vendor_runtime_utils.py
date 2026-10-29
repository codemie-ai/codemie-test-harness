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

"""Utility class for managing vendor AgentCore runtimes (AWS Bedrock)."""

import json
from typing import Optional, List
from codemie_sdk.models.vendor_assistant import VendorType
from codemie_sdk.models.vendor_runtime import (
    VendorRuntimeSettingsResponse,
    VendorRuntimesResponse,
    VendorRuntime,
    VendorRuntimeStatus,
    VendorRuntimeEndpointsResponse,
    VendorRuntimeEndpoint,
    VendorRuntimeEndpointStatus,
    VendorRuntimeEndpointDetail,
    VendorRuntimeInstallRequest,
    VendorRuntimeInstallSummary,
    VendorRuntimeUninstallResponse,
)
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.logger_util import setup_logger

logger = setup_logger(__name__)


class VendorRuntimeUtils:
    """Utility class for vendor AgentCore runtime operations."""

    def __init__(self):
        self.client = get_client()
        self.vendor_runtime_service = self.client.vendor_runtimes

    def get_runtime_settings(
        self,
        vendor: VendorType,
        page: int = 0,
        per_page: int = 10,
    ) -> VendorRuntimeSettingsResponse:
        """Get runtime settings for a specific cloud vendor."""
        logger.info(
            f"Getting runtime settings for {vendor.value} (page={page}, per_page={per_page})"
        )
        settings = self.vendor_runtime_service.get_runtime_settings(
            vendor=vendor, page=page, per_page=per_page
        )
        logger.info(
            f"Retrieved {len(settings.data)} settings for {vendor.value} (total: {settings.pagination.total})"
        )
        return settings

    def get_runtimes(
        self,
        vendor: VendorType,
        setting_id: str,
        per_page: int = 10,
        next_token: Optional[str] = None,
    ) -> VendorRuntimesResponse:
        """Get runtimes for a specific vendor setting."""
        logger.info(
            f"Getting runtimes for {vendor.value} setting {setting_id} (per_page={per_page})"
        )
        runtimes = self.vendor_runtime_service.get_runtimes(
            vendor=vendor,
            setting_id=setting_id,
            per_page=per_page,
            next_token=next_token,
        )
        logger.info(f"Retrieved {len(runtimes.data)} runtimes for setting {setting_id}")
        return runtimes

    def get_runtime(
        self,
        vendor: VendorType,
        runtime_id: str,
        setting_id: str,
    ) -> VendorRuntime:
        """Get a specific runtime by ID."""
        logger.info(
            f"Getting runtime {runtime_id} for {vendor.value} setting {setting_id}"
        )
        runtime = self.vendor_runtime_service.get_runtime(
            vendor=vendor, runtime_id=runtime_id, setting_id=setting_id
        )
        logger.info(f"Retrieved runtime: {runtime.name} (status: {runtime.status})")
        return runtime

    def get_prepared_runtime(
        self,
        runtimes: List[VendorRuntime],
    ) -> Optional[VendorRuntime]:
        """Get first PREPARED runtime from the list."""
        return next(
            (r for r in runtimes if r.status == VendorRuntimeStatus.PREPARED),
            runtimes[0] if runtimes else None,
        )

    def get_endpoints(
        self,
        vendor: VendorType,
        runtime_id: str,
        setting_id: str,
        per_page: int = 10,
        next_token: Optional[str] = None,
    ) -> VendorRuntimeEndpointsResponse:
        """Get endpoints for a specific runtime."""
        logger.info(
            f"Getting endpoints for runtime {runtime_id} ({vendor.value}, setting={setting_id}, per_page={per_page})"
        )
        endpoints = self.vendor_runtime_service.get_endpoints(
            vendor=vendor,
            runtime_id=runtime_id,
            setting_id=setting_id,
            per_page=per_page,
            next_token=next_token,
        )
        logger.info(
            f"Retrieved {len(endpoints.data)} endpoints for runtime {runtime_id}"
        )
        return endpoints

    def get_prepared_endpoint(
        self,
        endpoints: List[VendorRuntimeEndpoint],
    ) -> Optional[VendorRuntimeEndpoint]:
        """Get first PREPARED endpoint from the list."""
        return next(
            (e for e in endpoints if e.status == VendorRuntimeEndpointStatus.PREPARED),
            endpoints[0] if endpoints else None,
        )

    def get_endpoint(
        self,
        vendor: VendorType,
        runtime_id: str,
        endpoint_name: str,
        setting_id: str,
    ) -> VendorRuntimeEndpointDetail:
        """Get detail for a specific runtime endpoint by name."""
        logger.info(
            f"Getting endpoint detail for '{endpoint_name}' "
            f"(runtime={runtime_id}, {vendor.value}, setting={setting_id})"
        )
        endpoint = self.vendor_runtime_service.get_endpoint(
            vendor=vendor,
            runtime_id=runtime_id,
            endpoint_name=endpoint_name,
            setting_id=setting_id,
        )
        logger.info(
            f"Retrieved endpoint detail: {endpoint.name} (status: {endpoint.status})"
        )
        return endpoint

    def get_imported_endpoint(
        self,
        endpoints: List[VendorRuntimeEndpoint],
    ) -> Optional[VendorRuntimeEndpoint]:
        """Get first endpoint that has already been imported into CodeMie (aiRunId is not None)."""
        return next((e for e in endpoints if e.aiRunId is not None), None)

    def find_first_unimported_endpoint(
        self,
        endpoints: List[VendorRuntimeEndpoint],
    ) -> Optional[VendorRuntimeEndpoint]:
        """Get first PREPARED endpoint that has not yet been imported into CodeMie."""
        return next(
            (
                e
                for e in endpoints
                if e.aiRunId is None
                and e.status == VendorRuntimeEndpointStatus.PREPARED
            ),
            None,
        )

    def install_endpoint_with_config(
        self,
        vendor: VendorType,
        runtime_id: str,
        endpoint_name: str,
        setting_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        message_path: str = "message",
        streaming: bool = False,
        text_path: Optional[str] = None,
        chunk_text_path: Optional[str] = None,
        extra_payload: Optional[dict] = None,
        thoughts_path: Optional[dict] = None,
        thought_text_path: Optional[str] = None,
        thought_name_path: Optional[str] = None,
        thought_args_path: Optional[str] = None,
        thought_active_path: Optional[str] = None,
        history_path: Optional[str] = None,
        history_role_path: str = "role",
        history_message_path: str = "content",
        history_user_role: str = "user",
        history_assistant_role: str = "assistant",
    ) -> VendorRuntimeInstallSummary:
        """Install endpoint with new structured configuration_json format."""
        request_block: dict = {"message_path": message_path}
        if extra_payload is not None:
            request_block["extra_payload"] = extra_payload
        if history_path is not None:
            request_block["history"] = {
                "history_path": history_path,
                "role_path": history_role_path,
                "message_path": history_message_path,
                "user_role": history_user_role,
                "assistant_role": history_assistant_role,
            }

        reasoning: dict = {}
        if thoughts_path:
            reasoning["thoughts_path"] = thoughts_path
        if thought_text_path:
            reasoning["text_path"] = thought_text_path
        if thought_name_path:
            reasoning["name_path"] = thought_name_path
        if thought_args_path:
            reasoning["args_path"] = thought_args_path
        if thought_active_path:
            reasoning["active_path"] = thought_active_path

        response_block: dict = {"streaming": streaming}
        if streaming:
            chunk: dict = {}
            if chunk_text_path:
                chunk["text_path"] = chunk_text_path
            if reasoning:
                chunk["reasoning"] = reasoning
            if chunk:
                response_block["chunk"] = chunk
        else:
            body: dict = {}
            if text_path:
                body["text_path"] = text_path
            if reasoning:
                body["reasoning"] = reasoning
            if body:
                response_block["body"] = body

        config = {"request": request_block, "response": response_block}

        logger.info(
            f"Installing endpoint '{endpoint_name}' with structured config "
            f"(streaming={streaming}, runtime={runtime_id}, setting={setting_id})"
        )
        request = VendorRuntimeInstallRequest(
            id=runtime_id,
            agentcoreRuntimeEndpointName=endpoint_name,
            setting_id=setting_id,
            configuration_json=json.dumps(config),
            assistant_name=name,
            assistant_description=description,
        )
        response = self.vendor_runtime_service.install_endpoints(
            vendor=vendor, endpoints=[request]
        )
        summary = response.summary[0]
        logger.info(
            f"Installed endpoint '{endpoint_name}' with structured config: aiRunId={summary.aiRunId}"
        )
        return summary

    def uninstall_endpoint(
        self,
        vendor: VendorType,
        ai_run_id: str,
    ) -> VendorRuntimeUninstallResponse:
        """Uninstall a runtime endpoint by its CodeMie ai_run_id."""
        logger.info(f"Uninstalling endpoint aiRunId={ai_run_id} ({vendor.value})")
        response = self.vendor_runtime_service.uninstall_endpoint(
            vendor=vendor, ai_run_id=ai_run_id
        )
        logger.info(f"Uninstall success={response.success}")
        return response

    def find_setting_for_integration(
        self,
        vendor: VendorType,
        integration_id: str,
    ):
        """Find runtime setting for an integration by paginating through all settings."""
        page = 0
        per_page = 50

        while True:
            settings_response = self.get_runtime_settings(
                vendor=vendor,
                page=page,
                per_page=per_page,
            )

            for s in settings_response.data:
                if s.setting_id == integration_id:
                    return s

            if page >= settings_response.pagination.pages - 1:
                break

            page += 1

        logger.warning(f"Setting not found for integration ID '{integration_id}'")
        return None
