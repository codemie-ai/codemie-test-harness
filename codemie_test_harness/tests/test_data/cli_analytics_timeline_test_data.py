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

"""Synthetic hooks for a Copilot session with overlapping subagents and a skill."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    CliSessionSeed,
    to_iso,
)


@dataclass
class HooksOnlyTimelineSeed(CliSessionSeed):
    """One priced Copilot agent, an overlapping agent without usage, and a tool skill."""

    agent_input_tokens: int = 1500
    agent_output_tokens: int = 60

    def events(self, project_name: str) -> list[dict]:
        events = super().events(project_name)
        main_usage = next(
            event for event in events if event["type"] == "agent.usage.request"
        )
        envelope = {
            "session_id": self.session_id,
            "schema_version": 2,
            "codemie_project_name": project_name,
        }

        def hook(event_type: str, offset_s: int, suffix: str, **fields: object) -> dict:
            return {
                **envelope,
                **fields,
                "type": event_type,
                "event_id": f"{self.session_id}:{suffix}",
                "timestamp": to_iso(self.started_at + timedelta(seconds=offset_s), 0),
            }

        priced_agent = {"agent_id": "agent-priced", "agent_type": "file-auditor"}
        idle_agent = {**priced_agent, "agent_id": "agent-idle"}
        skill = {
            "tool_use_id": "skill-tool",
            "tool_name": "skill",
            "skill_name": "timeline-check",
        }
        events.extend(
            [
                hook("agent.subagent.start", 1, "priced-start", **priced_agent),
                hook("agent.subagent.start", 2, "idle-start", **idle_agent),
                hook("agent.tool.start", 3, "skill-start", **skill),
                hook("agent.tool.end", 4, "skill-end", **skill),
                {
                    **main_usage,
                    "agent_id": priced_agent["agent_id"],
                    "event_id": f"{self.session_id}:agent-usage",
                    "request_id": f"{self.session_id}:agent-request",
                    "message_id": f"{self.session_id}:agent-message",
                    "timestamp": to_iso(self.started_at + timedelta(seconds=5), 0),
                    "scope_kind": "agent",
                    "input_tokens": self.agent_input_tokens,
                    "output_tokens": self.agent_output_tokens,
                },
                hook("agent.subagent.stop", 6, "priced-stop", **priced_agent),
                hook("agent.subagent.stop", 7, "idle-stop", **idle_agent),
            ]
        )
        return [
            {**event, "platform": "copilot-cli"}
            for event in sorted(events, key=lambda event: event["timestamp"])
        ]


def get_hooks_only_timeline_seed(model: str) -> HooksOnlyTimelineSeed:
    return HooksOnlyTimelineSeed(
        key="hooks_only_timeline",
        started_at=datetime.now(timezone.utc).replace(microsecond=0)
        - timedelta(minutes=1),
        duration=timedelta(seconds=10),
        model=model,
        input_tokens=3200,
        output_tokens=90,
    )
