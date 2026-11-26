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

"""Test data for CLI Analytics Session Detail request costs: sessions whose listed
requests must add up to the session cost."""

from datetime import timedelta

from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    CliSessionSeed,
    seed_day_start,
)

# A Claude catalog name with an 8-digit date stamp: the form a Bedrock-style id wraps.
DATED_CLAUDE_MODEL = r"claude-[a-z0-9-]+-\d{8}"

# How Claude Code names a Bedrock model: the plain Bedrock id, and the same id behind
# LiteLLM's converse route with a cross-region prefix.
BEDROCK_ID_FORMS = {
    "bedrock": "anthropic.{model}-v1:0",
    "converse": "converse/global.anthropic.{model}-v1:0",
}


def get_hooks_only_requests_seed(model: str) -> CliSessionSeed:
    """Three requests reported by hooks only (no OTel record, as GitHub Copilot or
    Claude Code with telemetry off send them). Each reads from the prompt cache and
    writes to it for five minutes and for an hour."""
    return CliSessionSeed(
        key="hooks_only_requests",
        started_at=seed_day_start() + timedelta(hours=13),
        input_tokens=3_000,
        output_tokens=300,
        cache_read_tokens=30_000,
        cache_creation_5m_tokens=6_000,
        cache_creation_1h_tokens=21_000,
        requests=3,
        model=model,
    )


def get_one_hour_cache_write_seed(model: str) -> CliSessionSeed:
    """One request Claude Code reports twice, as with telemetry on: its OTel record,
    whose cache writes are one total, and the CLI's usage row, which says they are all
    one-hour writes (codemie-claude turns one-hour prompt caching on)."""
    return CliSessionSeed(
        key="one_hour_cache_write",
        started_at=seed_day_start() + timedelta(hours=14),
        input_tokens=1_000,
        output_tokens=100,
        cache_read_tokens=5_000,
        cache_creation_1h_tokens=20_000,
        cost_usd=0.0001,
        usage_row=True,
        model=model,
    )


def get_bedrock_id_seed(model: str, form: str) -> CliSessionSeed:
    """One request Claude Code reports with its cost under a Bedrock-style id of the
    catalog model ``model`` (Claude Desktop 3p and codemie-claude do so for Haiku). It
    reads from the prompt cache, so a request left unpriced loses its cache-read cost."""
    return CliSessionSeed(
        key=f"bedrock_id_{form}",
        started_at=seed_day_start() + timedelta(hours=15),
        input_tokens=1_000,
        output_tokens=200,
        cache_read_tokens=40_000,
        cost_usd=0.0001,
        model=BEDROCK_ID_FORMS[form].format(model=model),
    )
