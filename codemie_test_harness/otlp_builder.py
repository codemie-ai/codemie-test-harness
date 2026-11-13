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

"""Builders for CLI Analytics ingest payloads (OTLP logs/metrics/traces and NDJSON hook events).

Kept at the package root on purpose: importing it must not import codemie_test_harness.tests
(its __init__ loads the .env file) nor codemie_test_harness.cli.

OTLP/JSON differs from plain protobuf JSON in one respect that matters here: trace, span and
parent span ids are lowercase hex strings, not base64. Every other bytes field (in practice
AnyValue.bytesValue) stays base64. The BE decoder converts exactly those three keys from hex.
"""

import base64
import json
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

from google.protobuf import json_format
from google.protobuf.message import Message
from opentelemetry.proto.collector.logs.v1 import logs_service_pb2 as logs_svc
from opentelemetry.proto.collector.metrics.v1 import metrics_service_pb2 as metrics_svc
from opentelemetry.proto.collector.trace.v1 import trace_service_pb2 as trace_svc
from opentelemetry.proto.common.v1 import common_pb2 as common
from opentelemetry.proto.logs.v1 import logs_pb2 as logs
from opentelemetry.proto.metrics.v1 import metrics_pb2 as metrics
from opentelemetry.proto.resource.v1 import resource_pb2 as resource
from opentelemetry.proto.trace.v1 import trace_pb2 as trace

PROJECT_KEY = "codemie_project_name"
_HEX_ID_KEYS = frozenset({"traceId", "spanId", "parentSpanId"})
_BYTES_PROBE = b"\xff\xfebytes-value"
_BIG_INT = 2**60 + 1  # above 2**53: must survive JSON as a decimal string


@dataclass(frozen=True)
class OtlpPayload:
    """One export request in both encodings. wire_count = log records / data points / spans."""

    protobuf: bytes
    json: bytes
    wire_count: int
    message: Message


def _str_attr(key: str, value: str):
    return common.KeyValue(key=key, value=common.AnyValue(string_value=value))


def _resource(session_id: str, resource_project: Optional[str]):
    attributes = [
        _str_attr("service.name", "autotest-cli"),
        _str_attr("session.id", session_id),
        common.KeyValue(
            key="payload.bytes", value=common.AnyValue(bytes_value=_BYTES_PROBE)
        ),
        common.KeyValue(key="payload.big", value=common.AnyValue(int_value=_BIG_INT)),
    ]
    if resource_project:
        attributes.append(_str_attr(PROJECT_KEY, resource_project))
    return resource.Resource(attributes=attributes)


def _project_attrs(project_names: Iterable[str], index: int) -> list:
    names = list(project_names)
    return [_str_attr(PROJECT_KEY, names[index % len(names)])] if names else []


def _trace_id() -> bytes:
    return secrets.token_bytes(16)


def _span_id() -> bytes:
    return secrets.token_bytes(8)


def _to_json(message: Message) -> bytes:
    """OTLP/JSON: camelCase keys, enums as integers, trace/span ids as lowercase hex."""
    document = json_format.MessageToDict(message, use_integers_for_enums=True)
    _ids_to_hex(document)
    return json.dumps(document).encode()


def _ids_to_hex(node) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in _HEX_ID_KEYS and isinstance(value, str):
                node[key] = base64.b64decode(value).hex()
            else:
                _ids_to_hex(value)
    elif isinstance(node, list):
        for item in node:
            _ids_to_hex(item)


def _payload(message: Message, wire_count: int) -> OtlpPayload:
    return OtlpPayload(
        protobuf=message.SerializeToString(),
        json=_to_json(message),
        wire_count=wire_count,
        message=message,
    )


def build_logs(
    n: int,
    project_names: Iterable[str],
    resource_project: Optional[str] = None,
    session_id: Optional[str] = None,
) -> OtlpPayload:
    """n log records; record i carries project_names[i % len] (none when the list is empty).

    session_id sets the resource's session.id (default: a generated autotest id)."""
    session_id = session_id or f"autotest-otlp-{secrets.token_hex(6)}"
    now = time.time_ns()
    records = [
        logs.LogRecord(
            time_unix_nano=now + i,
            severity_number=logs.SeverityNumber.SEVERITY_NUMBER_INFO,
            body=common.AnyValue(string_value=f"autotest log {i}"),
            attributes=[_str_attr("event.name", "autotest")]
            + _project_attrs(project_names, i),
            trace_id=_trace_id(),
            span_id=_span_id(),
        )
        for i in range(n)
    ]
    message = logs_svc.ExportLogsServiceRequest(
        resource_logs=[
            logs.ResourceLogs(
                resource=_resource(session_id, resource_project),
                scope_logs=[logs.ScopeLogs(log_records=records)],
            )
        ]
    )
    return _payload(message, n)


def build_metrics(
    n: int,
    project_names: Iterable[str],
    resource_project: Optional[str] = None,
    session_id: Optional[str] = None,
) -> OtlpPayload:
    """One cumulative-delta Sum metric with n data points, each with an exemplar (ids)."""
    m = metrics
    session_id = session_id or f"autotest-otlp-{secrets.token_hex(6)}"
    now = time.time_ns()
    points = [
        m.NumberDataPoint(
            time_unix_nano=now + i,
            start_time_unix_nano=now,
            as_int=1,
            attributes=_project_attrs(project_names, i),
            exemplars=[
                m.Exemplar(
                    time_unix_nano=now + i,
                    as_int=1,
                    trace_id=_trace_id(),
                    span_id=_span_id(),
                )
            ],
        )
        for i in range(n)
    ]
    metric = m.Metric(
        name="autotest.counter",
        sum=m.Sum(
            data_points=points,
            aggregation_temporality=m.AggregationTemporality.AGGREGATION_TEMPORALITY_DELTA,
            is_monotonic=True,
        ),
    )
    message = metrics_svc.ExportMetricsServiceRequest(
        resource_metrics=[
            m.ResourceMetrics(
                resource=_resource(session_id, resource_project),
                scope_metrics=[m.ScopeMetrics(metrics=[metric])],
            )
        ]
    )
    return _payload(message, n)


def build_traces(
    n: int,
    project_names: Iterable[str],
    resource_project: Optional[str] = None,
    session_id: Optional[str] = None,
) -> OtlpPayload:
    """n spans, each with a parent span id and one link (ids at several depths)."""
    t = trace
    session_id = session_id or f"autotest-otlp-{secrets.token_hex(6)}"
    now = time.time_ns()
    spans = [
        t.Span(
            trace_id=_trace_id(),
            span_id=_span_id(),
            parent_span_id=_span_id(),
            name=f"autotest span {i}",
            kind=t.Span.SpanKind.SPAN_KIND_CLIENT,
            start_time_unix_nano=now + i,
            end_time_unix_nano=now + i + 1000,
            attributes=_project_attrs(project_names, i),
            links=[t.Span.Link(trace_id=_trace_id(), span_id=_span_id())],
        )
        for i in range(n)
    ]
    message = trace_svc.ExportTraceServiceRequest(
        resource_spans=[
            t.ResourceSpans(
                resource=_resource(session_id, resource_project),
                scope_spans=[t.ScopeSpans(spans=spans)],
            )
        ]
    )
    return _payload(message, n)


def build_hook_events(
    session_id: str,
    project: Optional[str],
    developer_name: str,
    repository: str,
    prompt: str,
    now: Optional[datetime] = None,
    *,
    batch_id: str = "",
    input_tokens: int = 1,
    output_tokens: int = 1,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
    session_start: bool = True,
    session_end: bool = True,
    tool_calls: Iterable[dict] = (),
    min_session_end_offset_s: float = 0.0,
) -> list[dict]:
    """The four events of one CLI session; every event carries codemie_project_name=project.

    project=None omits the key. event_ids are unique per session id, so a re-send of the
    same events is a duplicate for the BE, a new session id is new data.

    batch_id disambiguates event ids across repeated calls with the same session_id (a
    resumed session's later batch): "" (the default) keeps every existing call site's ids
    unchanged; a non-empty value makes the same event type ingested again in a later batch
    stored as new data instead of being deduplicated as a resend (the BE keys a record's
    identity by (event type, session, event_id), see record_hash/_event_identity).

    input_tokens / output_tokens / cache_read_tokens / cache_creation_tokens: carried on the
    usage.request event (cache_creation_tokens as cache_creation_1h_tokens, summed
    server-side into cache_creation_tokens alongside cache_creation_5m_tokens).

    session_start / session_end: include the agent.session.start / agent.session.end
    events. A resumed batch (same session_id as an earlier call) should pass
    session_start=False to avoid re-opening the session that is already running.

    tool_calls: iterable of {"tool_name": str, "tool_use_id": str, "outcome": "success" |
    "error"}. Each emits an agent.tool.start paired with an agent.tool.end (success) or
    agent.tool.error (error), between the usage event and session.end so neither can ever
    become the session's last dimension event (see DIMENSION_HOOK_TYPES; these hook pairs
    have no bearing on tool_call_count once the session also has OTLP tool spans: the BE's
    hook-based tool_facts_daily fallback is used only for a session/day with no span of
    kind TOOL/TOOL_EXECUTION/INTERACTION, see _NO_SPAN_OF_KIND in rollups.py).

    min_session_end_offset_s: floors the agent.session.end offset (default: right after the
    last tool pair, same as before this parameter existed). A session that also sends OTLP
    spans (build_tool_spans / build_interaction_spans) alongside its hook events should set
    this past every span's own timestamp, so the hook session.end event -- not a span -- is
    unambiguously the session's last dimension event regardless of whether span timestamps
    also factor into the environment's computed session duration.
    """
    now = now or datetime.now(timezone.utc)
    common = {
        "session_id": session_id,
        "schema_version": 2,
        "entrypoint": "cli",
        "developer_name": developer_name,
        "cwd": repository,
        "git_branch": "autotest",
    }
    if project is not None:
        common[PROJECT_KEY] = project

    def event(event_type: str, offset_s: float, event_id: str, **fields) -> dict:
        timestamp = now + timedelta(seconds=offset_s)
        return {
            "type": event_type,
            "event_id": event_id,
            "timestamp": timestamp.isoformat(timespec="milliseconds").replace(
                "+00:00", "Z"
            ),
            **common,
            **fields,
        }

    def dim_event(event_type: str, offset_s: float, **fields) -> dict:
        return event(
            event_type, offset_s, f"{event_type}:{session_id}{batch_id}", **fields
        )

    events = []
    offset = 0
    if session_start:
        events.append(dim_event("agent.session.start", offset))
        offset += 1
    events.append(dim_event("agent.prompt.submit", offset, prompt_body=prompt))
    offset += 1
    events.append(
        event(
            "agent.usage.request",
            offset,
            f"agent.usage.request:{session_id}{batch_id}",
            request_id=f"req-{session_id}{batch_id}",
            model_raw="claude-sonnet-5-5",
            model="claude-sonnet-5-5",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read_tokens,
            cache_creation_1h_tokens=cache_creation_tokens,
            stop_reason="end_turn",
            is_api_error=False,
        )
    )
    offset += 1
    for call in tool_calls:
        tool_name, tool_use_id = call["tool_name"], call["tool_use_id"]
        outcome = call.get("outcome", "success")
        end_type = "agent.tool.end" if outcome == "success" else "agent.tool.error"
        events.append(
            event(
                "agent.tool.start",
                offset,
                f"agent.tool.start:{session_id}{batch_id}:{tool_use_id}",
                tool_name=tool_name,
                tool_use_id=tool_use_id,
            )
        )
        offset += 0.1
        events.append(
            event(
                end_type,
                offset,
                f"{end_type}:{session_id}{batch_id}:{tool_use_id}",
                tool_name=tool_name,
                tool_use_id=tool_use_id,
            )
        )
        offset += 0.1
    if session_end:
        events.append(
            dim_event("agent.session.end", max(offset, min_session_end_offset_s))
        )
    return events


def build_tool_spans(
    session_id: str,
    calls: Iterable[dict],
    resource_project: Optional[str] = None,
    now: Optional[datetime] = None,
) -> OtlpPayload:
    """One `claude_code.tool` span plus one `claude_code.tool.execution` span per call.

    `calls`: iterable of {"tool_name": str, "tool_use_id": str, "success": bool}. The two
    spans of a call share its tool_use_id, the join key the BE's reader uses to pair a
    tool call with its outcome (see get_session_detail_tools / invocations_hourly kind=1);
    `success` becomes the execution span's "true"/"false" `success` attribute.

    Unlike hook events (agent.tool.start/end/error), whose tool-call facts only ever reach
    the aggregate tool_facts_daily/invocations_hourly rollups, real OTLP tool spans are the
    only source of the per-session, per-tool success/failure breakdown a session detail
    response exposes (`tools`, `tool_calls_success`): that reader query selects from the
    `spans` table alone, with no hook-event fallback.

    Each span's own "session.id" attribute (not just the resource's) is what the BE's span
    decoder reads to attribute it to `session_id` (see decode_traces/_SESSION_ID_KEY).
    """
    now = now or datetime.now(timezone.utc)
    spans = []
    offset = 0
    for call in calls:
        tool_name = call["tool_name"]
        tool_use_id = call["tool_use_id"]
        success = call.get("success", True)
        start = now + timedelta(seconds=offset)
        end = start + timedelta(seconds=1)
        spans.append(
            trace.Span(
                trace_id=_trace_id(),
                span_id=_span_id(),
                name="claude_code.tool",
                kind=trace.Span.SpanKind.SPAN_KIND_CLIENT,
                start_time_unix_nano=int(start.timestamp() * 1_000_000_000),
                end_time_unix_nano=int(end.timestamp() * 1_000_000_000),
                attributes=[
                    _str_attr("session.id", session_id),
                    _str_attr("tool_name", tool_name),
                    _str_attr("tool_use_id", tool_use_id),
                ],
            )
        )
        exec_end = end + timedelta(milliseconds=500)
        spans.append(
            trace.Span(
                trace_id=_trace_id(),
                span_id=_span_id(),
                name="claude_code.tool.execution",
                kind=trace.Span.SpanKind.SPAN_KIND_CLIENT,
                start_time_unix_nano=int(end.timestamp() * 1_000_000_000),
                end_time_unix_nano=int(exec_end.timestamp() * 1_000_000_000),
                attributes=[
                    _str_attr("session.id", session_id),
                    _str_attr("tool_use_id", tool_use_id),
                    _str_attr("success", "true" if success else "false"),
                ],
            )
        )
        offset += 2
    message = trace_svc.ExportTraceServiceRequest(
        resource_spans=[
            trace.ResourceSpans(
                resource=_resource(session_id, resource_project),
                scope_spans=[trace.ScopeSpans(spans=spans)],
            )
        ]
    )
    return _payload(message, len(spans))


def build_interaction_spans(
    session_id: str,
    count: int,
    resource_project: Optional[str] = None,
    now: Optional[datetime] = None,
) -> OtlpPayload:
    """`count` `claude_code.interaction` spans (span_kind INTERACTION) of one session.

    This is the only source of a session's `turns`/prompt count once it also has any
    TOOL or TOOL_EXECUTION span (as build_tool_spans sends): the BE's turns_daily
    hook-based fallback (counting agent.prompt.submit) only runs for a session/day with
    no span of kind TOOL, TOOL_EXECUTION or INTERACTION at all (_NO_SPAN_OF_KIND in
    rollups.py), so a session with tool spans needs its own interaction spans to have a
    non-zero turn count; count(*) of this kind is `turns`, no attribute required beyond
    session.id.
    """
    now = now or datetime.now(timezone.utc)
    spans = []
    for i in range(count):
        start = now + timedelta(seconds=i)
        end = start + timedelta(milliseconds=500)
        spans.append(
            trace.Span(
                trace_id=_trace_id(),
                span_id=_span_id(),
                name="claude_code.interaction",
                kind=trace.Span.SpanKind.SPAN_KIND_CLIENT,
                start_time_unix_nano=int(start.timestamp() * 1_000_000_000),
                end_time_unix_nano=int(end.timestamp() * 1_000_000_000),
                attributes=[_str_attr("session.id", session_id)],
            )
        )
    message = trace_svc.ExportTraceServiceRequest(
        resource_spans=[
            trace.ResourceSpans(
                resource=_resource(session_id, resource_project),
                scope_spans=[trace.ScopeSpans(spans=spans)],
            )
        ]
    )
    return _payload(message, len(spans))


def ndjson_bytes(events: Iterable[dict]) -> bytes:
    """NDJSON body: one JSON object per line, newline-terminated."""
    return ("\n".join(json.dumps(e) for e in events) + "\n").encode("utf-8")


def parse_discard(body: bytes, content_type: str, signal: str) -> tuple[int, str]:
    """(rejected count, error message) of an Export*ServiceResponse in either encoding.

    An empty protobuf body or a JSON object without partial_success means nothing rejected.
    """
    response_type, field = {
        "logs": (logs_svc.ExportLogsServiceResponse, "rejected_log_records"),
        "metrics": (metrics_svc.ExportMetricsServiceResponse, "rejected_data_points"),
        "traces": (trace_svc.ExportTraceServiceResponse, "rejected_spans"),
    }[signal]
    response = response_type()
    if content_type.split(";", 1)[0].strip().lower() == "application/json":
        json_format.Parse(body or b"{}", response, ignore_unknown_fields=True)
    else:
        response.ParseFromString(body)
    return getattr(
        response.partial_success, field
    ), response.partial_success.error_message
