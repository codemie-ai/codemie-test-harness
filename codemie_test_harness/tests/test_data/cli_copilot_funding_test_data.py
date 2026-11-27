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

"""GitHub Copilot CLI sessions for the funding checks.

A session launched with `codemie-copilot --profile <CodeMie profile>` sends its model requests
through the CodeMie proxy. When the CLI can prove that route it sends the session's analytics
with the same evidence as a managed Claude Code session: routed via CodeMie, subscription type
codemie, the launch profile's project, and the api_based funding claim of publication contract
1. A native `copilot` session has none of that and is sent with the project header only.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    CliSessionSeed,
)

COPILOT_PLATFORM = "copilot-cli"
MANAGED = "managed"  # codemie-copilot, routed through the CodeMie proxy
NATIVE = "native"  # copilot on its own

CODEMIE = "codemie"
UNKNOWN = "unknown"
PROFILE = "profile"
NO_ORIGIN = "none"
API_BASED = "api_based"

# subscription_type and project_origin each session must be stored with
EXPECTED_CLASSES = {
    MANAGED: {"subscription_type": CODEMIE, "project_origin": PROFILE},
    NATIVE: {"subscription_type": UNKNOWN, "project_origin": NO_ORIGIN},
}


@dataclass
class CopilotSessionSeed(CliSessionSeed):
    """A Copilot CLI hooks-only session: every event names the Copilot platform and how the
    session was launched, as the CLI's Copilot hooks write them."""

    entrypoint: str = NATIVE

    def events(self, project_name: str) -> list[dict]:
        return [
            {**event, "platform": COPILOT_PLATFORM, "entrypoint": self.entrypoint}
            for event in super().events(project_name)
        ]


def managed_copilot_headers(session_id: str) -> dict:
    """The headers the CLI adds to every analytics batch of a codemie-copilot session whose
    route through CodeMie it proved (the CLI's `evidenceHeaders` in contract mode).
    X-CodeMie-Project is sent by the ingest call itself."""
    return {
        "X-CodeMie-Session-Id": session_id,
        "X-CodeMie-Routed-Via-CodeMie": "true",
        "X-CodeMie-Subscription-Type": CODEMIE,
        "X-CodeMie-Project-Source": PROFILE,
        "X-CodeMie-Publication-Contract": "1",
        "X-CodeMie-Funding-Route": API_BASED,
    }


def get_copilot_funding_seeds(model: str) -> dict[str, CopilotSessionSeed]:
    """A managed and a native Copilot session of `model`, keyed by entrypoint. Their token
    counts differ, so each funding bucket's cost tells which session it holds."""
    started_at = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(
        minutes=1
    )
    return {
        MANAGED: CopilotSessionSeed(
            key="copilot_managed",
            started_at=started_at,
            input_tokens=4200,
            output_tokens=120,
            model=model,
            entrypoint=MANAGED,
        ),
        NATIVE: CopilotSessionSeed(
            key="copilot_native",
            started_at=started_at,
            input_tokens=1700,
            output_tokens=40,
            model=model,
            entrypoint=NATIVE,
        ),
    }
