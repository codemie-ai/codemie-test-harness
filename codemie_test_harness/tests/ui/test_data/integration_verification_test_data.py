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

from dataclasses import dataclass

from codemie_test_harness.tests.utils.base_utils import get_random_name


@dataclass
class IntegrationVerificationAssistantData:
    """Test data for integration verification test."""

    name: str
    description: str
    system_instructions: str
    toolkit_category: str
    tool_name: str


def get_integration_verification_assistant_data() -> (
    IntegrationVerificationAssistantData
):
    """Get test data for missing integrations validation dialog test.

    Returns:
        IntegrationVerificationAssistantData with test assistant configuration
    """
    return IntegrationVerificationAssistantData(
        name=f"Test Integration Validation {get_random_name()}",
        description="Assistant for testing integration validation dialog",
        system_instructions="You are a test assistant for integration validation",
        toolkit_category="Quality Assurance",
        tool_name="Xray Get Tests",
    )
