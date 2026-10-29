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

"""Constants for LLM output responses."""

from dataclasses import dataclass
from typing import List
from codemie_test_harness.tests.enums.model_types import ModelTypes
from codemie_test_harness.tests.enums.environment import Environment


@dataclass
class LlmResponseData:
    """Data class to store LLM model response information."""

    model_type: ModelTypes
    environments: List[Environment]


# Define environment sets using centralized enum methods (type-safe enums)
AZURE_ENVS = Environment.get_azure_environments()
GCP_ENVS = Environment.get_gcp_environments()
AWS_ENVS = Environment.get_aws_environments()
OTHER_ENVS = [
    Environment.PREVIEW,
    Environment.OSS_PREVIEW,
    Environment.LOCALHOST,
    Environment.PRODUCTION,
]
DIAL_ENVS = [Environment.PREVIEW]
# Fable models are not deployed on production
AWS_ENVS_NO_PROD = [env for env in AWS_ENVS if env != Environment.PRODUCTION]

# Define model responses with their environment restrictions
MODEL_RESPONSES = [
    # Azure LLMs test data
    LlmResponseData(ModelTypes.GPT_41, AZURE_ENVS),
    LlmResponseData(ModelTypes.GPT_41_MINI, AZURE_ENVS),
    LlmResponseData(ModelTypes.O3_MINI, AZURE_ENVS),
    LlmResponseData(ModelTypes.O3_2025_04_16, AZURE_ENVS),
    LlmResponseData(ModelTypes.O4_MINI_2025_04_16, AZURE_ENVS),
    LlmResponseData(ModelTypes.O1, AZURE_ENVS),
    LlmResponseData(ModelTypes.GPT_5_2025_08_07, AZURE_ENVS),
    LlmResponseData(ModelTypes.GPT_5_MINI_2025_08_07, AZURE_ENVS),
    LlmResponseData(ModelTypes.GPT_5_NANO_2025_08_07, AZURE_ENVS),
    LlmResponseData(ModelTypes.GPT_5_2_2025_12_11, AZURE_ENVS),
    LlmResponseData(ModelTypes.GPT_5_4_2026_03_05, AZURE_ENVS),
    LlmResponseData(ModelTypes.GPT_5_5_2026_04_24, AZURE_ENVS),
    LlmResponseData(ModelTypes.GPT_5_6_LUNA_2026_07_09, AZURE_ENVS),
    LlmResponseData(ModelTypes.GPT_5_6_SOL_2026_07_09, AZURE_ENVS),
    LlmResponseData(ModelTypes.GPT_5_6_TERRA_2026_07_09, AZURE_ENVS),
    LlmResponseData(ModelTypes.GPT_6_LUNA, AZURE_ENVS),
    LlmResponseData(ModelTypes.GPT_6_SOL, AZURE_ENVS),
    LlmResponseData(ModelTypes.GPT_6_1_SOL, AZURE_ENVS),
    # GCP LLMs test data
    LlmResponseData(ModelTypes.CLAUDE_SONNET_4_5_VERTEX, GCP_ENVS),
    LlmResponseData(ModelTypes.GEMINI_3_FLASH, GCP_ENVS),
    LlmResponseData(ModelTypes.GEMINI_3_5_FLASH, GCP_ENVS),
    LlmResponseData(ModelTypes.GEMINI_3_6_FLASH, GCP_ENVS),
    LlmResponseData(ModelTypes.GEMINI_3_7_FLASH, GCP_ENVS),
    LlmResponseData(ModelTypes.GEMINI_3_8_FLASH, GCP_ENVS),
    LlmResponseData(ModelTypes.GEMINI_4_ARGON, GCP_ENVS),
    LlmResponseData(ModelTypes.GEMINI_31_PRO, GCP_ENVS),
    LlmResponseData(ModelTypes.CLAUDE_SONNET_4_6_VERTEX, GCP_ENVS),
    LlmResponseData(ModelTypes.CLAUDE_OPUS_4_6_VERTEX, GCP_ENVS),
    # Bedrock LLMs test data
    LlmResponseData(ModelTypes.CLAUDE_SONNET_4_5_20250929, AWS_ENVS),
    LlmResponseData(ModelTypes.CLAUDE_4_5_SONNET, AWS_ENVS),
    LlmResponseData(ModelTypes.CLAUDE_4_5_HAIKU, AWS_ENVS),
    LlmResponseData(ModelTypes.CLAUDE_5_5_HAIKU, AWS_ENVS),
    LlmResponseData(ModelTypes.CLAUDE_4_5_OPUS, AWS_ENVS),
    LlmResponseData(ModelTypes.CLAUDE_4_6_OPUS, AWS_ENVS),
    LlmResponseData(ModelTypes.CLAUDE_4_7_OPUS, AWS_ENVS),
    LlmResponseData(ModelTypes.CLAUDE_4_8_OPUS, AWS_ENVS),
    LlmResponseData(ModelTypes.CLAUDE_4_6_SONNET, AWS_ENVS),
    LlmResponseData(ModelTypes.CLAUDE_5_SONNET, AWS_ENVS),
    LlmResponseData(ModelTypes.CLAUDE_5_OPUS, AWS_ENVS),
    # LlmResponseData(ModelTypes.CLAUDE_FABLE_5, AWS_ENVS_NO_PROD),
    # LlmResponseData(ModelTypes.CLAUDE_FABLE_5_1, AWS_ENVS_NO_PROD),
    LlmResponseData(ModelTypes.CLAUDE_5_5_OPUS, AWS_ENVS),
    LlmResponseData(ModelTypes.KIMI_K3, AWS_ENVS_NO_PROD),
    LlmResponseData(ModelTypes.CLAUDE_5_5_SONNET, AWS_ENVS),
    # Other LLMs test data
    LlmResponseData(ModelTypes.DEEPSEEK_V4_PRO, OTHER_ENVS),
    LlmResponseData(ModelTypes.GROK_4_6, OTHER_ENVS),
    # DIAL Gateway PoC LLMs test data
    LlmResponseData(ModelTypes.GPT_5_2_2025_12_11_DIAL, DIAL_ENVS),
    LlmResponseData(ModelTypes.GPT_5_4_2026_03_05_DIAL, DIAL_ENVS),
    LlmResponseData(ModelTypes.GPT_5_5_2026_04_24_DIAL, DIAL_ENVS),
    LlmResponseData(ModelTypes.GPT_5_6_LUNA_2026_07_09_DIAL, DIAL_ENVS),
    LlmResponseData(ModelTypes.GPT_5_6_SOL_2026_07_09_DIAL, DIAL_ENVS),
    LlmResponseData(ModelTypes.GPT_5_6_TERRA_2026_07_09_DIAL, DIAL_ENVS),
    LlmResponseData(ModelTypes.CLAUDE_4_6_SONNET_DIAL, DIAL_ENVS),
    LlmResponseData(ModelTypes.CLAUDE_5_SONNET_DIAL, DIAL_ENVS),
    LlmResponseData(ModelTypes.CLAUDE_4_8_OPUS_DIAL, DIAL_ENVS),
    LlmResponseData(ModelTypes.CLAUDE_5_OPUS_DIAL, DIAL_ENVS),
    LlmResponseData(ModelTypes.CLAUDE_4_5_HAIKU_DIAL, DIAL_ENVS),
]

SKIP_TOP_P_MODELS = {
    ModelTypes.CLAUDE_4_7_OPUS,
    ModelTypes.CLAUDE_4_8_OPUS,
    ModelTypes.CLAUDE_5_SONNET,
    ModelTypes.CLAUDE_5_OPUS,
    ModelTypes.GPT_5_5_2026_04_24,
    ModelTypes.GPT_5_6_LUNA_2026_07_09,
    ModelTypes.GPT_5_6_SOL_2026_07_09,
    ModelTypes.GPT_5_6_TERRA_2026_07_09,
    ModelTypes.GROK_4_6,
    ModelTypes.GPT_6_LUNA,
    ModelTypes.GPT_6_SOL,
    # DIAL Gateway PoC counterparts of the models above
    ModelTypes.CLAUDE_4_8_OPUS_DIAL,
    ModelTypes.CLAUDE_5_SONNET_DIAL,
    ModelTypes.CLAUDE_5_OPUS_DIAL,
    ModelTypes.GPT_5_5_2026_04_24_DIAL,
    ModelTypes.GPT_5_6_LUNA_2026_07_09_DIAL,
    ModelTypes.GPT_5_6_SOL_2026_07_09_DIAL,
    ModelTypes.GPT_5_6_TERRA_2026_07_09_DIAL,
}

SKIP_TEMPERATURE_MODELS = {
    ModelTypes.CLAUDE_4_7_OPUS,
    ModelTypes.CLAUDE_4_8_OPUS,
    ModelTypes.CLAUDE_5_SONNET,
    ModelTypes.CLAUDE_5_OPUS,
    ModelTypes.GROK_4_6,
    # DIAL Gateway PoC counterparts of the models above
    ModelTypes.CLAUDE_4_8_OPUS_DIAL,
    ModelTypes.CLAUDE_5_SONNET_DIAL,
    ModelTypes.CLAUDE_5_OPUS_DIAL,
    ModelTypes.GPT_6_LUNA,
    ModelTypes.GPT_6_SOL,
}
