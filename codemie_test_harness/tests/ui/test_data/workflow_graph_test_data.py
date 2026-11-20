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

"""Test data for the workflow graph (edit canvas) rendering tests.

Every state of every workflow here uses the inline custom node ``graph_stub``, backed by
the ``transform_node`` module, so no assistant, tool or integration is needed. Branching
(conditional, switch, iterator) is expressed only through the states' ``next`` fields.

The editor draws, besides one node per YAML state, a ``start`` and an ``end`` node, one
node per conditional or switch branch and one node per iterator. It draws one edge per
transition: ``start`` to the first state, every ``state_id`` / ``state_ids`` target, and for
a branch the edge from the parent state to the branch node plus one edge per branch target.
An iterator draws a node and no edge of its own.
"""

from dataclasses import dataclass
from typing import Optional

from codemie_test_harness.tests.utils.yaml_utils import (
    CustomNodeModel,
    StateModel,
    WorkflowYamlModel,
    prepare_yaml_content,
)

# Id of the inline custom node every state points at.
GRAPH_STUB_NODE_ID = "graph_stub"
# Module the inline custom node is backed by.
_GRAPH_STUB_MODULE = "transform_node"

# Nodes the editor adds around the YAML states.
START_AND_END_NODES = 2


def _state(node_id: str, /, **next_fields) -> StateModel:
    """A ``graph_stub`` state whose ``next`` holds ``next_fields``."""
    return StateModel(
        id=node_id,
        custom_node_id=GRAPH_STUB_NODE_ID,
        next=next_fields,
        resolve_dynamic_values_in_prompt=None,
    )


def _go(state_id: str, target: str) -> StateModel:
    return _state(state_id, state_id=target)


def _if(
    state_id: str,
    then: str,
    otherwise: str,
    expression: str,
    meta_next_state_id: Optional[str] = None,
) -> StateModel:
    next_fields = {}
    if meta_next_state_id:
        next_fields["meta_next_state_id"] = meta_next_state_id
    next_fields["condition"] = {
        "expression": expression,
        "then": then,
        "otherwise": otherwise,
    }
    return _state(state_id, **next_fields)


def _switch(state_id: str, cases: dict, default: str, variable: str) -> StateModel:
    return _state(
        state_id,
        switch={
            "cases": [
                {"condition": f"{variable} == '{value}'", "state_id": target}
                for value, target in cases.items()
            ],
            "default": default,
        },
    )


def _workflow_yaml(states: list[StateModel]) -> str:
    workflow = WorkflowYamlModel(
        custom_nodes=[
            CustomNodeModel(
                id=GRAPH_STUB_NODE_ID,
                custom_node_id=_GRAPH_STUB_MODULE,
                config={"mappings": []},
            )
        ],
        states=states,
    )
    return prepare_yaml_content(workflow.model_dump(exclude_none=True))


# ---------------- 50-state workflow ----------------

# Topology of the frontend's large-workflow fixture: 50 states, 4 conditionals, 2 switches
# and 1 iterator (``it_fetch``, which takes a single ``state_id`` plus ``iter_key``: the
# backend rejects ``state_ids`` on an iterator). It repeats the branch id ``conditional_7`` on two parents and has a state
# named ``conditional_1``, as the failing customer workflow did.
_LARGE_WORKFLOW_STATES = [
    _go("intake", "parse"),
    _go("parse", "normalize"),
    _go("normalize", "conditional_1"),
    _go("conditional_1", "classify"),
    _switch(
        "classify",
        {"a": "kind_a", "b": "kind_b", "c": "kind_c", "d": "kind_d"},
        "kind_other",
        "kind",
    ),
    _go("kind_a", "a_step_1"),
    _go("a_step_1", "a_step_2"),
    _go("a_step_2", "merge"),
    _go("kind_b", "b_step_1"),
    _go("b_step_1", "merge"),
    _go("kind_c", "c_step_1"),
    _go("c_step_1", "c_step_2"),
    _go("c_step_2", "c_step_3"),
    _go("c_step_3", "merge"),
    _go("kind_d", "merge"),
    _go("kind_other", "merge"),
    _state("merge", state_ids=["fan_1", "fan_2", "fan_3", "fan_4"]),
    _go("fan_1", "fan_join"),
    _go("fan_2", "fan_join"),
    _go("fan_3", "fan_join"),
    _go("fan_4", "fan_join"),
    _if("fan_join", "review_one", "review_two", "fan_ok"),
    _if("review_one", "it_fetch", "manual_review", "needs_items", "conditional_7"),
    _if("review_two", "it_fetch", "manual_review", "has_items", "conditional_7"),
    _go("manual_review", "late_check"),
    _state("it_fetch", state_id="it_a", iter_key="items"),
    _go("it_a", "it_done"),
    _go("it_b", "it_done"),
    _go("it_c", "it_done"),
    _go("it_done", "late_check"),
    _if("late_check", "tail_1", "tail_alt", "all_clear", "conditional_8"),
    _go("tail_alt", "audit_1"),
    _go("audit_1", "audit_2"),
    _go("audit_2", "tail_1"),
    _go("tail_1", "tail_2"),
    _go("tail_2", "tail_3"),
    _switch("tail_3", {"x": "tail_4a", "y": "tail_4b"}, "tail_5", "route"),
    _go("tail_4a", "tail_6"),
    _go("tail_4b", "tail_6"),
    _go("tail_5", "tail_6"),
    _go("tail_6", "tail_7"),
    _go("tail_7", "tail_8"),
    _go("tail_8", "tail_9"),
    _go("tail_9", "tail_10"),
    _go("tail_10", "publish"),
    _state("publish", state_ids=["pub_a", "pub_b", "pub_c"]),
    _go("pub_a", "notify"),
    _go("pub_b", "notify"),
    _go("pub_c", "notify"),
    _go("notify", "end"),
]

LARGE_WORKFLOW_STATE_COUNT = 50
# 50 states + start + end + 6 branch nodes (4 conditionals, 2 switches) + 1 iterator.
LARGE_WORKFLOW_NODE_COUNT = 59
# One edge per transition of the topology above.
LARGE_WORKFLOW_EDGE_COUNT = 72


def build_large_workflow_yaml() -> str:
    """YAML of the 50-state workflow."""
    return _workflow_yaml(_LARGE_WORKFLOW_STATES)


# ---------------- repeated branch ids ----------------

# Five states, three conditionals:
#  - ``check_a`` and ``check_b`` both set ``meta_next_state_id: conditional_7``;
#  - ``check_c`` sets none, so the editor generates its branch id and must not reuse
#    the id of the state named ``conditional_1``.
_REPEATED_BRANCH_STATES = [
    _go("conditional_1", "check_a"),
    _if("check_a", "check_b", "check_c", "first_ok", "conditional_7"),
    _if("check_b", "check_c", "wrap_up", "second_ok", "conditional_7"),
    _if("check_c", "wrap_up", "end", "third_ok"),
    _go("wrap_up", "end"),
]

REPEATED_BRANCH_STATE_COUNT = 5
# 5 states + start + end + 3 branch nodes.
REPEATED_BRANCH_NODE_COUNT = 10


def build_repeated_branch_workflow_yaml() -> str:
    """YAML with a repeated ``meta_next_state_id`` and a state named ``conditional_1``."""
    return _workflow_yaml(_REPEATED_BRANCH_STATES)


# ---------------- small and medium workflows ----------------


@dataclass(frozen=True)
class GraphWorkflowCase:
    """A workflow and the canvas it must produce."""

    case_id: str
    yaml_config: str
    expected_nodes: int
    expected_edges: int


# Three states in a row: nodes = 3 + start + end; edges = start->first, 2 between, last->end.
_SMALL_LINEAR_STATES = [
    _go("step_one", "step_two"),
    _go("step_two", "step_three"),
    _go("step_three", "end"),
]

# Shape of the frontend's branch fixture (conditional, switch) plus an iterator:
#  - nodes: 7 states + start + end + conditional + switch + iterator = 12
#  - edges: start->check_quality, check_quality->branch, branch->analyzer, branch->end,
#    analyzer->switch, switch->3 targets, 2 documentation states->end,
#    unknown_language->fetch_items, fetch_items->process_item, process_item->end = 13
_MEDIUM_BRANCHING_STATES = [
    _if("check_quality", "analyzer", "end", "quality_ok"),
    _switch(
        "analyzer",
        {"Java": "documentation_java", "Python": "documentation_python"},
        "unknown_language",
        "language",
    ),
    _go("documentation_java", "end"),
    _go("documentation_python", "end"),
    _go("unknown_language", "fetch_items"),
    _state("fetch_items", state_id="process_item", iter_key="items"),
    _go("process_item", "end"),
]

SMALL_AND_MEDIUM_WORKFLOW_CASES = [
    GraphWorkflowCase(
        "small-linear",
        _workflow_yaml(_SMALL_LINEAR_STATES),
        expected_nodes=5,
        expected_edges=4,
    ),
    GraphWorkflowCase(
        "medium-conditional-switch-iterator",
        _workflow_yaml(_MEDIUM_BRANCHING_STATES),
        expected_nodes=12,
        expected_edges=13,
    ),
]
