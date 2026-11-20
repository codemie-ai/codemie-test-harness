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

"""Test data for CLI Analytics turn counting: Claude Code sessions with injected prompts."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    OWNER,
    SEED_MODEL,
    to_iso,
)

TYPED_PROMPT = "use an Explore subagent to list the files in this folder"
SUBAGENT_HAND_BACK_BODY = '<agent-message from="autotest-subagent-1"> [Subagent hand-back] The folder is empty.'
TYPED_INPUT_TOKENS = 1000
HAND_BACK_INPUT_TOKENS = 2000


@dataclass(frozen=True)
class InjectedPrompt:
    """A message Claude Code adds to the conversation on its own, as an interaction span.

    ``hook_body`` is the body of the agent.prompt.submit hook of the same prompt_id, or
    None when no hook arrives for it. ``answered`` is whether the model replied to it,
    that is, whether its span holds an api_request.
    """

    log_body: str
    hook_body: str | None
    answered: bool


HAND_BACK = InjectedPrompt(
    log_body=SUBAGENT_HAND_BACK_BODY, hook_body=SUBAGENT_HAND_BACK_BODY, answered=True
)
UNANSWERED_TASK_NOTIFICATION = InjectedPrompt(
    log_body="<task-notification><task-id>autotest-subagent-1</task-id></task-notification>",
    hook_body=None,
    answered=False,
)


def _attr(key: str, value) -> dict:
    kind = "intValue" if isinstance(value, int) else "stringValue"
    if isinstance(value, float):
        kind = "doubleValue"
    return {"key": key, "value": {kind: str(value) if kind == "intValue" else value}}


def _nanos(moment: datetime) -> str:
    return str(int(moment.timestamp()) * 10**9)


@dataclass
class ClaudeCodeTurnsSeed:
    """One Claude Code session: a typed prompt answered by the model, then one injected
    prompt. Typed prompts are the only turns, so the session has exactly one turn.

    ``summary_turns`` is the turn count of the agent.session.summary the client sends at the
    end: a client that counts the injected prompt too reports 2. None sends no summary."""

    key: str
    injected: InjectedPrompt
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0)
        - timedelta(minutes=10)
    )
    user: str = OWNER
    summary_turns: int | None = 2
    session_id: str = field(
        default_factory=lambda: f"autotest-cc-{uuid.uuid4().hex[:12]}"
    )

    @property
    def expected_turns(self) -> int:
        return 1

    @property
    def trace_id(self) -> str:
        return uuid.uuid5(uuid.NAMESPACE_URL, self.session_id).hex

    @property
    def typed_span_id(self) -> str:
        return self.trace_id[:16]

    @property
    def injected_span_id(self) -> str:
        return self.trace_id[16:]

    @property
    def typed_prompt_id(self) -> str:
        return f"typed-{self.session_id}"

    @property
    def injected_prompt_id(self) -> str:
        return f"injected-{self.session_id}"

    @property
    def injected_at(self) -> datetime:
        return self.started_at + timedelta(seconds=20)

    @property
    def typed_input_tokens(self) -> int:
        return TYPED_INPUT_TOKENS

    def events(self, project_name: str) -> list[dict]:
        """Hook events for ``POST /v1/analytics/cli-analytics/event-hooks``."""
        envelope = {
            "session_id": self.session_id,
            "schema_version": 2,
            "codemie_project_name": project_name,
        }

        def hook(event_type: str, moment: datetime, **fields) -> dict:
            return {
                **envelope,
                "type": event_type,
                "timestamp": to_iso(moment),
                "event_id": f"{event_type}:{self.session_id}:{fields.get('prompt_id', '')}",
                **fields,
            }

        events = [
            hook("agent.session.start", self.started_at),
            hook(
                "agent.prompt.submit",
                self.started_at,
                prompt_id=self.typed_prompt_id,
                prompt_body=TYPED_PROMPT,
            ),
        ]
        if self.injected.hook_body is not None:
            events.append(
                hook(
                    "agent.prompt.submit",
                    self.injected_at,
                    prompt_id=self.injected_prompt_id,
                    prompt_body=self.injected.hook_body,
                )
            )
        if self.summary_turns is not None:
            events.append(
                hook(
                    "agent.session.summary",
                    self.injected_at + timedelta(seconds=10),
                    is_final=True,
                    turns=self.summary_turns,
                    started_at=to_iso(self.started_at),
                    ended_at=to_iso(self.injected_at + timedelta(seconds=10)),
                )
            )
        return events

    def _log_record(
        self,
        name: str,
        moment: datetime,
        span_id: str,
        prompt_id: str,
        user_email,
        *extra,
    ) -> dict:
        attributes = [
            _attr("session.id", self.session_id),
            _attr("event.name", name),
            _attr("prompt.id", prompt_id),
            _attr("user.email", user_email),
            *extra,
        ]
        return {
            "timeUnixNano": _nanos(moment),
            "body": {"stringValue": f"claude_code.{name}"},
            "attributes": attributes,
            "traceId": self.trace_id,
            "spanId": span_id,
        }

    def _api_request(
        self, moment, span_id, prompt_id, user_email, input_tokens
    ) -> dict:
        return self._log_record(
            "api_request",
            moment,
            span_id,
            prompt_id,
            user_email,
            _attr("model", SEED_MODEL),
            _attr("request_id", f"req_{prompt_id}"),
            _attr("input_tokens", input_tokens),
            _attr("output_tokens", 10),
            _attr("cache_read_tokens", 0),
            _attr("cache_creation_tokens", 0),
            _attr("cost_usd", 0.01),
        )

    def otlp_logs(self, user_email: str) -> dict:
        """OTLP logs (JSON form) for ``POST /v1/analytics/cli-analytics/logs``."""
        typed_at = self.started_at + timedelta(seconds=1)
        records = [
            self._log_record(
                "user_prompt",
                typed_at,
                self.typed_span_id,
                self.typed_prompt_id,
                user_email,
                _attr("prompt_length", len(TYPED_PROMPT)),
            ),
            self._api_request(
                typed_at + timedelta(seconds=2),
                self.typed_span_id,
                self.typed_prompt_id,
                user_email,
                TYPED_INPUT_TOKENS,
            ),
            self._log_record(
                "user_prompt",
                self.injected_at,
                self.injected_span_id,
                self.injected_prompt_id,
                user_email,
                _attr("prompt_length", len(self.injected.log_body)),
            ),
        ]
        if self.injected.answered:
            records.append(
                self._api_request(
                    self.injected_at + timedelta(seconds=2),
                    self.injected_span_id,
                    self.injected_prompt_id,
                    user_email,
                    HAND_BACK_INPUT_TOKENS,
                )
            )
        return {
            "resourceLogs": [
                {
                    "resource": {"attributes": [_attr("service.name", "claude-code")]},
                    "scopeLogs": [
                        {
                            "scope": {"name": "com.anthropic.claude_code.events"},
                            "logRecords": records,
                        }
                    ],
                }
            ]
        }

    def otlp_traces(self) -> dict:
        """OTLP traces (JSON form) for ``POST /v1/analytics/cli-analytics/traces``: the
        interaction span of the typed prompt and the one of the injected prompt."""

        def interaction(span_id: str, moment: datetime, sequence: int) -> dict:
            return {
                "traceId": self.trace_id,
                "spanId": span_id,
                "name": "claude_code.interaction",
                "kind": 1,
                "startTimeUnixNano": _nanos(moment),
                "endTimeUnixNano": _nanos(moment + timedelta(seconds=5)),
                "attributes": [
                    _attr("session.id", self.session_id),
                    _attr("span.type", "interaction"),
                    _attr("interaction.sequence", sequence),
                ],
                "status": {"code": 0},
            }

        return {
            "resourceSpans": [
                {
                    "resource": {"attributes": [_attr("service.name", "claude-code")]},
                    "scopeSpans": [
                        {
                            "scope": {"name": "com.anthropic.claude_code.tracing"},
                            "spans": [
                                interaction(self.typed_span_id, self.started_at, 1),
                                interaction(self.injected_span_id, self.injected_at, 2),
                            ],
                        }
                    ],
                }
            ]
        }


def get_injected_prompt_seeds() -> dict[str, ClaudeCodeTurnsSeed]:
    """One session per kind of injected prompt, keyed by the scenario id."""
    return {
        "subagent-hand-back": ClaudeCodeTurnsSeed("hand_back", HAND_BACK),
        "unanswered-task-notification": ClaudeCodeTurnsSeed(
            "task_notification", UNANSWERED_TASK_NOTIFICATION
        ),
    }
