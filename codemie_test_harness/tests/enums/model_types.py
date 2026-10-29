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

"""Enum representing LLM model types."""

from enum import Enum


class ModelTypes(str, Enum):
    """Enum representing different LLM model types."""

    # Azure
    GPT_41 = "gpt-4.1"
    GPT_41_MINI = "gpt-4.1-mini"
    O3_MINI = "o3-mini"
    O3_2025_04_16 = "o3-2025-04-16"
    O4_MINI_2025_04_16 = "o4-mini-2025-04-16"
    O1 = "o1"
    GPT_5_2025_08_07 = "gpt-5-2025-08-07"
    GPT_5_NANO_2025_08_07 = "gpt-5-nano-2025-08-07"
    GPT_5_MINI_2025_08_07 = "gpt-5-mini-2025-08-07"
    GPT_5_2_2025_12_11 = "gpt-5-2-2025-12-11"
    GPT_5_4_2026_03_05 = "gpt-5.4-2026-03-05"
    GPT_5_5_2026_04_24 = "gpt-5.5-2026-04-24"
    GPT_5_6_LUNA_2026_07_09 = "gpt-5.6-luna-2026-07-09"
    GPT_5_6_SOL_2026_07_09 = "gpt-5.6-sol-2026-07-09"
    GPT_5_6_TERRA_2026_07_09 = "gpt-5.6-terra-2026-07-09"
    GPT_6_LUNA = "gpt-6-luna"
    GPT_6_SOL = "gpt-6-sol"
    GPT_6_1_SOL = "gpt-6.1-sol"

    # GCP
    CLAUDE_SONNET_4_5_VERTEX = "claude-4-5-sonnet-vertex"
    GEMINI_3_FLASH = "gemini-3-flash"
    GEMINI_3_5_FLASH = "gemini-3.5-flash"
    GEMINI_3_6_FLASH = "gemini-3.6-flash"
    GEMINI_3_7_FLASH = "gemini-3.7-flash"
    GEMINI_3_8_FLASH = "gemini-3.8-flash"
    GEMINI_4_ARGON = "gemini-4-argon"
    GEMINI_31_PRO = "gemini-3.1-pro"
    CLAUDE_SONNET_4_6_VERTEX = "claude-sonnet-4-6-vertex"
    CLAUDE_OPUS_4_6_VERTEX = "claude-opus-4-6-vertex"

    # Bedrock
    KIMI_K3 = "moonshotai.kimi-k3"
    CLAUDE_SONNET_4_5_20250929 = "claude-sonnet-4-5-20250929"
    CLAUDE_4_5_SONNET = "claude-4-5-sonnet"
    CLAUDE_4_6_SONNET = "claude-sonnet-4-6"
    CLAUDE_4_5_OPUS = "claude-opus-4-5-20251101"
    CLAUDE_4_6_OPUS = "claude-opus-4-6-20260205"
    CLAUDE_4_7_OPUS = "claude-opus-4-7"
    CLAUDE_4_8_OPUS = "claude-opus-4-8"
    CLAUDE_4_5_HAIKU = "claude-haiku-4-5-20251001"
    CLAUDE_5_SONNET = "claude-sonnet-5"
    CLAUDE_5_OPUS = "claude-opus-5"
    CLAUDE_5_5_OPUS = "claude-opus-5-5"
    # CLAUDE_FABLE_5 = "claude-fable-5"
    # CLAUDE_FABLE_5_1 = "claude-fable-5-1"
    CLAUDE_5_5_SONNET = "claude-sonnet-5-5"
    CLAUDE_5_5_HAIKU = "claude-haiku-5-5"

    # Other
    DEEPSEEK_V4_PRO = "deepseek-v4-pro"
    GROK_4_6 = "grok-4.6"

    # DIAL Gateway (PoC)
    GPT_5_2_2025_12_11_DIAL = "gpt-5-2-2025-12-11-dial"
    GPT_5_4_2026_03_05_DIAL = "gpt-5.4-2026-03-05-dial"
    GPT_5_5_2026_04_24_DIAL = "gpt-5.5-2026-04-24-dial"
    GPT_5_6_LUNA_2026_07_09_DIAL = "gpt-5.6-luna-2026-07-09-dial"
    GPT_5_6_SOL_2026_07_09_DIAL = "gpt-5.6-sol-2026-07-09-dial"
    GPT_5_6_TERRA_2026_07_09_DIAL = "gpt-5.6-terra-2026-07-09-dial"
    CLAUDE_4_6_SONNET_DIAL = "claude-sonnet-4-6-dial"
    CLAUDE_5_SONNET_DIAL = "claude-sonnet-5-dial"
    CLAUDE_4_8_OPUS_DIAL = "claude-opus-4-8-dial"
    CLAUDE_5_OPUS_DIAL = "claude-opus-5-dial"
    CLAUDE_4_5_HAIKU_DIAL = "claude-haiku-4-5-20251001-dial"
