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

"""Test data for 3rd party vendor assistant tests."""

import pytest
from codemie_sdk.models.vendor_assistant import VendorType
from codemie_sdk.models.integration import CredentialTypes

from codemie_test_harness.tests.llm.assistants.test_llm import SIMPLE_GREETING_PROMPT
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


# Test data for vendor assistant tests
# Extensible for AWS Bedrock, Azure AI, and GCP Vertex AI
vendor_assistant_test_data = [
    pytest.param(
        VendorType.AWS,
        CredentialTypes.AWS,
        CredentialsManager.aws_credentials(),
        SIMPLE_GREETING_PROMPT,
        "Hello",
        marks=[pytest.mark.aws, pytest.mark.bedrock],
        id="AWS_Bedrock",
    ),
    # Future: Azure AI assistants
    # pytest.param(
    #     VendorType.AZURE,
    #     CredentialTypes.AZURE,
    #     CredentialsManager.azure_credentials(),
    #     "Just say one word: 'Hello'",
    #     "Hello",
    #     marks=[pytest.mark.vendor, pytest.mark.azure, pytest.mark.api],
    #     id="Azure_AI",
    # ),
    # Future: GCP Vertex AI assistants
    # pytest.param(
    #     VendorType.GCP,
    #     CredentialTypes.GCP,
    #     CredentialsManager.gcp_credentials(),
    #     "Just say one word: 'Hello'",
    #     "Hello",
    #     marks=[pytest.mark.vendor, pytest.mark.gcp, pytest.mark.api],
    #     id="GCP_Vertex_AI",
    # ),
]
