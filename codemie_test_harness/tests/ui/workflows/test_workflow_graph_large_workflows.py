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

import pytest
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests.ui.pageobject.workflows.edit_workflow_page import (
    EditWorkflowPage,
)
from codemie_test_harness.tests.ui.test_data.workflow_graph_test_data import (
    LARGE_WORKFLOW_EDGE_COUNT,
    LARGE_WORKFLOW_NODE_COUNT,
    LARGE_WORKFLOW_STATE_COUNT,
    REPEATED_BRANCH_NODE_COUNT,
    REPEATED_BRANCH_STATE_COUNT,
    SHARED_META_ID_EDGE_COUNT,
    SHARED_META_ID_NODE_COUNT,
    SHARED_META_ID_STATE_COUNT,
    SMALL_AND_MEDIUM_WORKFLOW_CASES,
    build_large_workflow_yaml,
    build_repeated_branch_workflow_yaml,
    build_shared_meta_id_workflow_yaml,
)


# @case workflow-graph-large-workflows_TC_001
@pytest.mark.workflow
@pytest.mark.ui
def test_large_workflow_renders_every_state_and_transition(page, graph_workflow):
    """A 50-state workflow draws a node per state and an edge per transition.

    The canvas holds the 50 states plus start, end, one node per branch and one per
    iterator (59 nodes), not the 50 of the payload.
    """
    created = graph_workflow(build_large_workflow_yaml())
    assert_that(
        len(created.state_ids),
        equal_to(LARGE_WORKFLOW_STATE_COUNT),
        "the stored workflow should list every state of the YAML",
    )

    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(created.workflow.id)
    edit_page.should_be_on_edit_workflow_page()

    edit_page.should_have_canvas_node_count(LARGE_WORKFLOW_NODE_COUNT)
    edit_page.should_have_canvas_node_for_each_state(created.state_ids)
    edit_page.should_have_canvas_edge_count(LARGE_WORKFLOW_EDGE_COUNT)


# @case workflow-graph-large-workflows_TC_002
@pytest.mark.workflow
@pytest.mark.ui
def test_repeated_branch_ids_and_state_named_like_generated_id_keep_every_node(
    page, graph_workflow
):
    """Two conditionals sharing a branch id and a state named ``conditional_1`` lose no node."""
    created = graph_workflow(build_repeated_branch_workflow_yaml())
    assert_that(
        len(created.state_ids),
        equal_to(REPEATED_BRANCH_STATE_COUNT),
        "the stored workflow should list every state of the YAML",
    )

    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(created.workflow.id)
    edit_page.should_be_on_edit_workflow_page()

    edit_page.should_have_canvas_node_count(REPEATED_BRANCH_NODE_COUNT)
    edit_page.should_have_canvas_node_for_each_state(created.state_ids)


# @case workflow-graph-large-workflows_TC_004
@pytest.mark.workflow
@pytest.mark.ui
@pytest.mark.parametrize(
    "graph_case",
    SMALL_AND_MEDIUM_WORKFLOW_CASES,
    ids=[case.case_id for case in SMALL_AND_MEDIUM_WORKFLOW_CASES],
)
def test_small_and_medium_workflows_keep_their_nodes_and_edges(
    page, graph_workflow, graph_case
):
    """Workflows well below the large-graph size still draw every node and edge."""
    created = graph_workflow(graph_case.yaml_config)

    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(created.workflow.id)
    edit_page.should_be_on_edit_workflow_page()

    edit_page.should_have_canvas_node_count(graph_case.expected_nodes)
    edit_page.should_have_canvas_node_for_each_state(created.state_ids)
    edit_page.should_have_canvas_edge_count(graph_case.expected_edges)


# @case workflow-graph-large-workflows_TC_008
@pytest.mark.workflow
@pytest.mark.ui
def test_shared_meta_ids_across_conditional_and_iterator_states_keep_every_node(
    page, graph_workflow
):
    """Conditional and iterated states that repeat a meta id each keep their own node.

    Two pairs of conditionals share a ``meta_next_state_id`` and two pairs of iterated
    states share a ``meta_iter_state_id``; the canvas still draws a node for every state
    and every transition.
    """
    created = graph_workflow(build_shared_meta_id_workflow_yaml())
    assert_that(
        len(created.state_ids),
        equal_to(SHARED_META_ID_STATE_COUNT),
        "the stored workflow should list every state of the YAML",
    )

    edit_page = EditWorkflowPage(page)
    edit_page.navigate_to(created.workflow.id)
    edit_page.should_be_on_edit_workflow_page()

    edit_page.should_have_canvas_node_count(SHARED_META_ID_NODE_COUNT)
    edit_page.should_have_canvas_node_for_each_state(created.state_ids)
    edit_page.should_have_canvas_edge_count(SHARED_META_ID_EDGE_COUNT)
