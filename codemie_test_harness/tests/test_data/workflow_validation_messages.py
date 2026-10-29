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

# Workflow validation error messages

# Common string constants to avoid duplication
INVALID_YAML_PROVIDED = "Invalid YAML config was provided:"
INVALID_YAML_CONFIG = "Invalid YAML config was provided"
INVALID_YAML_CONFIG_SCHEMA = "Configuration contains validation errors"
INVALID_YAML_CONFIG_CROSS_REF = "Configuration contains cross-reference errors"
INVALID_YAML_FORMAT = "Invalid YAML format was provided"
INVALID_YAML_FORMAT_JSON = "Invalid YAML format"
WORKFLOW_RESOURCES_NOT_EXIST = "Configuration references unavailable resources"
WORKFLOW_MUST_HAVE_STATE = "Workflow must have at least one valid state"

# Error types
ERROR_TYPE_SCHEMA_VALIDATION = "schema_validation"
ERROR_TYPE_RESOURCE_VALIDATION = "resource_validation"
ERROR_TYPE_CROSS_REFERENCE_VALIDATION = "cross_reference_validation"
ERROR_TYPE_PARSING = "parsing"
ERROR_TYPE_MISSING_STATES = "missing_states"

# Resource types
RESOURCE_TYPE_ASSISTANT = "assistant"
RESOURCE_TYPE_TOOL = "tool"
RESOURCE_TYPE_TOOL_FROM_ASSISTANT = "tool_from_assistant"
RESOURCE_TYPE_STATE = "state"
RESOURCE_TYPE_ASSISTANTS_0 = "assistants[0]"
RESOURCE_TYPE_TOOLS_0 = "tools[0]"
RESOURCE_TYPE_STATES_0 = "states[0]"

# Field names
FIELD_ID = "'id'"
FIELD_NAME = "'name'"
FIELD_TOOL = "'tool'"
FIELD_NEXT = "'next'"
FIELD_EXPRESSION = "'expression'"
FIELD_THEN = "'then'"
FIELD_OTHERWISE = "'otherwise'"
FIELD_CASES = "'cases'"
FIELD_DEFAULT = "'default'"
FIELD_CONDITION = "'condition'"
FIELD_STATE_ID = "'state_id'"
FIELD_SYSTEM_PROMPT = "'system_prompt'"
FIELD_ASSISTANT_ID = "'assistant_id'"
FIELD_TOOL_ID = "'tool_id'"
FIELD_CUSTOM_NODE_ID = "'custom_node_id'"
FIELD_WORKFLOW_ID = "'workflow_id'"

# Common phrases
IS_REQUIRED = "is required"
MUST_BE_SET = "must be set"
ONE_AND_ONLY_ONE_OF = "one and only one of"
AT_LEAST_ONE_OF = "at least one of"

# Field validation messages
FIELD_ID_REQUIRED = f"{FIELD_ID} {IS_REQUIRED}"
FIELD_NAME_REQUIRED = f"{FIELD_NAME} {IS_REQUIRED}"
FIELD_TOOL_REQUIRED = f"{FIELD_TOOL} {IS_REQUIRED}"
FIELD_NEXT_REQUIRED = f"{FIELD_NEXT} {IS_REQUIRED}"
FIELD_EXPRESSION_REQUIRED = f"{FIELD_EXPRESSION} {IS_REQUIRED}"
FIELD_THEN_REQUIRED = f"{FIELD_THEN} {IS_REQUIRED}"
FIELD_OTHERWISE_REQUIRED = f"{FIELD_OTHERWISE} {IS_REQUIRED}"
FIELD_CASES_REQUIRED = f"{FIELD_CASES} {IS_REQUIRED}"
FIELD_DEFAULT_REQUIRED = f"{FIELD_DEFAULT} {IS_REQUIRED}"
FIELD_CONDITION_REQUIRED = f"{FIELD_CONDITION} {IS_REQUIRED}"
FIELD_STATE_ID_REQUIRED = f"{FIELD_STATE_ID} {IS_REQUIRED}"

# Test resource IDs
STATE_COVERAGE = "coverage"
COVERAGE_ASSISTANT = "coverage_assistant"
INVALID_ASSISTANT_ID = "e3bb4613-d3ed-4391-8350-8702175b0e2x"
ANOTHER_ASSISTANT = "another_assistant"
INVALID_TOOL_ID = "Invalid-tool"
DATASOURCE_ID = "datasource_id"

# Error messages
MSG_ASSISTANT_NOT_EXIST_TEMPLATE = (
    "Assistant '{assistant_id}' (referenced as '{alias}') does not exist"
)
MSG_ASSISTANT_UNDEFINED = (
    f"{FIELD_ASSISTANT_ID} key references undefined '{{assistant_id}}' assistant"
)
MSG_TOOL_NOT_EXIST_TEMPLATE = (
    "Tool '{tool_id}' (referenced in assistant definition) does not exist"
)

# JSON error object generic message types (for 'message' field in error objects)
ERR_MSG_MISSING_REQUIRED_FIELD = "Missing required field"
ERR_MSG_RESOURCE_NOT_FOUND = "Resource not found"
ERR_MSG_INVALID_REFERENCE = "Invalid reference"
ERR_MSG_INVALID_VALUE = "Invalid value"
MSG_DATASOURCE_NOT_FOUND = (
    "Workflow can't be created because the following Assistants / Tools / "
    "Data sources do not exist: Data sources (referenced in assistant definitions) "
    "do not exist:datasource_id -> coverage_assistant (in state: coverage)"
)

ASSISTANT_NOT_EXIST = [
    f"Assistants do not exist:{COVERAGE_ASSISTANT} -> {INVALID_ASSISTANT_ID}"
]

ASSISTANT_NOT_EXIST_IN_STATE = [
    f"{INVALID_YAML_PROVIDED} 1) In '{STATE_COVERAGE}' state: {FIELD_ASSISTANT_ID} key references undefined '{ANOTHER_ASSISTANT}' assistant"
]

INVALID_YAML = [INVALID_YAML_FORMAT]

INVALID_DATA_SOURCE = [MSG_DATASOURCE_NOT_FOUND]

INVALID_TOOL = [
    f"Tools (referenced in assistant definitions) do not exist:{INVALID_TOOL_ID}"
]

INVALID_STATE = [
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {ONE_AND_ONLY_ONE_OF} {FIELD_CUSTOM_NODE_ID} or {FIELD_ASSISTANT_ID} or {FIELD_TOOL_ID} or {FIELD_WORKFLOW_ID} {MUST_BE_SET}",
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {ONE_AND_ONLY_ONE_OF} {FIELD_CUSTOM_NODE_ID} or {FIELD_ASSISTANT_ID} or {FIELD_WORKFLOW_ID} or {FIELD_TOOL_ID} {MUST_BE_SET}",
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {ONE_AND_ONLY_ONE_OF} {FIELD_CUSTOM_NODE_ID} or {FIELD_TOOL_ID} or {FIELD_ASSISTANT_ID} or {FIELD_WORKFLOW_ID} {MUST_BE_SET}",
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {ONE_AND_ONLY_ONE_OF} {FIELD_CUSTOM_NODE_ID} or {FIELD_TOOL_ID} or {FIELD_WORKFLOW_ID} or {FIELD_ASSISTANT_ID} {MUST_BE_SET}",
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {ONE_AND_ONLY_ONE_OF} {FIELD_CUSTOM_NODE_ID} or {FIELD_WORKFLOW_ID} or {FIELD_ASSISTANT_ID} or {FIELD_TOOL_ID} {MUST_BE_SET}",
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {ONE_AND_ONLY_ONE_OF} {FIELD_CUSTOM_NODE_ID} or {FIELD_WORKFLOW_ID} or {FIELD_TOOL_ID} or {FIELD_ASSISTANT_ID} {MUST_BE_SET}",
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {ONE_AND_ONLY_ONE_OF} {FIELD_ASSISTANT_ID} or {FIELD_CUSTOM_NODE_ID} or {FIELD_TOOL_ID} or {FIELD_WORKFLOW_ID} {MUST_BE_SET}",
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {ONE_AND_ONLY_ONE_OF} {FIELD_ASSISTANT_ID} or {FIELD_CUSTOM_NODE_ID} or {FIELD_WORKFLOW_ID} or {FIELD_TOOL_ID} {MUST_BE_SET}",
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {ONE_AND_ONLY_ONE_OF} {FIELD_ASSISTANT_ID} or {FIELD_TOOL_ID} or {FIELD_CUSTOM_NODE_ID} or {FIELD_WORKFLOW_ID} {MUST_BE_SET}",
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {ONE_AND_ONLY_ONE_OF} {FIELD_ASSISTANT_ID} or {FIELD_TOOL_ID} or {FIELD_WORKFLOW_ID} or {FIELD_CUSTOM_NODE_ID} {MUST_BE_SET}",
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {ONE_AND_ONLY_ONE_OF} {FIELD_ASSISTANT_ID} or {FIELD_WORKFLOW_ID} or {FIELD_CUSTOM_NODE_ID} or {FIELD_TOOL_ID} {MUST_BE_SET}",
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {ONE_AND_ONLY_ONE_OF} {FIELD_ASSISTANT_ID} or {FIELD_WORKFLOW_ID} or {FIELD_TOOL_ID} or {FIELD_CUSTOM_NODE_ID} {MUST_BE_SET}",
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {ONE_AND_ONLY_ONE_OF} {FIELD_TOOL_ID} or {FIELD_CUSTOM_NODE_ID} or {FIELD_ASSISTANT_ID} or {FIELD_WORKFLOW_ID} {MUST_BE_SET}",
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {ONE_AND_ONLY_ONE_OF} {FIELD_TOOL_ID} or {FIELD_CUSTOM_NODE_ID} or {FIELD_WORKFLOW_ID} or {FIELD_ASSISTANT_ID} {MUST_BE_SET}",
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {ONE_AND_ONLY_ONE_OF} {FIELD_TOOL_ID} or {FIELD_ASSISTANT_ID} or {FIELD_CUSTOM_NODE_ID} or {FIELD_WORKFLOW_ID} {MUST_BE_SET}",
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {ONE_AND_ONLY_ONE_OF} {FIELD_TOOL_ID} or {FIELD_ASSISTANT_ID} or {FIELD_WORKFLOW_ID} or {FIELD_CUSTOM_NODE_ID} {MUST_BE_SET}",
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {ONE_AND_ONLY_ONE_OF} {FIELD_TOOL_ID} or {FIELD_WORKFLOW_ID} or {FIELD_CUSTOM_NODE_ID} or {FIELD_ASSISTANT_ID} {MUST_BE_SET}",
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {ONE_AND_ONLY_ONE_OF} {FIELD_TOOL_ID} or {FIELD_WORKFLOW_ID} or {FIELD_ASSISTANT_ID} or {FIELD_CUSTOM_NODE_ID} {MUST_BE_SET}",
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {ONE_AND_ONLY_ONE_OF} {FIELD_WORKFLOW_ID} or {FIELD_CUSTOM_NODE_ID} or {FIELD_ASSISTANT_ID} or {FIELD_TOOL_ID} {MUST_BE_SET}",
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {ONE_AND_ONLY_ONE_OF} {FIELD_WORKFLOW_ID} or {FIELD_CUSTOM_NODE_ID} or {FIELD_TOOL_ID} or {FIELD_ASSISTANT_ID} {MUST_BE_SET}",
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {ONE_AND_ONLY_ONE_OF} {FIELD_WORKFLOW_ID} or {FIELD_ASSISTANT_ID} or {FIELD_CUSTOM_NODE_ID} or {FIELD_TOOL_ID} {MUST_BE_SET}",
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {ONE_AND_ONLY_ONE_OF} {FIELD_WORKFLOW_ID} or {FIELD_ASSISTANT_ID} or {FIELD_TOOL_ID} or {FIELD_CUSTOM_NODE_ID} {MUST_BE_SET}",
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {ONE_AND_ONLY_ONE_OF} {FIELD_WORKFLOW_ID} or {FIELD_TOOL_ID} or {FIELD_CUSTOM_NODE_ID} or {FIELD_ASSISTANT_ID} {MUST_BE_SET}",
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {ONE_AND_ONLY_ONE_OF} {FIELD_WORKFLOW_ID} or {FIELD_TOOL_ID} or {FIELD_ASSISTANT_ID} or {FIELD_CUSTOM_NODE_ID} {MUST_BE_SET}",
]

MISSING_STATES = [WORKFLOW_MUST_HAVE_STATE]

MISSING_ASSISTANT_ID = [
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_ASSISTANTS_0}': {FIELD_ID_REQUIRED}"
]

MISSING_SYSTEM_PROMPT = [
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_ASSISTANTS_0}': {AT_LEAST_ONE_OF} {FIELD_SYSTEM_PROMPT} or {FIELD_ASSISTANT_ID} {MUST_BE_SET}",
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_ASSISTANTS_0}': {AT_LEAST_ONE_OF} {FIELD_ASSISTANT_ID} or {FIELD_SYSTEM_PROMPT} {MUST_BE_SET}",
]

MISSING_TOOL_NAME = [
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_ASSISTANTS_0}.tools[0]': {FIELD_NAME_REQUIRED}"
]

MISSING_TOOLS_ID = [
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_TOOLS_0}': {FIELD_ID_REQUIRED}"
]

MISSING_TOOLS_NAME = [
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_TOOLS_0}': {FIELD_TOOL_REQUIRED}"
]

MISSING_STATES_ID = [
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {FIELD_ID_REQUIRED}"
]

MISSING_STATES_NEXT = [
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}': {FIELD_NEXT_REQUIRED}"
]

MISSING_STATES_NEXT_CONDITION_EXPRESSION = [
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}.next.condition': {FIELD_EXPRESSION_REQUIRED}"
]

MISSING_STATES_NEXT_CONDITION_THEN = [
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}.next.condition': {FIELD_THEN_REQUIRED}"
]

MISSING_STATES_NEXT_CONDITION_OTHERWISE = [
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}.next.condition': {FIELD_OTHERWISE_REQUIRED}"
]

MISSING_STATES_NEXT_SWITCH_CASES = [
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}.next.switch': {FIELD_CASES_REQUIRED}"
]

MISSING_STATES_NEXT_SWITCH_DEFAULT = [
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}.next.switch': {FIELD_DEFAULT_REQUIRED}"
]

MISSING_STATES_NEXT_SWITCH_CASES_CONDITION = [
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}.next.switch.cases[0]': {FIELD_CONDITION_REQUIRED}"
]

MISSING_STATES_NEXT_SWITCH_CASES_STATE_ID = [
    f"{INVALID_YAML_PROVIDED} 1) In '{RESOURCE_TYPE_STATES_0}.next.switch.cases[0]': {FIELD_STATE_ID_REQUIRED}"
]

INVALID_YAML_FORMAT_PROVIDED = [INVALID_YAML_FORMAT]


# JSON Error Format Expected Structures (for error_format=json)

JSON_INVALID_ASSISTANT_ID = {
    "error_type": ERROR_TYPE_RESOURCE_VALIDATION,
    "message": WORKFLOW_RESOURCES_NOT_EXIST,
    "errors": [
        {
            "message": ERR_MSG_RESOURCE_NOT_FOUND,
            "path": "assistant_id",
            "details": f"Assistant '{INVALID_ASSISTANT_ID}' does not exist",
            "state_id": STATE_COVERAGE,
        }
    ],
}

JSON_INVALID_ASSISTANT_IN_STATE = {
    "error_type": ERROR_TYPE_CROSS_REFERENCE_VALIDATION,
    "message": INVALID_YAML_CONFIG_CROSS_REF,
    "errors": [
        {
            "message": ERR_MSG_INVALID_REFERENCE,
            "path": "assistant_id",
            "details": f"Assistant '{ANOTHER_ASSISTANT}' not found",
            "state_id": STATE_COVERAGE,
        }
    ],
}

JSON_INVALID_YAML = {
    "error_type": ERROR_TYPE_PARSING,
    "message": INVALID_YAML_FORMAT_JSON,
}

JSON_INVALID_DATA_SOURCE = {
    "error_type": ERROR_TYPE_RESOURCE_VALIDATION,
    "message": WORKFLOW_RESOURCES_NOT_EXIST,
    "errors": [
        {
            "message": ERR_MSG_RESOURCE_NOT_FOUND,
            "path": "datasource_ids",
            "details": f"Datasource '{DATASOURCE_ID}' (used by assistant '{COVERAGE_ASSISTANT}') does not exist",
            "state_id": STATE_COVERAGE,
        }
    ],
}

JSON_INVALID_TOOL = {
    "error_type": ERROR_TYPE_RESOURCE_VALIDATION,
    "message": WORKFLOW_RESOURCES_NOT_EXIST,
    "errors": [
        {
            "message": ERR_MSG_RESOURCE_NOT_FOUND,
            "path": "tools",
            "details": f"Tool '{INVALID_TOOL_ID}' (referenced in assistant '{COVERAGE_ASSISTANT}') does not exist",
        }
    ],
}

JSON_INVALID_STATE = {
    "error_type": ERROR_TYPE_SCHEMA_VALIDATION,
    "message": INVALID_YAML_CONFIG_SCHEMA,
    "errors": [
        {
            "message": ERR_MSG_INVALID_VALUE,
            "path": "",
            # Multiple variations due to field order
            "details_any": [
                "Must set one of: custom_node_id or assistant_id or tool_id or workflow_id",
                "Must set one of: custom_node_id or assistant_id or workflow_id or tool_id",
                "Must set one of: custom_node_id or tool_id or assistant_id or workflow_id",
                "Must set one of: custom_node_id or tool_id or workflow_id or assistant_id",
                "Must set one of: custom_node_id or workflow_id or assistant_id or tool_id",
                "Must set one of: custom_node_id or workflow_id or tool_id or assistant_id",
                "Must set one of: assistant_id or custom_node_id or tool_id or workflow_id",
                "Must set one of: assistant_id or custom_node_id or workflow_id or tool_id",
                "Must set one of: assistant_id or tool_id or custom_node_id or workflow_id",
                "Must set one of: assistant_id or tool_id or workflow_id or custom_node_id",
                "Must set one of: assistant_id or workflow_id or custom_node_id or tool_id",
                "Must set one of: assistant_id or workflow_id or tool_id or custom_node_id",
                "Must set one of: tool_id or custom_node_id or assistant_id or workflow_id",
                "Must set one of: tool_id or custom_node_id or workflow_id or assistant_id",
                "Must set one of: tool_id or assistant_id or custom_node_id or workflow_id",
                "Must set one of: tool_id or assistant_id or workflow_id or custom_node_id",
                "Must set one of: tool_id or workflow_id or custom_node_id or assistant_id",
                "Must set one of: tool_id or workflow_id or assistant_id or custom_node_id",
                "Must set one of: workflow_id or custom_node_id or assistant_id or tool_id",
                "Must set one of: workflow_id or custom_node_id or tool_id or assistant_id",
                "Must set one of: workflow_id or assistant_id or custom_node_id or tool_id",
                "Must set one of: workflow_id or assistant_id or tool_id or custom_node_id",
                "Must set one of: workflow_id or tool_id or custom_node_id or assistant_id",
                "Must set one of: workflow_id or tool_id or assistant_id or custom_node_id",
            ],
            "state_id": STATE_COVERAGE,
        }
    ],
}

JSON_MISSING_STATES = {
    "error_type": ERROR_TYPE_MISSING_STATES,
    "message": WORKFLOW_MUST_HAVE_STATE,
}

JSON_MISSING_ASSISTANT_ID = {
    "error_type": ERROR_TYPE_SCHEMA_VALIDATION,
    "message": INVALID_YAML_CONFIG_SCHEMA,
    "errors": [
        {
            "message": ERR_MSG_MISSING_REQUIRED_FIELD,
            "path": "id",
            "details": "Required fields: id",
        }
    ],
}

JSON_MISSING_SYSTEM_PROMPT = {
    "error_type": ERROR_TYPE_SCHEMA_VALIDATION,
    "message": INVALID_YAML_CONFIG_SCHEMA,
    "errors": [
        {
            "message": ERR_MSG_INVALID_VALUE,
            "path": "assistants",
            # Multiple variations due to field order
            "details_any": [
                "Must set one of: system_prompt or assistant_id",
                "Must set one of: assistant_id or system_prompt",
            ],
            "state_id": STATE_COVERAGE,
        }
    ],
}

JSON_MISSING_TOOL_NAME = {
    "error_type": ERROR_TYPE_SCHEMA_VALIDATION,
    "message": INVALID_YAML_CONFIG_SCHEMA,
    "errors": [
        {
            "message": ERR_MSG_MISSING_REQUIRED_FIELD,
            "path": "tools.name",
            "details": "Required fields: name",
            "state_id": STATE_COVERAGE,
        }
    ],
}

JSON_MISSING_TOOLS_ID = {
    "error_type": ERROR_TYPE_SCHEMA_VALIDATION,
    "message": INVALID_YAML_CONFIG_SCHEMA,
    "errors": [
        {
            "message": ERR_MSG_MISSING_REQUIRED_FIELD,
            "path": "id",
            "details": "Required fields: id",
        }
    ],
}

JSON_MISSING_TOOLS_NAME = {
    "error_type": ERROR_TYPE_SCHEMA_VALIDATION,
    "message": INVALID_YAML_CONFIG_SCHEMA,
    "errors": [
        {
            "message": ERR_MSG_MISSING_REQUIRED_FIELD,
            "path": "tool",
            "details": "Required fields: tool",
        }
    ],
}

JSON_MISSING_STATES_ID = {
    "error_type": ERROR_TYPE_SCHEMA_VALIDATION,
    "message": INVALID_YAML_CONFIG_SCHEMA,
    "errors": [
        {
            "message": ERR_MSG_MISSING_REQUIRED_FIELD,
            "path": "id",
            "details": "Required fields: id",
        }
    ],
}

JSON_MISSING_STATES_NEXT = {
    "error_type": ERROR_TYPE_SCHEMA_VALIDATION,
    "message": INVALID_YAML_CONFIG_SCHEMA,
    "errors": [
        {
            "message": ERR_MSG_MISSING_REQUIRED_FIELD,
            "path": "next",
            "details": "Required fields: next",
            "state_id": STATE_COVERAGE,
        }
    ],
}

JSON_MISSING_STATES_NEXT_CONDITION_EXPRESSION = {
    "error_type": ERROR_TYPE_SCHEMA_VALIDATION,
    "message": INVALID_YAML_CONFIG_SCHEMA,
    "errors": [
        {
            "message": ERR_MSG_MISSING_REQUIRED_FIELD,
            "path": "next.condition.expression",
            "details": "Required fields: expression",
            "state_id": STATE_COVERAGE,
        }
    ],
}

JSON_MISSING_STATES_NEXT_CONDITION_THEN = {
    "error_type": ERROR_TYPE_SCHEMA_VALIDATION,
    "message": INVALID_YAML_CONFIG_SCHEMA,
    "errors": [
        {
            "message": ERR_MSG_MISSING_REQUIRED_FIELD,
            "path": "next.condition.then",
            "details": "Required fields: then",
            "state_id": STATE_COVERAGE,
        }
    ],
}

JSON_MISSING_STATES_NEXT_CONDITION_OTHERWISE = {
    "error_type": ERROR_TYPE_SCHEMA_VALIDATION,
    "message": INVALID_YAML_CONFIG_SCHEMA,
    "errors": [
        {
            "message": ERR_MSG_MISSING_REQUIRED_FIELD,
            "path": "next.condition.otherwise",
            "details": "Required fields: otherwise",
            "state_id": STATE_COVERAGE,
        }
    ],
}

JSON_MISSING_STATES_NEXT_SWITCH_CASES = {
    "error_type": ERROR_TYPE_SCHEMA_VALIDATION,
    "message": INVALID_YAML_CONFIG_SCHEMA,
    "errors": [
        {
            "message": ERR_MSG_MISSING_REQUIRED_FIELD,
            "path": "next.switch.cases",
            "details": "Required fields: cases",
            "state_id": STATE_COVERAGE,
        }
    ],
}

JSON_MISSING_STATES_NEXT_SWITCH_DEFAULT = {
    "error_type": ERROR_TYPE_SCHEMA_VALIDATION,
    "message": INVALID_YAML_CONFIG_SCHEMA,
    "errors": [
        {
            "message": ERR_MSG_MISSING_REQUIRED_FIELD,
            "path": "next.switch.default",
            "details": "Required fields: default",
            "state_id": STATE_COVERAGE,
        }
    ],
}

JSON_MISSING_STATES_NEXT_SWITCH_CASES_CONDITION = {
    "error_type": ERROR_TYPE_SCHEMA_VALIDATION,
    "message": INVALID_YAML_CONFIG_SCHEMA,
    "errors": [
        {
            "message": ERR_MSG_MISSING_REQUIRED_FIELD,
            "path": "next.switch.cases[0].condition",
            "details": "Required fields: condition",
            "state_id": STATE_COVERAGE,
        }
    ],
}

JSON_MISSING_STATES_NEXT_SWITCH_CASES_STATE_ID = {
    "error_type": ERROR_TYPE_SCHEMA_VALIDATION,
    "message": INVALID_YAML_CONFIG_SCHEMA,
    "errors": [
        {
            "message": ERR_MSG_MISSING_REQUIRED_FIELD,
            "path": "next.switch.cases[0].state_id",
            "details": "Required fields: state_id",
            "state_id": STATE_COVERAGE,
        }
    ],
}

JSON_INVALID_YAML_FORMAT = {
    "error_type": ERROR_TYPE_PARSING,
    "message": INVALID_YAML_FORMAT_JSON,
    "errors": [
        {
            "message": "YAML parsing failed",
            "details": "Error occured while attempting to read YAML",
        }
    ],
}
