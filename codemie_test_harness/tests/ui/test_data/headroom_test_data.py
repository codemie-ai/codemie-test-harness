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

"""UI labels and helpers for the Headroom (context compression) UI tests."""

import yaml
from codemie_sdk import HeadroomConfig, HeadroomStrategy

# Strategy option labels (codemie-ui HeadroomConfig.tsx STRATEGY_OPTIONS).
STRATEGY_LOSSLESS = "Lossless"
STRATEGY_BALANCED = "Balanced"
STRATEGY_AGGRESSIVE = "Aggressive"

# Form defaults while nothing is stored (HeadroomConfig.tsx DEFAULT_HEADROOM_CONFIG).
DEFAULT_STRATEGY = STRATEGY_BALANCED

# What the assistant form test saves, and the stored value it must produce.
FORM_HEADROOM_SAVED = HeadroomConfig(
    enabled=True,
    compress_user_messages=False,
    compress_tool_outputs=True,
    strategy=HeadroomStrategy.AGGRESSIVE,
)

# The same assistant edited to the opposite flags: user input on, tool outputs off.
FORM_HEADROOM_EDITED = FORM_HEADROOM_SAVED.model_copy(
    update={"compress_user_messages": True, "compress_tool_outputs": False}
)

# Analytics Insights tab: Headroom widgets and summary tiles (backend headroom_handler.py
# labels; the UI shows the tile labels in upper case).
HEADROOM_WIDGET_TITLES = [
    "Headroom Summary",
    "Savings Over Time",
    "Savings by Strategy",
]
HEADROOM_SUMMARY_TILE_LABELS = [
    "Original Tokens",
    "Compacted Tokens",
    "Tokens Saved",
    "Saved Share (%)",
    "Compacted Requests",
    "Unique Sessions",
]


def workflow_headroom_block(yaml_config: str) -> dict:
    """The top-level ``headroom`` block of a workflow YAML ({} when there is none)."""
    return yaml.safe_load(yaml_config).get("headroom") or {}


def assistant_node_headroom_block(yaml_config: str, assistant_id: str) -> dict:
    """The ``headroom`` block of one assistant of a workflow YAML ({} when there is none)."""
    assistants = yaml.safe_load(yaml_config).get("assistants") or []
    matching = [entry for entry in assistants if entry.get("id") == assistant_id]
    return (matching[0].get("headroom") if matching else None) or {}
