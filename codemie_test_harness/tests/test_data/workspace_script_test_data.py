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

"""Test data for workspace scripts run from workflows and assistants.

Run a Script from a Workflow Step.
Scripts Can Call Platform Tools.

Scripts are templates: ``__MARKER__`` and ``__HEX__`` are replaced per run so one run's
output can never be mistaken for another's. Use ``render_script``.
"""

import json

# Runtime feature flag (customer config component) that switches tool calling from scripts on.
FEATURE_COMPONENT_ID = "features:workspaceScriptBridge"

JIRA_TOOL = "generic_jira_tool"
CONFLUENCE_TOOL = "generic_confluence_tool"

# Marker the matrix script prints before the JSON of its results.
MATRIX_MARKER = "MATRIX"

SCOPE_MARKER = "SCOPE"
NO_CONTEXT_MARKER = "NOCTX"
WHOAMI_MARKER = "WHOAMI"
SWITCH_MARKER = "SWITCH"
DENY_MARKER = "DENY"

# Save-time refusal of a tool_access list (the error_detail message the workflow validator emits).
# The live API returns "Tool access is invalid" (not "Invalid tool access") embedded in a longer
# "<br>Workflow can't be created because the following Assistants / Tools / Data sources do not
# exist: <br>Tool access is invalid:<br>Step '<step>': <reason><br>" message — match that wording.
INVALID_TOOL_ACCESS_MESSAGE = "Tool access is invalid"

# Text that is present in the matrix script source, used as a positive control for grep.
MATRIX_SOURCE_PROBE = "issue/NOPE-1"

# Error codes of the script SDK that the tests rely on.
CODE_TOOL_UNAVAILABLE = "tool_unavailable"
CODE_TOOL_BLOCKED = "tool_blocked"
CODE_BAD_ARGUMENTS = "bad_arguments"
CODE_NO_CONTEXT = "no_context"
CODE_UNAVAILABLE = "unavailable"


def render_script(template: str, marker: str = "", hex_value: str = "") -> str:
    return template.replace("__MARKER__", marker).replace("__HEX__", hex_value)


ECHO_SCRIPT = """\
print("ECHO-__MARKER__")
"""

WRITE_FILE_SCRIPT = """\
with open("result.txt", "w") as handle:
    handle.write("FILE-__MARKER__")
print("WROTE-__MARKER__")
"""

FAILING_SCRIPT = """\
print("BEFORE-FAIL-__MARKER__")
raise RuntimeError("BOOM-__MARKER__")
"""

# One run exercises every scenario of a script that calls platform tools in a workflow tool step.
# Each scenario's outcome is printed as one JSON object so the tests can assert on them separately.
# The request sentinel is built at runtime from two literals so it never appears in the script source.
TOOL_CALLING_MATRIX_SCRIPT = """\
import json
from codemie_runtime_sdk import call_tool, call_tools, ToolCallError

JIRA = "generic_jira_tool"
ME = {"method": "GET", "relative_url": "/rest/api/2/myself"}
INFO = {"method": "GET", "relative_url": "/rest/api/2/serverInfo"}
SENTINEL = "SENT-" + "__HEX__"
results = {}


def describe(item):
    if isinstance(item, ToolCallError):
        return {"error": error_dict(item)}
    result = item["result"]
    return {
        "status": (item.get("http") or {}).get("status"),
        "type": type(result).__name__,
        "keys": sorted(result) if isinstance(result, dict) else None,
    }


def error_dict(error):
    return {
        "code": error.code,
        "retryable": error.retryable,
        "may_have_run": error.may_have_run,
        "message": str(error),
    }


def scenario(label, call):
    try:
        results[label] = describe(call())
    except ToolCallError as error:
        results[label] = {"error": error_dict(error)}


scenario("me", lambda: call_tool(JIRA, ME))
scenario("info", lambda: call_tool(JIRA, INFO))
scenario("unknown_tool", lambda: call_tool("no_such_tool", {}))
scenario("script_tool", lambda: call_tool("execute_workspace_script", {"script_path": "x.py"}))
scenario("bad_arguments", lambda: call_tool(JIRA, {"methodd": "GET"}))
results["batch"] = [
    describe(item)
    for item in call_tools(
        [
            {"name": JIRA, "args": ME},
            {"name": "no_such_tool", "args": {}},
            {"name": JIRA, "args": INFO},
        ]
    )
]
scenario("sentinel", lambda: call_tool(JIRA, {"method": "GET", "relative_url": "/rest/api/2/issue/NOPE-1?x=" + SENTINEL}))
print("MATRIX=" + json.dumps(results))
"""

# Calls a Jira tool and a Confluence tool; used where only one of the two is in scope.
SCOPE_PROBE_SCRIPT = """\
import json
from codemie_runtime_sdk import call_tool, ToolCallError

results = {}
calls = {
    "jira": ("generic_jira_tool", {"method": "GET", "relative_url": "/rest/api/2/myself"}),
    "confluence": ("generic_confluence_tool", {"method": "GET", "relative_url": "/rest/api/space", "params": "limit=1"}),
}
for label, (name, args) in calls.items():
    try:
        envelope = call_tool(name, args)
        results[label] = {"status": (envelope.get("http") or {}).get("status")}
    except ToolCallError as error:
        results[label] = {"error": {"code": error.code}}
print("SCOPE=" + json.dumps(results))
"""

# Calls a tool without any assistant or workflow context (direct run of a workspace script).
NO_CONTEXT_SCRIPT = """\
import json
from codemie_runtime_sdk import call_tool, ToolCallError

try:
    call_tool("generic_jira_tool", {"method": "GET", "relative_url": "/rest/api/2/myself"})
    outcome = {"status": "called"}
except ToolCallError as error:
    outcome = {"error": {"code": error.code}}
print("NOCTX=" + json.dumps(outcome))
"""

# Used for the tool-calling switch check: the script reports whatever the SDK does.
SWITCH_PROBE_SCRIPT = """\
import json

try:
    from codemie_runtime_sdk import call_tool, ToolCallError
except ImportError as error:
    print("SWITCH=" + json.dumps({"import_error": str(error)}))
else:
    try:
        call_tool("generic_jira_tool", {"method": "GET", "relative_url": "/rest/api/2/myself"})
        print("SWITCH=" + json.dumps({"status": "called"}))
    except ToolCallError as error:
        print("SWITCH=" + json.dumps({"error": {"code": error.code, "message": str(error)}}))
"""

# File references that the shape rule must reject (name, description). Owner is the caller's own id.
UNSAFE_FILE_NAMES = [
    ("/etc/passwd", "absolute-path"),
    ("../other-owner/secret.txt", "parent-traversal"),
    ("folder\\file.txt", "backslash"),
    (".", "bare-dot"),
    ("name\x01.txt", "control-character"),
    ("", "empty-name"),
]

# Cap on files for one run request (backend default).
RUN_FILES_MAX_COUNT = 20

# Reports which Jira account the tool call used, through the HTTP status of the answer.
WHOAMI_SCRIPT = """\
import json
from codemie_runtime_sdk import call_tool, ToolCallError

try:
    envelope = call_tool("generic_jira_tool", {"method": "GET", "relative_url": "/rest/api/2/myself"})
    outcome = {"status": (envelope.get("http") or {}).get("status")}
except ToolCallError as error:
    outcome = {"error": {"code": error.code}}
print("WHOAMI=" + json.dumps(outcome))
"""

# Calls one tool with the given args and reports only whether the call went through or which code refused it.
DENY_PROBE_SCRIPT = """\
import json
from codemie_runtime_sdk import call_tool, ToolCallError

try:
    call_tool("__TOOL__", __ARGS__)
    outcome = {"status": "called"}
except ToolCallError as error:
    outcome = {"error": {"code": error.code}}
print("DENY=" + json.dumps(outcome))
"""

CONFLUENCE_SPACE_ARGS = {
    "method": "GET",
    "relative_url": "/rest/api/space",
    "params": "limit=1",
}
JIRA_MYSELF_ARGS = {"method": "GET", "relative_url": "/rest/api/2/myself"}


def render_deny_probe(tool: str, args: dict) -> str:
    return DENY_PROBE_SCRIPT.replace("__TOOL__", tool).replace(
        "__ARGS__", json.dumps(args)
    )


# Tools a script must never call, grouped by family: (family, tool name).
EXCLUDED_TOOLS = [
    ("code-executor", "code_executor"),
    ("code-executor", "generate_image_tool"),
    ("file-analysis", "file_analysis"),
    ("file-analysis", "pptx_tool"),
    ("file-analysis", "pdf_tool"),
    ("file-analysis", "csv_tool"),
    ("file-analysis", "excel_tool"),
    ("file-analysis", "docx_tool"),
    ("file-analysis", "email_analysis_tool"),
    ("agent-workspace", "list_workspace_files"),
    ("agent-workspace", "read_workspace_file"),
    ("agent-workspace", "write_workspace_file"),
    ("agent-workspace", "edit_workspace_file"),
    ("agent-workspace", "delete_workspace_file"),
    ("agent-workspace", "grep_workspace_files"),
    ("agent-workspace", "generate_workspace_image_v2"),
    ("agent-workspace", "inspect_workspace_image"),
    ("filesystem", "read_file_from_file_system"),
    ("filesystem", "list_directory_from_file_system"),
    ("filesystem", "write_file_to_file_system"),
    ("filesystem", "diff_update_file_tool"),
    ("filesystem", "str_replace_editor"),
    ("filesystem", "run_command_line_tool"),
    ("platform", "get_assistants"),
    ("platform", "get_conversation_metrics"),
    ("platform", "get_raw_conversations"),
    ("platform", "get_spending"),
    ("platform", "get_key_spending"),
    ("platform", "get_conversation_analytics"),
    ("code-exploration", "get_code"),
    ("code-exploration", "read_resource"),
    ("code-exploration", "cypher_query"),
    ("code-exploration", "list_datasources"),
    ("user-input", "request_user_input"),
]

# Tools the assistant of the assistant-scope test has configured, yet the script must not call.
# The MCP server is the "Time MCP server" of the test data; its tools are listed here by name.
ASSISTANT_CONFIGURED_EXCLUDED_TOOLS = [
    ("agent-workspace", "list_workspace_files"),
    ("agent-workspace", "read_workspace_file"),
    ("agent-workspace", "write_workspace_file"),
    ("code-executor", "code_executor"),
    ("code-executor", "generate_image_tool"),
    ("file-analysis", "file_analysis"),
    ("file-analysis", "pdf_tool"),
    ("platform", "get_assistants"),
    ("platform", "get_spending"),
    ("mcp", "get_current_time"),
    ("mcp", "convert_time"),
]

CODES_MARKER = "CODES"

# Calls every named tool with no arguments and records the error code each call gets (CALLED when
# the call went through), then calls Jira as a control that the script can call tools at all.
EXCLUDED_TOOLS_PROBE_SCRIPT = """\
import json
from codemie_runtime_sdk import call_tool, ToolCallError

codes = {}
for name in __NAMES__:
    try:
        call_tool(name, {})
        codes[name] = "CALLED"
    except ToolCallError as error:
        codes[name] = error.code
control = call_tool("generic_jira_tool", {"method": "GET", "relative_url": "/rest/api/2/myself"})
print("CODES=" + json.dumps({"tools": codes, "control": (control.get("http") or {}).get("status")}))
"""


def render_excluded_tools_probe(tool_names: list[str]) -> str:
    return EXCLUDED_TOOLS_PROBE_SCRIPT.replace("__NAMES__", json.dumps(tool_names))
