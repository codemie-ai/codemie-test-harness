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

"""Test data for CLI Analytics skills started with a slash command.

Each seed is one Claude Code session sent the way the fixed CLI sends it: hook events,
OTel ``api_request`` log records and, for a fork whose requests Claude Code names,
``llm_request`` spans. No interaction or tool span is sent unless a seed says so, so a
session's day is a hooks-only ("fallback") day where the hooks decide what is a skill.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    OWNER,
    otlp_attr,
    otlp_nanos,
    to_iso,
)

CLAUDE_CODE = {"platform": "claude-code"}


@dataclass(frozen=True)
class Request:
    """One model request: its OTel ``api_request`` record at ``offset`` seconds after the
    session start, and the CLI's ``agent.usage.request`` a second before it.

    ``scope_kind`` is the attribution the CLI sends: ``skill`` (named after the seed's
    skill) or ``main``. ``agent_id`` is the fork that made the request. With
    ``span_named`` Claude Code also names the fork on an ``llm_request`` span (a fork a
    tool call started); without it the request sits among the main thread's and only
    the CLI's usage row tells whose it is (a foreground fork).
    ``request_id`` is empty behind a proxy: the backend then pairs the usage row with the
    record by model and token totals."""

    name: str
    offset: int
    prompt: int
    input_tokens: int
    output_tokens: int
    scope_kind: str = "main"
    agent_id: str = ""
    span_named: bool = False
    request_id: bool = True


@dataclass(frozen=True)
class Fork:
    """A forked skill's subagent: its start and stop at ``start`` / ``stop`` seconds after
    the session start, in prompt ``prompt``. With ``tagged`` its start carries the skill
    name the CLI reads from Claude Code's forked-skill marker; the desktop app writes none."""

    agent_id: str
    prompt: int
    start: int
    stop: int
    tagged: bool = True

    @property
    def run_ms(self) -> int:
        return (self.stop - self.start) * 1000


@dataclass
class SlashSkillSeed:
    """One Claude Code session that runs a skill.

    ``skill`` is the skill it runs, a name of its own so the Tools & Models counts of one
    seed are not mixed with another's. ``dispatches`` are slash commands of the skill,
    (prompt index, offset in seconds). ``skill_calls`` are Skill tool calls of the model,
    (prompt index, offset, fork agent id).
    With ``interaction_span`` each prompt also has its OTel interaction span, as a Claude
    Code session with tracing has."""

    key: str
    model: str
    requests: tuple[Request, ...]
    dispatches: tuple[tuple[int, int], ...] = ()
    skill_calls: tuple[tuple[int, int, str], ...] = ()
    forks: tuple[Fork, ...] = ()
    interaction_span: bool = False
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0)
        - timedelta(minutes=15)
    )
    user: str = OWNER
    session_id: str = field(
        default_factory=lambda: f"autotest-skill-{uuid.uuid4().hex[:12]}"
    )
    skill: str = field(default_factory=lambda: f"autotest-skill-{uuid.uuid4().hex[:8]}")

    # ── identities ───────────────────────────────────────────────────────────

    def prompt_id(self, index: int) -> str:
        return f"prompt-{index}-{self.session_id}"

    def request_id(self, request: Request) -> str:
        return f"req-{request.name}-{self.session_id}" if request.request_id else ""

    @property
    def trace_id(self) -> str:
        return uuid.uuid5(uuid.NAMESPACE_URL, self.session_id).hex

    def _span_id(self, name: str) -> str:
        return uuid.uuid5(uuid.NAMESPACE_URL, f"{self.session_id}/{name}").hex[:16]

    def _at(self, offset: float) -> datetime:
        return self.started_at + timedelta(seconds=offset)

    @property
    def prompts(self) -> list[int]:
        used = {request.prompt for request in self.requests}
        used |= {prompt for prompt, _ in self.dispatches}
        used |= {prompt for prompt, _, _ in self.skill_calls}
        return sorted(used)

    def prompted_at(self, index: int) -> int:
        """Seconds after the session start when prompt ``index`` is submitted: before
        everything else of that prompt."""
        offsets = [r.offset for r in self.requests if r.prompt == index]
        offsets += [o for p, o in self.dispatches if p == index]
        offsets += [o for p, o, _ in self.skill_calls if p == index]
        return min(offsets) - 1

    @property
    def ended_at(self) -> int:
        last = [r.offset for r in self.requests] + [f.stop for f in self.forks]
        return max(last) + 5

    # ── hook events ──────────────────────────────────────────────────────────

    def _hook(self, project: str, event_type: str, offset: float, key: str, **fields):
        return {
            "type": event_type,
            "event_id": f"{event_type}:{self.session_id}:{key}",
            "timestamp": to_iso(self._at(offset)),
            "session_id": self.session_id,
            "schema_version": 2,
            "codemie_project_name": project,
            **CLAUDE_CODE,
            **fields,
        }

    def events(self, project: str) -> list[dict]:
        """Hook events for ``POST /v1/analytics/cli-analytics/event-hooks``."""
        events = [self._hook(project, "agent.session.start", 0, "start")]
        for index in self.prompts:
            events.append(
                self._hook(
                    project,
                    "agent.prompt.submit",
                    self.prompted_at(index),
                    str(index),
                    hook_event_name="UserPromptSubmit",
                    prompt_id=self.prompt_id(index),
                    prompt_body=f"autotest prompt {index}",
                )
            )
        for prompt, offset in self.dispatches:
            events.append(
                self._hook(
                    project,
                    "agent.skill.dispatch",
                    offset,
                    str(prompt),
                    hook_event_name="UserPromptExpansion",
                    expansion_type="slash_command",
                    command_name=self.skill,
                    command_source="projectSettings",
                    skill_name=self.skill,
                    prompt_id=self.prompt_id(prompt),
                )
            )
        for prompt, offset, agent_id in self.skill_calls:
            events.extend(self._skill_call(project, prompt, offset, agent_id))
        for fork in self.forks:
            events.extend(self._fork_events(project, fork))
        events.extend(self._usage(project, request) for request in self.requests)
        events.append(self._hook(project, "agent.session.end", self.ended_at, "end"))
        return events

    def _skill_call(self, project: str, prompt: int, offset: int, agent_id: str):
        """PreToolUse and PostToolUse of a Skill call that forked ``agent_id``; the CLI
        names the fork in ``fork_agent_id`` and Claude Code in ``tool_response``."""
        call = {
            "prompt_id": self.prompt_id(prompt),
            "tool_name": "Skill",
            "tool_input": f'{{"skill": "{self.skill}"}}',
            "tool_use_id": f"toolu_{agent_id}",
        }
        response = (
            f'{{"success":true,"commandName":"{self.skill}","status":"forked",'
            f'"background":true,"agentId":"{agent_id}","result":"Running in the background"}}'
        )
        return [
            self._hook(
                project,
                "agent.tool.start",
                offset,
                agent_id,
                hook_event_name="PreToolUse",
                skill_name=self.skill,
                **call,
            ),
            self._hook(
                project,
                "agent.tool.end",
                offset,
                agent_id,
                hook_event_name="PostToolUse",
                tool_response=response,
                fork_agent_id=agent_id,
                duration_ms=12,
                **call,
            ),
        ]

    def _fork_events(self, project: str, fork: Fork) -> list[dict]:
        start = self._hook(
            project,
            "agent.subagent.start",
            fork.start,
            fork.agent_id,
            hook_event_name="SubagentStart",
            prompt_id=self.prompt_id(fork.prompt),
            agent_id=fork.agent_id,
            agent_type="general-purpose",
        )
        if fork.tagged:
            start["skill_name"] = self.skill
        stop = self._hook(
            project,
            "agent.subagent.stop",
            fork.stop,
            fork.agent_id,
            hook_event_name="SubagentStop",
            agent_id=fork.agent_id,
            agent_type="general-purpose",
        )
        return [start, stop]

    def _usage(self, project: str, request: Request) -> dict:
        return self._hook(
            project,
            "agent.usage.request",
            request.offset - 1,
            request.name,
            request_id=self.request_id(request),
            message_id=f"msg-{request.name}-{self.session_id}",
            agent_id=request.agent_id,
            agent_type="general-purpose" if request.agent_id else "",
            scope_kind=request.scope_kind,
            scope_name=self.skill if request.scope_kind == "skill" else "",
            model_raw=self.model,
            model=self.model,
            input_tokens=request.input_tokens,
            output_tokens=request.output_tokens,
            cache_read_tokens=0,
            cache_creation_5m_tokens=0,
            cache_creation_1h_tokens=0,
            stop_reason="end_turn",
            is_api_error=False,
        )

    # ── OTel ─────────────────────────────────────────────────────────────────

    def _group_span(self, request: Request) -> str:
        """The span that groups a request: the fork's request group when Claude Code names
        the fork, else the interaction span of its prompt."""
        if request.span_named:
            return self._span_id(f"group-{request.name}")
        return self._span_id(f"interaction-{request.prompt}")

    def otlp_logs(self, user_email: str) -> dict:
        """OTLP logs (JSON form) for ``POST /v1/analytics/cli-analytics/logs``: one
        ``api_request`` per request. Catalog money is tokens × the model's price, so the
        reported cost is a token value only."""

        def record(request: Request) -> dict:
            attributes = {
                "event.name": {"stringValue": "api_request"},
                "session.id": {"stringValue": self.session_id},
                "prompt.id": {"stringValue": self.prompt_id(request.prompt)},
                "user.email": {"stringValue": user_email},
                "model": {"stringValue": self.model},
                "cost_usd": {"doubleValue": 0.0001},
                "input_tokens": {"intValue": str(request.input_tokens)},
                "output_tokens": {"intValue": str(request.output_tokens)},
                "cache_read_tokens": {"intValue": "0"},
                "cache_creation_tokens": {"intValue": "0"},
            }
            if request.request_id:
                attributes["request_id"] = {"stringValue": self.request_id(request)}
            return {
                "timeUnixNano": otlp_nanos(self._at(request.offset)),
                "body": {"stringValue": "claude_code.api_request"},
                "attributes": [{"key": k, "value": v} for k, v in attributes.items()],
                "traceId": self.trace_id,
                "spanId": self._group_span(request),
            }

        return _resource_logs([record(request) for request in self.requests])

    def otlp_traces(self) -> dict | None:
        """OTLP traces (JSON form) for ``POST /v1/analytics/cli-analytics/traces``: the
        ``llm_request`` span of each request that names its fork and, with
        ``interaction_span``, the interaction span of each prompt. None when there are none."""
        spans = []
        for request in self.requests:
            if request.span_named:
                moment = self._at(request.offset - 1)
                spans.append(
                    self._span(
                        "claude_code.llm_request",
                        self._span_id(f"llm-{request.name}"),
                        moment,
                        moment + timedelta(seconds=1),
                        parent=self._group_span(request),
                        agent_id=request.agent_id,
                    )
                )
        if self.interaction_span:
            for index in self.prompts:
                start = self._at(self.prompted_at(index) - 1)
                spans.append(
                    self._span(
                        "claude_code.interaction",
                        self._span_id(f"interaction-{index}"),
                        start,
                        self._at(self.ended_at - 1),
                        **{"span.type": "interaction"},
                    )
                )
        if not spans:
            return None
        return {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [otlp_attr("service.name", "claude-code")]
                    },
                    "scopeSpans": [
                        {
                            "scope": {"name": "com.anthropic.claude_code.tracing"},
                            "spans": spans,
                        }
                    ],
                }
            ]
        }

    def _span(self, name, span_id, start, end, parent=None, **attributes) -> dict:
        span = {
            "traceId": self.trace_id,
            "spanId": span_id,
            "name": name,
            "kind": 1,
            "startTimeUnixNano": otlp_nanos(start),
            "endTimeUnixNano": otlp_nanos(end),
            "attributes": [
                otlp_attr("session.id", self.session_id),
                *(otlp_attr(key, value) for key, value in attributes.items()),
            ],
            "status": {"code": 0},
        }
        if parent:
            span["parentSpanId"] = parent
        return span

    # ── expectations ─────────────────────────────────────────────────────────

    def tokens_of(self, *names: str) -> tuple[int, int]:
        """(input, output) tokens of the named requests together."""
        chosen = [r for r in self.requests if r.name in names]
        return (
            sum(r.input_tokens for r in chosen),
            sum(r.output_tokens for r in chosen),
        )

    @property
    def inline_skill_run_ms(self) -> int:
        """Run of an inline slash skill: from its first slash command to the last request
        the CLI attributed to the skill."""
        first_dispatch = min(offset for _, offset in self.dispatches)
        last_skill_request = max(
            r.offset for r in self.requests if r.scope_kind == "skill"
        )
        return (last_skill_request - first_dispatch) * 1000


def _fork_id() -> str:
    """A fork agent id of the form Claude Code gives one, new for every seed."""
    return f"a{uuid.uuid4().hex[:16]}"


def _resource_logs(records: list[dict]) -> dict:
    return {
        "resourceLogs": [
            {
                "resource": {"attributes": [otlp_attr("service.name", "claude-code")]},
                "scopeLogs": [
                    {
                        "scope": {"name": "com.anthropic.claude_code.events"},
                        "logRecords": records,
                    }
                ],
            }
        ]
    }


# ── A forked skill counts once, as a skill ───────────────────────────────────


def get_slash_fork_seed(model: str) -> SlashSkillSeed:
    """/forkme: the slash command and its fork's start share the prompt, so they are one
    invocation. The fork runs 40 s and makes one request Claude Code names by its id."""
    fork_id = _fork_id()
    return SlashSkillSeed(
        key="slash_fork",
        model=model,
        dispatches=((0, 5),),
        forks=(Fork(fork_id, prompt=0, start=6, stop=46),),
        requests=(
            Request("main", 2, 0, 800, 40),
            Request(
                "fork",
                10,
                0,
                1500,
                120,
                scope_kind="skill",
                agent_id=fork_id,
                span_named=True,
            ),
        ),
    )


def get_skill_call_fork_seed(model: str) -> SlashSkillSeed:
    """The model runs the same skill through the Skill tool: the call and the fork it
    names are one invocation. The fork runs 30 s and makes one request."""
    fork_id = _fork_id()
    return SlashSkillSeed(
        key="skill_call_fork",
        model=model,
        skill_calls=((0, 5, fork_id),),
        forks=(Fork(fork_id, prompt=0, start=6, stop=36),),
        requests=(
            Request("main", 2, 0, 800, 40),
            Request(
                "fork",
                10,
                0,
                1300,
                110,
                scope_kind="skill",
                agent_id=fork_id,
                span_named=True,
            ),
        ),
    )


# ── An inline skill run as a slash command ───────────────────────────────────


def get_inline_slash_seed(model: str) -> SlashSkillSeed:
    """/inlineme runs in the main thread: the CLI attributes two of the prompt's requests
    to the skill. A third request of the same prompt stays the main thread's, and so does
    a request of a later ordinary prompt."""
    return SlashSkillSeed(
        key="inline_slash",
        model=model,
        interaction_span=True,
        dispatches=((0, 5),),
        requests=(
            Request("skill-1", 15, 0, 1100, 70, scope_kind="skill"),
            Request("skill-2", 35, 0, 900, 50, scope_kind="skill"),
            Request("main", 45, 0, 5000, 300),
            Request("ordinary", 70, 1, 4000, 200),
        ),
    )


INLINE_SKILL_REQUESTS = ("skill-1", "skill-2")


# ── A foreground fork no request names (Claude Code desktop app) ─────────────


def get_foreground_fork_seed(model: str) -> SlashSkillSeed:
    """/forkme in the desktop app: the fork runs in the foreground, writes no
    forked-skill marker (no skill_name on its start), and Claude Code names it on none of
    its requests. Behind the local proxy no request carries a request id. Only the CLI's
    usage rows, under the fork's agent id, tell its request from the main thread's request
    of the same prompt."""
    fork_id = _fork_id()
    return SlashSkillSeed(
        key="foreground_fork",
        model=model,
        interaction_span=True,
        dispatches=((0, 5),),
        forks=(Fork(fork_id, prompt=0, start=7, stop=25, tagged=False),),
        requests=(
            Request(
                "fork",
                15,
                0,
                1700,
                180,
                scope_kind="skill",
                agent_id=fork_id,
                request_id=False,
            ),
            Request("main", 35, 0, 500, 50, request_id=False),
        ),
    )
