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

"""Test data for the CLI Analytics UI checks of incomplete cost pricing."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    CliSessionSeed,
    seed_day_start,
)

# Words the UI puts in the accessible name of the marker next to a cost value.
PARTIAL_ESTIMATE_NOTICE = (
    "Partial estimate. Model with missing pricing for some or all usage:"
)
COST_UNKNOWN_NOTICE = "Cost unknown. Model with missing pricing for some or all usage:"
# Descriptions under the "Avg Cost / Session" value of the Cost section.
AVG_COST_COMPLETE_NOTE = "Per session with cost"
AVG_COST_PARTIAL_NOTE = "Partial estimate"
AVG_COST_UNKNOWN_NOTE = "Cost unknown"
# What a cost value shows when no model of the selection has a price.
UNKNOWN_COST_VALUE = "-"

# Large enough that the priced cost is whole cents of a visible amount, not "$0.00".
SEED_INPUT_TOKENS = 2_000_000
SEED_OUTPUT_TOKENS = 100_000
SEED_REPOSITORY = "/work/autotest-cli-pricing-repo"
# The window the filters narrow the dashboard to: the seeded session's start, both ways.
WINDOW_MARGIN = timedelta(minutes=5)


def unpriced_model_name() -> str:
    """A model name no price catalog knows, unique so no catalog can ever price it."""
    return f"autotest-unpriced-{uuid.uuid4().hex[:8]}"


@dataclass(frozen=True)
class PricingSession:
    """One seeded CLI session (in a project of its own) and what the dashboard shows for it.

    ``priced_cost`` is the dashboard text of the cost the priced model contributes, None when
    no model of the session has a price. ``unpriced_model`` is the model without a catalog price,
    None when pricing is complete.
    """

    project: str
    session_id: str
    started_at: datetime
    priced_model: str | None
    priced_cost: str | None
    unpriced_model: str | None

    @property
    def window_start(self) -> datetime:
        return self.started_at - WINDOW_MARGIN

    @property
    def window_end(self) -> datetime:
        return self.started_at + WINDOW_MARGIN


def get_pricing_session_seeds(models: list[str]) -> list[CliSessionSeed]:
    """The events of one session that makes a request to each model: same session, same
    start, equal tokens per model, so every priced model adds the same amount."""
    session_id = f"autotest-cli-{uuid.uuid4().hex[:12]}"
    started_at = seed_day_start() + timedelta(hours=10)
    return [
        CliSessionSeed(
            key=model,
            started_at=started_at,
            input_tokens=SEED_INPUT_TOKENS,
            output_tokens=SEED_OUTPUT_TOKENS,
            repository=SEED_REPOSITORY,
            model=model,
            session_id=session_id,
        )
        for model in models
    ]
