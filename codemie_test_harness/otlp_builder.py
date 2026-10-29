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
) -> list[dict]:
    """The four events of one CLI session; every event carries codemie_project_name=project.

    project=None omits the key. event_ids are unique per session id, so a re-send of the
    same events is a duplicate for the BE, a new session id is new data.
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

    def event(event_type: str, offset_s: int, **fields) -> dict:
        timestamp = now + timedelta(seconds=offset_s)
        return {
            "type": event_type,
            "event_id": f"{event_type}:{session_id}",
            "timestamp": timestamp.isoformat(timespec="milliseconds").replace(
                "+00:00", "Z"
            ),
            **common,
            **fields,
        }

    return [
        event("agent.session.start", 0),
        event("agent.prompt.submit", 1, prompt_body=prompt),
        event(
            "agent.usage.request",
            2,
            request_id=f"req-{session_id}",
            model_raw="claude-sonnet-5-5",
            model="claude-sonnet-5-5",
            input_tokens=1,
            output_tokens=1,
            cache_read_tokens=0,
            stop_reason="end_turn",
            is_api_error=False,
        ),
        event("agent.session.end", 3),
    ]


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
