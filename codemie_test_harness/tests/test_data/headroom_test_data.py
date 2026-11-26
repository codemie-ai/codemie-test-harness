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

"""Configs, messages and expected values for the Headroom (context compression) tests."""

import json
import re
from dataclasses import dataclass

import yaml
from codemie_sdk import HeadroomConfig, HeadroomStrategy
from codemie_sdk.models.assistant import ToolDetails, ToolKitDetails

from codemie_test_harness.tests.enums.tools import PlatformTool, Toolkit
from codemie_test_harness.tests.test_data.workflow_validation_messages import (
    INVALID_YAML_PROVIDED,
)

# ---------------------------------------------------------------------------------------------
# Assistant and workflow configs
# ---------------------------------------------------------------------------------------------

# Every update sends all four fields: the backend fills defaults into the fields a config
# leaves out, so a partial update would also reset the ones it does not name.
ASSISTANT_HEADROOM_AGGRESSIVE = HeadroomConfig(
    enabled=True,
    compress_user_messages=False,
    compress_tool_outputs=True,
    strategy=HeadroomStrategy.AGGRESSIVE,
)
ASSISTANT_HEADROOM_LOSSLESS = ASSISTANT_HEADROOM_AGGRESSIVE.model_copy(
    update={"strategy": HeadroomStrategy.LOSSLESS}
)

# Compression on with the aggressive strategy, the one the live probe saved tokens with.
CHAT_HEADROOM_AGGRESSIVE = HeadroomConfig(
    enabled=True,
    compress_user_messages=True,
    compress_tool_outputs=True,
    strategy=HeadroomStrategy.AGGRESSIVE,
)


def chat_headroom(strategy: HeadroomStrategy) -> HeadroomConfig:
    """Compression on for user input and tool outputs with the given strategy."""
    return CHAT_HEADROOM_AGGRESSIVE.model_copy(update={"strategy": strategy})


# Top-level ``headroom:`` blocks of a workflow YAML (schema $defs.HeadroomOverride).
WORKFLOW_HEADROOM_BALANCED = {"enabled": True, "strategy": "balanced"}
WORKFLOW_HEADROOM_AGGRESSIVE = {"enabled": True, "strategy": "aggressive"}


def workflow_headroom(strategy: HeadroomStrategy) -> dict:
    """Top-level ``headroom:`` block that turns compression on with the given strategy."""
    return {"enabled": True, "strategy": strategy.value}


# ---------------------------------------------------------------------------------------------
# Invalid values
# ---------------------------------------------------------------------------------------------

UNKNOWN_STRATEGY = "turbo"


def assistant_headroom_with_unknown_strategy() -> HeadroomConfig:
    """A config whose strategy is outside the enum.

    Built with ``model_construct`` so the SDK model does not reject the value before it
    reaches the backend, which is what the test checks.
    """
    return HeadroomConfig.model_construct(
        enabled=True,
        compress_user_messages=True,
        compress_tool_outputs=True,
        strategy=UNKNOWN_STRATEGY,
    )


# Backend request validation (rest_api/main.py, _validation_error_details) reports
# "<field path without 'body'>: <pydantic message>" in error.message, with status 422.
ASSISTANT_INVALID_STATUS = 422
ASSISTANT_INVALID_STRATEGY_FIELD = "headroom_config.strategy"

# Workflow configuration errors are a 400 (routers/workflow.py, _wrap_validation_errors).
# A schema error reads "In '<path>': config does not conform to the required schema"
# (workflows/validation/schema.py, _format_validation_error_message): enum and
# additionalProperties have no dedicated wording.
WORKFLOW_INVALID_STATUS = 400
SCHEMA_NOT_CONFORMING = "config does not conform to the required schema"


@dataclass(frozen=True)
class InvalidWorkflowHeadroom:
    headroom: dict
    expected_message: str


INVALID_WORKFLOW_HEADROOM = {
    "unknown_strategy": InvalidWorkflowHeadroom(
        headroom={"enabled": True, "strategy": UNKNOWN_STRATEGY},
        expected_message=(
            f"{INVALID_YAML_PROVIDED} 1) In 'headroom.strategy': {SCHEMA_NOT_CONFORMING}"
        ),
    ),
    "unknown_key": InvalidWorkflowHeadroom(
        headroom={"enabled": True, "compress_everything": True},
        expected_message=f"{INVALID_YAML_PROVIDED} 1) In 'headroom': {SCHEMA_NOT_CONFORMING}",
    ),
}


def clean_workflow_error_details(details: str) -> str:
    """The error details as the config-validation tests compare them: no <br>, single spaces."""
    return re.sub(r" {2,}", " ", details.replace("<br>", " ")).strip()


def workflow_yaml_with_headroom(model: str, headroom: dict) -> str:
    """A one-assistant workflow YAML with the given top-level ``headroom`` block."""
    return yaml.safe_dump(
        {
            "headroom": headroom,
            "assistants": [
                {
                    "id": "headroom_assistant",
                    "model": model,
                    "system_prompt": "You are a helpful assistant.",
                }
            ],
            "states": [
                {
                    "id": "headroom_assistant",
                    "assistant_id": "headroom_assistant",
                    "next": {"state_id": "end"},
                }
            ],
        },
        sort_keys=False,
    )


# ---------------------------------------------------------------------------------------------
# Compression runs
# ---------------------------------------------------------------------------------------------

# Headroom skips input under HEADROOM_MIN_TOKENS (1000). The live probe saved about 10k
# tokens on a ~28k-character repetitive log with the aggressive strategy; this builds one
# of the same size and shape.
LOG_LINE_COUNT = 300


def repetitive_log_prompt() -> str:
    """A user message well above 1000 tokens: a repetitive service log to summarise."""
    lines = [
        f"2026-01-01T10:{i // 60:02d}:{i % 60:02d}Z INFO worker-{i % 4} "
        f"processed batch {i % 10} status=OK latency_ms=12 queue=default retries=0"
        for i in range(LOG_LINE_COUNT)
    ]
    return "Summarise this service log in one sentence:\n" + "\n".join(lines)


# The lossless strategy compresses structured data only: it saves tokens when the user
# message is nothing but a pretty-printed JSON array (developer confirmation), and saved
# none on the repetitive log above.
JSON_RECORD_COUNT = 60


def json_array_prompt() -> str:
    """A user message that is only a pretty-printed JSON array of 60 user records."""
    records = [
        {
            "id": i,
            "name": f"user-{i}",
            "email": f"user{i}@example.com",
            "status": "active" if i % 2 == 0 else "inactive",
            "score": (i * 37) % 101,
        }
        for i in range(JSON_RECORD_COUNT)
    ]
    return json.dumps(records, indent=2)


# Workflow node task that hands the long input to the assistant.
WORKFLOW_TASK = "Summarise the user input in one sentence."

# ---------------------------------------------------------------------------------------------
# Compress user input / Compress tool outputs flags
# ---------------------------------------------------------------------------------------------

# Only a HumanMessage (compress_user_messages) or a ToolMessage (compress_tool_outputs)
# may take compressed text; system prompts and assistant replies never do
# (service/headroom/hook.py, _is_compressible). All four fields are always sent.
HEADROOM_USER_INPUT_ONLY = HeadroomConfig(
    enabled=True,
    compress_user_messages=True,
    compress_tool_outputs=False,
    strategy=HeadroomStrategy.AGGRESSIVE,
)
HEADROOM_TOOL_OUTPUTS_ONLY = HeadroomConfig(
    enabled=True,
    compress_user_messages=False,
    compress_tool_outputs=True,
    strategy=HeadroomStrategy.AGGRESSIVE,
)

# get_assistants (Platform Tools) returns a large tool output - 20 assistants with their
# details - from a short user message (developer confirmation; the code executor was
# unsuitable: the stand's validator rejected the code the model passed).
GET_ASSISTANTS_TOOLKITS = [
    ToolKitDetails(
        toolkit=Toolkit.PLATFORM_TOOLS.value,
        tools=[ToolDetails(name=PlatformTool.GET_ASSISTANTS.value)],
    )
]
LARGE_TOOL_OUTPUT_PROMPT = (
    "Call get_assistants exactly once with scope 'visible_to_user', limit 20 and "
    "offset 0. Do not call any other tool. Then tell me how many of the returned "
    "assistants have a name starting with 'a', and list the first 5 names."
)
DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."


@dataclass(frozen=True)
class CompressFlagsScenario:
    """An assistant config and the chat that exercises one message kind."""

    headroom: HeadroomConfig
    system_prompt: str
    toolkits: list
    prompt: str
    # Tools the chat must have run (assert_tool_triggered): none for a plain message.
    expected_tools: tuple = ()


# The flag of the long message kind is on: Headroom saves tokens.
USER_INPUT_ON_LONG_USER_MESSAGE = CompressFlagsScenario(
    headroom=HEADROOM_USER_INPUT_ONLY,
    system_prompt=DEFAULT_SYSTEM_PROMPT,
    toolkits=[],
    prompt=repetitive_log_prompt(),
)
TOOL_OUTPUTS_ON_LARGE_TOOL_OUTPUT = CompressFlagsScenario(
    headroom=HEADROOM_TOOL_OUTPUTS_ONLY,
    system_prompt=DEFAULT_SYSTEM_PROMPT,
    toolkits=GET_ASSISTANTS_TOOLKITS,
    prompt=LARGE_TOOL_OUTPUT_PROMPT,
    expected_tools=(PlatformTool.GET_ASSISTANTS,),
)
# The flag of the long message kind is off: nothing is compressed.
USER_INPUT_OFF_LONG_USER_MESSAGE = CompressFlagsScenario(
    headroom=HEADROOM_TOOL_OUTPUTS_ONLY,
    system_prompt=DEFAULT_SYSTEM_PROMPT,
    toolkits=[],
    prompt=repetitive_log_prompt(),
)
TOOL_OUTPUTS_OFF_LARGE_TOOL_OUTPUT = CompressFlagsScenario(
    headroom=HEADROOM_USER_INPUT_ONLY,
    system_prompt=DEFAULT_SYSTEM_PROMPT,
    toolkits=GET_ASSISTANTS_TOOLKITS,
    prompt=LARGE_TOOL_OUTPUT_PROMPT,
    expected_tools=(PlatformTool.GET_ASSISTANTS,),
)

# How long a chat with nothing to compress is watched for savings. The live probe saw a
# compressed chat's metrics at once and none for an uncompressed one within 30 s.
NO_SAVINGS_WINDOW = 30

# Analytics ingestion of a compression event took under 20 s in the live probe.
ANALYTICS_POLL_TIMEOUT = 90
METRICS_POLL_TIMEOUT = 60
# Summary ingestion of one chat's compression event (the live probe saw it under 20 s).
SUMMARY_POLL_TIMEOUT = 60
POLL_INTERVAL = 5

# ---------------------------------------------------------------------------------------------
# Analytics shape (service/analytics/handlers/headroom_handler.py)
# ---------------------------------------------------------------------------------------------

# Modes the summary can report once the period holds Headroom events: one of sdk or
# sidecar (HEADROOM_MODE of the stand), or mixed when the period saw both
# (headroom_handler.py, _active_mode).
HEADROOM_MODES = ["sdk", "sidecar", "mixed"]

SUMMARY_METRIC_IDS = [
    "tokens_original",
    "tokens_compacted",
    "tokens_saved",
    "saved_percent",
    "request_count",
    "session_count",
]
BY_STRATEGY_COLUMN_IDS = [
    "strategy",
    "request_count",
    "tokens_original",
    "tokens_compacted",
    "tokens_saved",
    "saved_percent",
]
TIMESERIES_COLUMN_IDS = [
    "time",
    "request_count",
    "tokens_original",
    "tokens_compacted",
    "tokens_saved",
]


def strategy_metric(response, strategy: HeadroomStrategy, column: str) -> int:
    """One column of the by-strategy row of ``strategy``; 0 while the strategy has no row.

    Rows are keyed by the strategy value (headroom_handler.py, _parse_terms_result).
    """
    for row in response.data.rows:
        if row.get("strategy") == strategy.value:
            return row.get(column) or 0
    return 0


def workflows_with_ids(workflows, ids) -> dict:
    """Workflows of a list response keyed by id, only those whose id is in ``ids``."""
    return {workflow.id: workflow for workflow in workflows if workflow.id in ids}


def summary_metric(response, metric_id: str) -> int:
    """Value of one numeric metric of a Headroom summary response; 0 when it is absent.

    Coalesces like ``strategy_metric``: an empty period may omit a metric or carry None.
    """
    for metric in response.data.metrics:
        if metric.id == metric_id:
            return metric.value or 0
    return 0
