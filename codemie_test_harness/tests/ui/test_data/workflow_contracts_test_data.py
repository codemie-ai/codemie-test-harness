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

"""Test data for the workflow contract controls and the Issues panel of the editor.

Each builder returns workflow YAML whose save-time contract check gives a known outcome.
Input and output contracts are JSON text, not YAML mappings: the backend types
``input_schema`` / ``output_schema`` as strings, and a mapping fails the YAML type check
before any contract runs.

Outcomes in the default ``warn`` mode (backend contract policy):

- a placeholder whose key an earlier state produced and a later one removed gives a
  WARNING and the save goes through;
- a key a state declares in its input contract that was removed before it runs gives an
  ERROR and the save is rejected;
- a key that reaches its consumer through a state with no output contract gives an
  UNVERIFIED finding, which never blocks the save;
- ``save_validation: strict`` (workflow or state level) turns every finding into an error.
"""

import json
from dataclasses import dataclass
from typing import Callable, Optional

from codemie_test_harness.tests.utils.yaml_utils import (
    AssistantModel,
    StateModel,
    prepare_yaml_content,
)

# ---------------------------------------------------------------------------
# State ids. The backend names them in its messages, so the expected texts below use them.
# ---------------------------------------------------------------------------
# /v1/config component behind the contract controls, the Issues panel and Check.
WORKFLOW_CONTRACTS_COMPONENT_ID = "features:workflowContracts"

ASSISTANT_ID = "contract_assistant"
PRODUCER_STATE_ID = "s1"
RESETTING_STATE_ID = "s2"
WARNING_STATE_ID = "c1"
DECLARING_STATE_ID = "c2"
DOC_PRODUCER_STATE_ID = "a"
DOC_PASSTHROUGH_STATE_ID = "middle"
DOC_CONSUMER_STATE_ID = "b"
TRANSFORM_STATE_ID = "source"
CLEAN_STATE_ID = "writer"

# Key produced by s1, removed by s2 and needed by c1 (and c2 in the rejected recipes).
REMOVED_KEY = "x"
# Key produced by ``a`` and needed by ``b`` through ``middle``, which has no contract.
UNVERIFIED_KEY = "doc"

# ---------------------------------------------------------------------------
# Texts the editor shows (frontend IssueGroups.tsx, IssuesPanel.tsx, EditWorkflowPage.tsx,
# useContractCheck.ts, EditWorkflowHeaderActions.tsx); messages from the backend as the
# stand returned them on the recon walk.
# ---------------------------------------------------------------------------
REMOVED_KEY_MESSAGE = (
    f"'{REMOVED_KEY}' needed by state '{WARNING_STATE_ID}' is removed before it runs"
)
REMOVED_KEY_FIELD_WARNING = (
    f"{REMOVED_KEY_MESSAGE}. Removed by '{RESETTING_STATE_ID}' through "
    "reset_keys_in_context_store."
)
UNVERIFIED_KEY_MESSAGE = f"The type of '{UNVERIFIED_KEY}' needed by state '{DOC_CONSUMER_STATE_ID}' cannot be verified"
TRANSFORM_FORM_ERROR_MESSAGE = f"State '{TRANSFORM_STATE_ID}' feeds other states, but its output contract is not a JSON schema"
TRANSFORM_OUTPUT_SCHEMA_YAML_KEY = "output_schema:"

SAVED_WITH_WARNINGS_NOTE = "Saved with warnings"
CREATED_WITH_WARNINGS_NOTE = "Workflow created with warnings"
NOT_SAVED_NOTE = "Changes not saved yet"
WORKFLOW_STRICT_LINE = "Blocked by the workflow-level save validation (strict)"
STATE_STRICT_TAG = "node save validation (strict)"
SAVED_WITH_ONE_WARNING_TOAST = "Workflow saved with 1 warning"
WARNED_SAVE_TOAST_PREFIX = "Workflow saved with"
NO_ISSUES_FOUND_TOAST = "No issues found"
RESOLVED_BADGE = "Resolved"

# Issue group labels and the Issues button colours (issueSeverity.ts).
ERRORS_GROUP = "Errors"
WARNINGS_GROUP = "Warnings"
UNVERIFIED_GROUP = "Unverified"
SEVERITY_RED = "red"
SEVERITY_AMBER = "amber"
SEVERITY_GREY = "grey"

# Save validation option written by the workflow-level selector (contractModes.ts).
WARN_MODE = "warn"
SAVE_VALIDATION_KEY = "save_validation"
LEGACY_VALIDATION_KEY = "validation"

# Recipe 6: 110 placeholders that are never produced give 110 UNVERIFIED findings; the
# backend lists the first 100 (CONTRACT_WARNINGS_CAP) and reports the rest as truncated.
TRUNCATION_PLACEHOLDER_COUNT = 110
LISTED_WARNINGS_CAP = 100
TRUNCATED_WARNINGS_LINE = (
    f"{TRUNCATION_PLACEHOLDER_COUNT - LISTED_WARNINGS_CAP} more warnings not shown"
)

# Coverage of the one-state clean workflow, as the stand reported it on Check.
CLEAN_WORKFLOW_COVERAGE = "Input contract coverage: 0 of 1 states"
# UNVERIFIED-only workflow on Check: one state, ``b``, cannot be verified.
UNVERIFIED_ONLY_TOAST = "1 states could not be verified"


def _object_schema(*keys: str) -> str:
    """JSON-schema text of an object that requires every key in ``keys`` as a string."""
    return json.dumps(
        {
            "type": "object",
            "properties": {key: {"type": "string"} for key in keys},
            "required": list(keys),
        }
    )


# Input contract typed into c2's panel by the rejected-save test: c2 needs the removed key.
DECLARED_REMOVED_KEY_INPUT_CONTRACT = _object_schema(REMOVED_KEY)


def _assistant(model: str) -> dict:
    return {"id": ASSISTANT_ID, "model": model, "system_prompt": "Answer briefly."}


def _state(state_id: str, next_state: str, **fields) -> dict:
    return {
        "id": state_id,
        "assistant_id": ASSISTANT_ID,
        **fields,
        "next": {"state_id": next_state},
    }


def _warning_chain(next_state: str, warning_state_output: Optional[str] = None) -> list:
    """s1 produces ``x``, s2 removes it, c1 reads ``{{ x }}`` in its task: one WARNING on c1."""
    producer = _state(
        PRODUCER_STATE_ID, RESETTING_STATE_ID, output_schema=_object_schema(REMOVED_KEY)
    )
    resetting = _state(RESETTING_STATE_ID, WARNING_STATE_ID)
    resetting["next"]["reset_keys_in_context_store"] = [REMOVED_KEY]
    warning_fields = {
        "task": f"use {{{{ {REMOVED_KEY} }}}}",
        "resolve_dynamic_values_in_prompt": True,
    }
    if warning_state_output:
        warning_fields["output_schema"] = warning_state_output
    return [producer, resetting, _state(WARNING_STATE_ID, next_state, **warning_fields)]


def _unverified_chain(next_state: str = "end") -> list:
    """``a`` produces ``doc``, ``middle`` has no contract, ``b`` declares ``doc``: one UNVERIFIED."""
    return [
        _state(
            DOC_PRODUCER_STATE_ID,
            DOC_PASSTHROUGH_STATE_ID,
            output_schema=_object_schema(UNVERIFIED_KEY),
        ),
        _state(DOC_PASSTHROUGH_STATE_ID, DOC_CONSUMER_STATE_ID),
        _state(
            DOC_CONSUMER_STATE_ID,
            next_state,
            input_schema=_object_schema(UNVERIFIED_KEY),
        ),
    ]


def _dump(model: str, states: list, **top_level) -> str:
    return prepare_yaml_content(
        {**top_level, "assistants": [_assistant(model)], "states": states}
    )


def build_clean_yaml(model: str) -> str:
    """One assistant state and no contracts: the save is clean."""
    return _dump(model, [_state(CLEAN_STATE_ID, "end")])


def build_warning_only_yaml(model: str) -> str:
    """Recipe 1 (recon-confirmed): one WARNING on c1, the save goes through (2xx)."""
    return _dump(model, _warning_chain("end"))


def build_warning_resolved_yaml(model: str) -> str:
    """Recipe 1 after the author fixed c1: its task no longer reads the removed key."""
    chain = _warning_chain("end")
    chain[-1]["task"] = "use the request"
    return _dump(model, chain)


def build_unverified_only_yaml(model: str) -> str:
    """Recipe 2 (recon-confirmed): one UNVERIFIED on ``b``, the save is clean."""
    return _dump(model, _unverified_chain())


def build_error_and_unverified_yaml(model: str) -> str:
    """Recipe 3 (recon-confirmed): c1 declares the removed ``x`` (ERROR, save rejected), and
    ``doc`` reaches ``b`` unverified. Recon saw "Errors (1)" and "Unverified (2)"."""
    chain = _warning_chain(DOC_PRODUCER_STATE_ID)
    chain[-1]["input_schema"] = _object_schema(REMOVED_KEY)
    chain[-1]["task"] = "use {{ missing_warning }}"
    return _dump(model, chain + _unverified_chain())


def build_warning_and_unverified_yaml(model: str) -> str:
    """WARNING on c1 and UNVERIFIED on ``b``; the save goes through (2xx).

    c2, between them, has no input contract yet: the rejected-save test types one into its
    panel. c1 carries an output contract without ``x``, so the removed key stays removed when
    it reaches c2 (assumed: composition of recipes 1 and 3, not run on the stand as a whole).
    """
    chain = _warning_chain(DECLARING_STATE_ID, warning_state_output=_object_schema("y"))
    chain.append(_state(DECLARING_STATE_ID, DOC_PRODUCER_STATE_ID))
    return _dump(model, chain + _unverified_chain())


def build_all_severities_yaml(model: str) -> str:
    """ERROR (c2 declares the removed ``x``), WARNING (c1) and UNVERIFIED (``b``); rejected.

    Same graph as ``build_warning_and_unverified_yaml`` with c2's input contract already set
    (assumed composition, see there).
    """
    chain = _warning_chain(DECLARING_STATE_ID, warning_state_output=_object_schema("y"))
    chain.append(
        _state(
            DECLARING_STATE_ID,
            DOC_PRODUCER_STATE_ID,
            input_schema=DECLARED_REMOVED_KEY_INPUT_CONTRACT,
        )
    )
    return _dump(model, chain + _unverified_chain())


def build_workflow_strict_yaml(model: str) -> str:
    """Recipe 4a (recon-confirmed): recipe 1 under workflow-level ``save_validation: strict``."""
    return _dump(model, _warning_chain("end"), save_validation="strict")


def build_state_strict_yaml(model: str) -> str:
    """Recipe 4b (recon-confirmed): recipe 1 with ``save_validation: strict`` on c1 only."""
    chain = _warning_chain("end")
    chain[-1]["save_validation"] = "strict"
    return _dump(model, chain)


def build_transform_example_output_yaml(model: str) -> str:
    """Recipe 5 (recon-confirmed): a Transform state whose output contract is an example, not
    a schema, under workflow strict. The finding sits on ``output_schema`` of a Transform node,
    which has no control in the node panel, so Go to Issue opens the YAML editor."""
    return prepare_yaml_content(
        {
            "save_validation": "strict",
            "custom_nodes": [
                {
                    "id": TRANSFORM_STATE_ID,
                    "custom_node_id": "transform_node",
                    "config": {
                        "input_source": "context_store",
                        "mappings": [
                            {
                                "output_field": "items",
                                "type": "constant",
                                "value": [{"x": "first"}],
                            }
                        ],
                    },
                }
            ],
            "states": [
                {
                    "id": TRANSFORM_STATE_ID,
                    "custom_node_id": TRANSFORM_STATE_ID,
                    "output_schema": json.dumps({"x": "example"}),
                    "next": {"state_id": "end"},
                }
            ],
        }
    )


def build_truncated_warnings_yaml(model: str) -> str:
    """Recipe 6 (recon-confirmed): c1's task reads 110 keys nobody produces; the stand listed
    100 UNVERIFIED findings and "10 more warnings not shown". The save goes through."""
    chain = _warning_chain("end")
    chain[-1]["task"] = "use " + " ".join(
        f"{{{{ missing_{index} }}}}" for index in range(TRUNCATION_PLACEHOLDER_COUNT)
    )
    return _dump(model, chain)


def contract_warning_assistants_and_states(
    model: str,
) -> tuple[list[AssistantModel], list[StateModel]]:
    """Recipe 1 as YAML models, for workflows built from models (``create_script_workflow``).

    The first state is ``PRODUCER_STATE_ID``; point the previous state's ``next`` at it.
    """
    assistant = AssistantModel(
        id=ASSISTANT_ID, model=model, system_prompt="Answer briefly."
    )
    states = [
        StateModel(id=state["id"], **{k: v for k, v in state.items() if k != "id"})
        for state in _warning_chain("end")
    ]
    return [assistant], states


# ---------------------------------------------------------------------------
# Parametrize rows
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NoContractNodeCase:
    """A node type whose panel has no contract controls, and a text only its panel shows."""

    case_id: str
    sidebar_button: str
    panel_anchor_text: str


# Anchors: ConditionalTab.tsx "Expression" field, SwitchTab.tsx description,
# IteratorTab.tsx "Iteration Key" field.
NO_CONTRACT_NODE_CASES = [
    NoContractNodeCase("conditional", "Conditional", "Expression"),
    NoContractNodeCase(
        "switch",
        "Switch",
        "Allows for multiple branching paths based on different conditions",
    ),
    NoContractNodeCase("iterator", "Iterator", "Iteration Key"),
]


@dataclass(frozen=True)
class StrictCase:
    """Where ``save_validation: strict`` is set, and which strict marker the panel shows."""

    case_id: str
    yaml_builder: Callable[[str], str]
    strict_line_visible: bool
    strict_tag_visible: bool


STRICT_CASES = [
    StrictCase("workflow-level", build_workflow_strict_yaml, True, False),
    StrictCase("state-level", build_state_strict_yaml, False, True),
]


@dataclass(frozen=True)
class NavigatingSaveCase:
    """A seeded workflow whose save carries no WARNING or ERROR."""

    case_id: str
    yaml_builder: Callable[[str], str]


NAVIGATING_SAVE_CASES = [
    NavigatingSaveCase("clean", build_clean_yaml),
    NavigatingSaveCase("unverified-only", build_unverified_only_yaml),
]
