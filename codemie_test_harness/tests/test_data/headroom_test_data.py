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

import re
from dataclasses import dataclass

import yaml
from codemie_sdk import HeadroomConfig, HeadroomStrategy

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

# Top-level ``headroom:`` blocks of a workflow YAML (schema $defs.HeadroomOverride).
WORKFLOW_HEADROOM_BALANCED = {"enabled": True, "strategy": "balanced"}
WORKFLOW_HEADROOM_AGGRESSIVE = {"enabled": True, "strategy": "aggressive"}

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


# Workflow node task that hands the long input to the assistant.
WORKFLOW_TASK = "Summarise the user input in one sentence."

# Analytics ingestion of a compression event took under 20 s in the live probe.
ANALYTICS_POLL_TIMEOUT = 90
METRICS_POLL_TIMEOUT = 60
# Summary ingestion of one chat's compression event (the live probe saw it under 20 s).
SUMMARY_POLL_TIMEOUT = 60
POLL_INTERVAL = 5

# ---------------------------------------------------------------------------------------------
# Analytics shape (service/analytics/handlers/headroom_handler.py)
# ---------------------------------------------------------------------------------------------

# Mode the summary reports once the period holds Headroom events: the backend sets one of
# sdk, sidecar or mixed (headroom_handler.py, _active_mode). The target stand runs the
# in-process SDK; the live probe's summary read "sdk".
EXPECTED_HEADROOM_MODE = "sdk"

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


def workflows_with_ids(workflows, ids) -> dict:
    """Workflows of a list response keyed by id, only those whose id is in ``ids``."""
    return {workflow.id: workflow for workflow in workflows if workflow.id in ids}


def summary_metric(response, metric_id: str):
    """Value of one metric of a Headroom summary response, or None when it is absent."""
    for metric in response.data.metrics:
        if metric.id == metric_id:
            return metric.value
    return None
