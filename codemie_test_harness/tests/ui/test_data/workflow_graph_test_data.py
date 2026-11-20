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


def _canvas_counts(states: list[StateModel]) -> tuple[int, int]:
    """Nodes and edges the editor draws for ``states``, derived from their ``next`` fields.

    Nodes: the states, ``start``, ``end``, one node per conditional or switch, and one
    iterator per distinct (``iter_key``, ``meta_iter_state_id`` of the iterated state):
    iterator parents with the same pair share one iterator (the editor's iterator grouping).
    Edges: ``start`` to the first state, one per ``state_id`` / ``state_ids`` target, and per
    branch the edge to the branch node plus one per branch target.
    """
    by_id = {state.id: state for state in states}
    branches = 0
    iterators = set()
    edges = 1
    for state in states:
        next_fields = state.next
        edges += int(bool(next_fields.get("state_id")))
        edges += len(next_fields.get("state_ids", []))
        if "condition" in next_fields:
            branches += 1
            edges += 3
        if "switch" in next_fields:
            branches += 1
            edges += 2 + len(next_fields["switch"]["cases"])
        if next_fields.get("iter_key"):
            child = by_id[next_fields["state_id"]]
            iterators.add(
                (next_fields["iter_key"], child.next.get("meta_iter_state_id"))
            )
    nodes = len(states) + START_AND_END_NODES + branches + len(iterators)
    return nodes, edges


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

LARGE_WORKFLOW_STATE_COUNT = len(_LARGE_WORKFLOW_STATES)
LARGE_WORKFLOW_NODE_COUNT, LARGE_WORKFLOW_EDGE_COUNT = _canvas_counts(
    _LARGE_WORKFLOW_STATES
)


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

REPEATED_BRANCH_STATE_COUNT = len(_REPEATED_BRANCH_STATES)
REPEATED_BRANCH_NODE_COUNT, _ = _canvas_counts(_REPEATED_BRANCH_STATES)


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


def _graph_case(case_id: str, states: list[StateModel]) -> GraphWorkflowCase:
    nodes, edges = _canvas_counts(states)
    return GraphWorkflowCase(case_id, _workflow_yaml(states), nodes, edges)


SMALL_AND_MEDIUM_WORKFLOW_CASES = [
    _graph_case("small-linear", _SMALL_LINEAR_STATES),
    _graph_case("medium-conditional-switch-iterator", _MEDIUM_BRANCHING_STATES),
]


# ---------------- shared meta ids ----------------


def _iterated(state_id: str, target: str, meta_iter_state_id: str) -> StateModel:
    """A state an iterator runs over; it names the iterator it belongs to."""
    return _state(state_id, meta_iter_state_id=meta_iter_state_id, state_id=target)


def _loop(state_id: str, target: str) -> StateModel:
    """An iterator parent: runs ``target`` once per item of ``items``."""
    return _state(state_id, state_id=target, iter_key="items")


# Synthetic, linear-reachable workflow of 17 states in which:
#  - ``branch-02`` and ``branch-04`` share ``meta_next_state_id: conditional_1``, and
#    ``branch-10`` and ``branch-12`` share ``conditional_4`` (4 conditionals, 4 branch ids
#    in the YAML but only 2 distinct values);
#  - the states ``step-07`` and ``step-09`` share ``meta_iter_state_id: iterator_2``, and
#    ``step-15`` and ``step-17`` share ``iterator_3``; each is the target of an iterator
#    parent (``loop-06``, ``loop-08``, ``loop-14``, ``loop-16``) with ``iter_key: items``.
# Each iterator parent has a single ``state_id`` target.
_SHARED_META_ID_STATES = [
    _go("step-01", "branch-02"),
    _if("branch-02", "step-03", "branch-04", "first_ok", "conditional_1"),
    _go("step-03", "branch-04"),
    _if("branch-04", "step-05", "loop-06", "second_ok", "conditional_1"),
    _go("step-05", "loop-06"),
    _loop("loop-06", "step-07"),
    _iterated("step-07", "loop-08", "iterator_2"),
    _loop("loop-08", "step-09"),
    _iterated("step-09", "branch-10", "iterator_2"),
    _if("branch-10", "step-11", "branch-12", "third_ok", "conditional_4"),
    _go("step-11", "branch-12"),
    _if("branch-12", "step-13", "loop-14", "fourth_ok", "conditional_4"),
    _go("step-13", "loop-14"),
    _loop("loop-14", "step-15"),
    _iterated("step-15", "loop-16", "iterator_3"),
    _loop("loop-16", "step-17"),
    _iterated("step-17", "end", "iterator_3"),
]

SHARED_META_ID_STATE_COUNT = len(_SHARED_META_ID_STATES)
SHARED_META_ID_NODE_COUNT, SHARED_META_ID_EDGE_COUNT = _canvas_counts(
    _SHARED_META_ID_STATES
)


def build_shared_meta_id_workflow_yaml() -> str:
    """YAML whose conditional and iterated states repeat meta ids."""
    return _workflow_yaml(_SHARED_META_ID_STATES)
