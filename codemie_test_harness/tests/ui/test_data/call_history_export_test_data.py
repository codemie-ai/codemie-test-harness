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

"""Test data for the call history export UI tests (Download and Copy in the Calls history popup)."""

import re

CALL_HISTORY_TITLE_PREFIX = "Calls history for "

DOWNLOAD_SUCCESS_TOAST = "Call history downloaded"
COPY_SUCCESS_TOAST = "Call history copied to clipboard"
COPY_UNAVAILABLE_TOAST = "Could not copy call history. Clipboard access is unavailable; use Download instead."

# Spaces per indentation level of the exported JSON (JSON.stringify(payload, null, 2)).
EXPORT_INDENT = 2

EXPORT_TOP_LEVEL_KEYS = frozenset(
    {
        "execution_id",
        "state_id",
        "node",
        "status",
        "started_at",
        "completed_at",
        "duration_seconds",
        "calls",
    }
)

# Keys of every call that are always serialised (the others are dropped when the call lacks them).
EXPORT_CALL_REQUIRED_KEYS = frozenset({"index", "id", "message", "content"})

EXPORT_CALL_KEYS = frozenset(
    {
        "index",
        "id",
        "author_name",
        "tool_name",
        "author_type",
        "input_text",
        "message",
        "error",
        "children",
        "content",
        "date",
    }
)

# Label of a call row in the popup when the call has neither author nor tool name.
DEFAULT_CALL_LABEL = "Tool"


def expected_call_history_filename(node_name: str, execution_id: str) -> str:
    """File name the Download action suggests: ``call-history-<node-slug>-<execution_id>.json``.

    The slug is the node name with every run of non-alphanumeric characters collapsed to ``-``,
    the leading and trailing ``-`` trimmed and lowercased; ``node`` when nothing is left.
    """
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", node_name or "node").strip("-").lower()
    return f"call-history-{slug or 'node'}-{execution_id}.json"
