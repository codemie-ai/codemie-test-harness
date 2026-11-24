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

TYPED_PROMPT_TEXT = "use an Explore subagent to list the files in this folder"
# A prompt the user typed that starts like the message Claude Desktop shows for a peer
# session's hand-back, but without the "<agent-message" tag Claude Code injects.
TYPED_PEER_LOOKALIKE_TEXT = (
    "Another Claude session sent a message: summarise it for me in one line"
)
SUBAGENT_HAND_BACK_BODY = '<agent-message from="autotest-subagent-1"> [Subagent hand-back] The folder is empty.'
SECOND_SUBAGENT_HAND_BACK_BODY = '<agent-message from="autotest-subagent-2"> [Subagent hand-back] README.md has 3 lines.'
TASK_NOTIFICATION_BODY = (
    "<task-notification><task-id>autotest-subagent-1</task-id></task-notification>"
)
TYPED_INPUT_TOKENS = 1000
INJECTED_INPUT_TOKENS = 2000
# Seconds between two prompts of a session.
PROMPT_SPACING = 20


@dataclass(frozen=True)
class SessionPrompt:
    """A prompt of a Claude Code session, sent as its own interaction span.

    ``hook_body`` is the body of the agent.prompt.submit hook of the same prompt_id, or
    None when no hook arrives for it. ``answered`` is whether the model replied to it,
    that is, whether its span holds an api_request. ``typed`` is whether the user typed
    it: only typed prompts are turns.
    """

    log_body: str
    hook_body: str | None
    answered: bool
    typed: bool


TYPED_PROMPT = SessionPrompt(
    log_body=TYPED_PROMPT_TEXT,
    hook_body=TYPED_PROMPT_TEXT,
    answered=True,
    typed=True,
)
TYPED_PEER_LOOKALIKE = SessionPrompt(
    log_body=TYPED_PEER_LOOKALIKE_TEXT,
    hook_body=TYPED_PEER_LOOKALIKE_TEXT,
    answered=True,
    typed=True,
)
HAND_BACK = SessionPrompt(
    log_body=SUBAGENT_HAND_BACK_BODY,
    hook_body=SUBAGENT_HAND_BACK_BODY,
    answered=True,
    typed=False,
)
SECOND_HAND_BACK = SessionPrompt(
    log_body=SECOND_SUBAGENT_HAND_BACK_BODY,
    hook_body=SECOND_SUBAGENT_HAND_BACK_BODY,
    answered=True,
    typed=False,
)
UNANSWERED_TASK_NOTIFICATION = SessionPrompt(
    log_body=TASK_NOTIFICATION_BODY,
    hook_body=None,
    answered=False,
    typed=False,
)
ANSWERED_TASK_NOTIFICATION = SessionPrompt(
    log_body=TASK_NOTIFICATION_BODY,
    hook_body=TASK_NOTIFICATION_BODY,
    answered=True,
    typed=False,
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
    """One Claude Code session: a typed prompt answered by the model, then ``followups``,
    one interaction span each. Only typed prompts are turns.

    With ``client_summary`` the client sends an agent.session.summary at the end whose
    turns are ``summary_turns``, one per prompt line of the transcript, injected ones
    included, as CLI 0.16.7 and older counted them (0.16.8 and later skip injected
    prompts). The backend serves the larger of its own count and the summary, so a seed
    that checks the backend's count sends none. With ``late_injected_hooks`` the prompt
    hooks of the injected prompts are left out of ``events`` and sent later through
    ``late_events``, as when they reach the backend after the session was first rolled
    up."""

    key: str
    followups: tuple[SessionPrompt, ...]
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0)
        - timedelta(minutes=10)
    )
    user: str = OWNER
    client_summary: bool = False
    late_injected_hooks: bool = False
    session_id: str = field(
        default_factory=lambda: f"autotest-cc-{uuid.uuid4().hex[:12]}"
    )

    @property
    def prompts(self) -> tuple[SessionPrompt, ...]:
        return (TYPED_PROMPT, *self.followups)

    @property
    def summary_turns(self) -> int:
        return len(self.prompts)

    @property
    def expected_turns(self) -> int:
        return sum(1 for prompt in self.prompts if prompt.typed)

    @property
    def turns_before_late_hooks(self) -> int:
        """Turns while the late hooks are still missing: an answered injected prompt
        without its hook cannot be told from a typed one, so it counts until the hook
        arrives."""
        return sum(
            1
            for prompt in self.prompts
            if prompt.typed or (prompt.answered and prompt.hook_body is not None)
        )

    @property
    def trace_id(self) -> str:
        return uuid.uuid5(uuid.NAMESPACE_URL, self.session_id).hex

    def span_id(self, index: int) -> str:
        return uuid.uuid5(uuid.NAMESPACE_URL, f"{self.session_id}/{index}").hex[:16]

    def prompt_id(self, index: int) -> str:
        return f"prompt-{index}-{self.session_id}"

    def prompted_at(self, index: int) -> datetime:
        return self.started_at + timedelta(seconds=1 + PROMPT_SPACING * index)

    @property
    def ended_at(self) -> datetime:
        return self.prompted_at(len(self.prompts) - 1) + timedelta(seconds=10)

    def _envelope(self, project_name: str) -> dict:
        return {
            "session_id": self.session_id,
            "schema_version": 2,
            "codemie_project_name": project_name,
        }

    def _hook(
        self, project_name: str, event_type: str, moment: datetime, **fields
    ) -> dict:
        return {
            **self._envelope(project_name),
            "type": event_type,
            "timestamp": to_iso(moment),
            "event_id": f"{event_type}:{self.session_id}:{fields.get('prompt_id', '')}",
            **fields,
        }

    def _prompt_hooks(self, project_name: str, typed: bool) -> list[dict]:
        return [
            self._hook(
                project_name,
                "agent.prompt.submit",
                self.prompted_at(index),
                prompt_id=self.prompt_id(index),
                prompt_body=prompt.hook_body,
            )
            for index, prompt in enumerate(self.prompts)
            if prompt.hook_body is not None and prompt.typed == typed
        ]

    def events(self, project_name: str) -> list[dict]:
        """Hook events for ``POST /v1/analytics/cli-analytics/event-hooks``, without the
        injected prompts' hooks when they arrive late."""
        events = [self._hook(project_name, "agent.session.start", self.started_at)]
        events.extend(self._prompt_hooks(project_name, typed=True))
        if not self.late_injected_hooks:
            events.extend(self._prompt_hooks(project_name, typed=False))
        if self.client_summary:
            events.append(
                self._hook(
                    project_name,
                    "agent.session.summary",
                    self.ended_at,
                    is_final=True,
                    turns=self.summary_turns,
                    started_at=to_iso(self.started_at),
                    ended_at=to_iso(self.ended_at),
                )
            )
        return events

    def late_events(self, project_name: str) -> list[dict]:
        """The injected prompts' hooks a session with ``late_injected_hooks`` sends late."""
        return self._prompt_hooks(project_name, typed=False)

    def _log_record(
        self,
        name: str,
        moment: datetime,
        index: int,
        user_email,
        *extra,
    ) -> dict:
        attributes = [
            _attr("session.id", self.session_id),
            _attr("event.name", name),
            _attr("prompt.id", self.prompt_id(index)),
            _attr("user.email", user_email),
            *extra,
        ]
        return {
            "timeUnixNano": _nanos(moment),
            "body": {"stringValue": f"claude_code.{name}"},
            "attributes": attributes,
            "traceId": self.trace_id,
            "spanId": self.span_id(index),
        }

    def otlp_logs(self, user_email: str) -> dict:
        """OTLP logs (JSON form) for ``POST /v1/analytics/cli-analytics/logs``: the
        user_prompt of every prompt and the api_request of every answered one."""
        records = []
        for index, prompt in enumerate(self.prompts):
            moment = self.prompted_at(index)
            records.append(
                self._log_record(
                    "user_prompt",
                    moment,
                    index,
                    user_email,
                    _attr("prompt_length", len(prompt.log_body)),
                )
            )
            if prompt.answered:
                records.append(
                    self._log_record(
                        "api_request",
                        moment + timedelta(seconds=2),
                        index,
                        user_email,
                        _attr("model", SEED_MODEL),
                        _attr("request_id", f"req_{self.prompt_id(index)}"),
                        _attr(
                            "input_tokens",
                            TYPED_INPUT_TOKENS
                            if prompt.typed
                            else INJECTED_INPUT_TOKENS,
                        ),
                        _attr("output_tokens", 10),
                        _attr("cache_read_tokens", 0),
                        _attr("cache_creation_tokens", 0),
                        _attr("cost_usd", 0.01),
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
        """OTLP traces (JSON form) for ``POST /v1/analytics/cli-analytics/traces``: one
        interaction span per prompt."""

        def interaction(index: int) -> dict:
            moment = self.prompted_at(index) - timedelta(seconds=1)
            return {
                "traceId": self.trace_id,
                "spanId": self.span_id(index),
                "name": "claude_code.interaction",
                "kind": 1,
                "startTimeUnixNano": _nanos(moment),
                "endTimeUnixNano": _nanos(moment + timedelta(seconds=5)),
                "attributes": [
                    _attr("session.id", self.session_id),
                    _attr("span.type", "interaction"),
                    _attr("interaction.sequence", index + 1),
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
                                interaction(index) for index in range(len(self.prompts))
                            ],
                        }
                    ],
                }
            ]
        }


def get_injected_prompt_seeds() -> dict[str, ClaudeCodeTurnsSeed]:
    """One session per kind of injected prompt, keyed by the scenario id. Each has one
    typed prompt, so one turn. No client summary, so the served turns are the ones the
    backend counted."""
    return {
        "subagent-hand-back": ClaudeCodeTurnsSeed("hand_back", (HAND_BACK,)),
        "unanswered-task-notification": ClaudeCodeTurnsSeed(
            "task_notification", (UNANSWERED_TASK_NOTIFICATION,)
        ),
        "answered-task-notification": ClaudeCodeTurnsSeed(
            "answered_task_notification", (ANSWERED_TASK_NOTIFICATION,)
        ),
        "parallel-subagent-hand-backs": ClaudeCodeTurnsSeed(
            "parallel_hand_backs", (HAND_BACK, SECOND_HAND_BACK)
        ),
    }


def get_typed_prompts_seed() -> ClaudeCodeTurnsSeed:
    """Two typed prompts, the second starting like a peer session's hand-back, and a
    subagent hand-back between them: two turns. No client summary, so the served turns
    are the ones the backend counted."""
    return ClaudeCodeTurnsSeed("typed_prompts", (HAND_BACK, TYPED_PEER_LOOKALIKE))


def get_late_hook_seed() -> ClaudeCodeTurnsSeed:
    """A typed prompt and a subagent hand-back whose prompt hook reaches the backend after
    the session was rolled up. No client summary, so the served turns are the counted ones."""
    return ClaudeCodeTurnsSeed(
        "late_hand_back_hook", (HAND_BACK,), late_injected_hooks=True
    )
