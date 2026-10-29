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

"""Tests for iterative transitions (map-reduce patterns) in workflows.

These tests verify the behavior of iter_key transitions that enable map-reduce patterns
where a state's output is evaluated to extract a collection of items, each item is
processed in parallel, and results are aggregated.

Test coverage:
- Simple list iteration (iter_key: ".")
- Dictionary with list (iter_key: "items")
- Nested structures with JSON Pointer (iter_key: "/data/users")
- Complex nested arrays (iter_key: "/response/results")
- Array of objects with context population
- Multi-stage iteration with context propagation
- Context isolation during parallel execution
- Context merging after completion
- Message history merging
- Simple values vs JSON objects ({{task}} vs {{key}} access)
"""

import json
import random

import pytest
from codemie_sdk.models.workflow import WorkflowMode, WorkflowCreateRequest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
)

from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.yaml_utils import (
    StateModel,
    WorkflowYamlModel,
    prepare_yaml_content,
)


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.iterator
def test_simple_list_iteration(
    data_generator,
    item_processor,
    result_aggregator,
    workflow_utils,
    workflow_cleanup,
):
    """Test iteration over a simple list using iter_key: '.'.

    Scenario:
    1. First state outputs: ["item1", "item2", "item3"]
    2. Iteration with iter_key: "." (uses entire list)
    3. Second state processes each item (3 parallel executions)
    4. Third state aggregates results
    5. Verify all items were processed

    Expected behavior:
    - Each item becomes task input (accessible via {{task}})
    - All parallel iterations complete before moving to aggregation
    - Message history from all iterations is available to aggregator
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("generate_list"),
            item_processor("process_item"),
            result_aggregator("aggregate_results"),
        ],
        states=[
            StateModel(
                id="generate_list",
                assistant_id="generate_list",
                task='Output exactly this JSON array: ["apple", "banana", "cherry"]',
                output_schema='["string"]',
                next={
                    "state_id": "process_item",
                    "iter_key": ".",
                },
            ),
            StateModel(
                id="process_item",
                assistant_id="process_item",
                task="Process this item: {{task}}. Say 'Processed: {{task}}' and nothing else.",
                next={"state_id": "aggregate_results"},
            ),
            StateModel(
                id="aggregate_results",
                assistant_id="aggregate_results",
                task="List all the items that were processed in the previous steps.",
                next={"state_id": "end"},
            ),
        ],
    )

    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))
    created_workflow = workflow_utils.create_workflow(
        workflow_name=workflow_name,
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=yaml_content,
    )
    workflow_cleanup.append(created_workflow)

    output = workflow_utils.execute_workflow(
        created_workflow.id,
        execution_name="aggregate_results",
        user_input="Start processing",
    ).lower()

    # Verify all three items were processed
    assert_that(output, contains_string("apple"))
    assert_that(output, contains_string("banana"))
    assert_that(output, contains_string("cherry"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.iterator
def test_dictionary_with_list_iteration(
    data_generator,
    item_processor,
    result_aggregator,
    workflow_utils,
    workflow_cleanup,
):
    """Test iteration over a list within a dictionary using iter_key: 'items'.

    Scenario:
    1. First state outputs: {"items": ["file1.txt", "file2.txt"], "count": 2}
    2. Iteration with iter_key: "items" (extracts result['items'])
    3. Second state processes each file (2 parallel executions)
    4. Third state aggregates results
    5. Verify both files were processed

    Expected behavior:
    - iter_key extracts the specific list from the dictionary
    - Only the 'items' list is iterated, not other keys
    - Each item is processed in parallel
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("generate_data"),
            item_processor("process_file"),
            result_aggregator("aggregate_files"),
        ],
        states=[
            StateModel(
                id="generate_data",
                assistant_id="generate_data",
                task='Output this JSON: {"items": ["file1.txt", "file2.txt"], "count": 2}',
                output_schema='{"items": ["string"], "count": "number"}',
                next={
                    "state_id": "process_file",
                    "iter_key": "items",
                },
            ),
            StateModel(
                id="process_file",
                assistant_id="process_file",
                task="Process file: {{task}}. Say 'File processed: {{task}}' and nothing else.",
                next={"state_id": "aggregate_files"},
            ),
            StateModel(
                id="aggregate_files",
                assistant_id="aggregate_files",
                task="List all the files that were processed.",
                next={"state_id": "end"},
            ),
        ],
    )

    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))
    created_workflow = workflow_utils.create_workflow(
        workflow_name=workflow_name,
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=yaml_content,
    )
    workflow_cleanup.append(created_workflow)

    output = workflow_utils.execute_workflow(
        created_workflow.id,
        execution_name="aggregate_files",
        user_input="Start processing",
    ).lower()

    # Verify both files were processed
    assert_that(output, contains_string("file1.txt"))
    assert_that(output, contains_string("file2.txt"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.iterator
def test_nested_structure_json_pointer_iteration(
    data_generator,
    item_processor,
    result_aggregator,
    workflow_utils,
    workflow_cleanup,
):
    """Test iteration over nested structure using JSON Pointer (iter_key: '/data/users').

    Scenario:
    1. First state outputs nested structure with users array
    2. Iteration with iter_key: "/data/users" (JSON Pointer syntax)
    3. Second state processes each user object
    4. Third state aggregates results
    5. Verify all users were processed

    Expected behavior:
    - JSON Pointer navigates to nested array
    - Each user object populates context with its keys
    - Context variables like {{id}} and {{name}} are accessible
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("fetch_users"),
            item_processor("process_user"),
            result_aggregator("aggregate_users"),
        ],
        states=[
            StateModel(
                id="fetch_users",
                assistant_id="fetch_users",
                task=(
                    "Output this JSON: "
                    '{"status": "success", "data": {"users": ['
                    '{"id": 1, "name": "Alice"}, '
                    '{"id": 2, "name": "Bob"}'
                    "]}}"
                ),
                output_schema='{"status": "string", "data": {"users": [{"id": "number", "name": "string"}]}}',
                next={
                    "state_id": "process_user",
                    "iter_key": "/data/users",
                },
            ),
            StateModel(
                id="process_user",
                assistant_id="process_user",
                task="Process user ID {{id}} with name {{name}}. Say 'Processed user {{id}}: {{name}}' and nothing else.",
                next={"state_id": "aggregate_users"},
            ),
            StateModel(
                id="aggregate_users",
                assistant_id="aggregate_users",
                task="List all the users that were processed with their IDs and names.",
                next={"state_id": "end"},
            ),
        ],
    )

    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))
    created_workflow = workflow_utils.create_workflow(
        workflow_name=workflow_name,
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=yaml_content,
    )
    workflow_cleanup.append(created_workflow)

    output = workflow_utils.execute_workflow(
        created_workflow.id,
        execution_name="aggregate_users",
        user_input="Start processing",
    ).lower()

    # Verify both users were processed with their data
    assert_that(output, contains_string("alice"))
    assert_that(output, contains_string("bob"))
    # Verify IDs were accessible from context
    assert_that(output, contains_string("1") or contains_string("id 1"))
    assert_that(output, contains_string("2") or contains_string("id 2"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.iterator
def test_complex_nested_array_iteration(
    data_generator,
    item_processor,
    result_aggregator,
    workflow_utils,
    workflow_cleanup,
):
    """Test iteration over complex nested arrays using JSON Pointer.

    Scenario:
    1. First state outputs deeply nested structure
    2. Iteration with iter_key: "/response/results"
    3. Second state processes each result object
    4. Third state aggregates results
    5. Verify all nested items were processed

    Expected behavior:
    - JSON Pointer navigates to deeply nested array
    - Each object's keys populate the context
    - Context variables are accessible in task templates
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("fetch_results"),
            item_processor("process_result"),
            result_aggregator("aggregate_results"),
        ],
        states=[
            StateModel(
                id="fetch_results",
                assistant_id="fetch_results",
                task=(
                    "Output this JSON: "
                    '{"response": {"results": ['
                    '{"env": "dev", "status": "passed"}, '
                    '{"env": "staging", "status": "failed"}, '
                    '{"env": "prod", "status": "passed"}'
                    "]}}"
                ),
                output_schema='{"response": {"results": [{"env": "string", "status": "string"}]}}',
                next={
                    "state_id": "process_result",
                    "iter_key": "/response/results",
                },
            ),
            StateModel(
                id="process_result",
                assistant_id="process_result",
                task="Process environment {{env}} with status {{status}}. Say 'Environment {{env}}: {{status}}' and nothing else.",
                next={"state_id": "aggregate_results"},
            ),
            StateModel(
                id="aggregate_results",
                assistant_id="aggregate_results",
                task="List all environments and their statuses that were processed.",
                next={"state_id": "end"},
            ),
        ],
    )

    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))
    created_workflow = workflow_utils.create_workflow(
        workflow_name=workflow_name,
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=yaml_content,
    )
    workflow_cleanup.append(created_workflow)

    output = workflow_utils.execute_workflow(
        created_workflow.id,
        execution_name="aggregate_results",
        user_input="Start processing",
    ).lower()

    # Verify all environments were processed
    assert_that(output, contains_string("dev"))
    assert_that(output, contains_string("staging"))
    assert_that(output, contains_string("prod"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.iterator
def test_array_of_objects_context_population(
    data_generator,
    item_processor,
    result_aggregator,
    workflow_utils,
    workflow_cleanup,
):
    """Test that array of objects properly populates context variables.

    Scenario:
    1. First state outputs array of task objects
    2. Iteration with iter_key: "." (uses entire array)
    3. Second state uses context variables from object keys
    4. Verify context variables {{id}}, {{title}}, {{priority}} are accessible

    Expected behavior:
    - Each object's root elements are stored in context
    - Template variables {{id}}, {{title}}, {{priority}} resolve correctly
    - Each iteration has isolated context with its object's values
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("get_tasks"),
            item_processor("execute_task"),
            result_aggregator("summarize_tasks"),
        ],
        states=[
            StateModel(
                id="get_tasks",
                assistant_id="get_tasks",
                task=(
                    "Output this JSON: "
                    '[{"id": 1, "title": "Task A", "priority": "high"}, '
                    '{"id": 2, "title": "Task B", "priority": "low"}]'
                ),
                output_schema='[{"id": "number", "title": "string", "priority": "string"}]',
                next={
                    "state_id": "execute_task",
                    "iter_key": ".",
                },
            ),
            StateModel(
                id="execute_task",
                assistant_id="execute_task",
                task=(
                    "Execute task ID {{id}}: {{title}}. "
                    "Priority level: {{priority}}. "
                    "Say 'Executed task {{id}} ({{title}}) with priority {{priority}}' and nothing else."
                ),
                next={"state_id": "summarize_tasks"},
            ),
            StateModel(
                id="summarize_tasks",
                assistant_id="summarize_tasks",
                task="Summarize all tasks that were executed, including their IDs, titles, and priorities.",
                next={"state_id": "end"},
            ),
        ],
    )

    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))
    created_workflow = workflow_utils.create_workflow(
        workflow_name=workflow_name,
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=yaml_content,
    )
    workflow_cleanup.append(created_workflow)

    output = workflow_utils.execute_workflow(
        created_workflow.id,
        execution_name="summarize_tasks",
        user_input="Start processing",
    ).lower()

    # Verify all task details were accessible and processed
    assert_that(output, contains_string("task a"))
    assert_that(output, contains_string("task b"))
    assert_that(output, contains_string("high"))
    assert_that(output, contains_string("low"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.iterator
def test_multi_stage_iteration_with_object_items(
    data_generator,
    item_processor,
    data_validator,
    result_aggregator,
    workflow_utils,
    workflow_cleanup,
):
    """Test multi-stage iteration where each item goes through multiple processing states.

    Scenario:
    1. First state outputs chunks with data and metadata
    2. Iteration starts with iter_key: "chunks"
    3. Second state processes chunk (iter_key: "chunks")
    4. Third state validates chunk (iter_key: "chunks")
    5. Fourth state merges all results
    6. Verify context variables persist through all iteration stages

    Expected behavior:
    - Same iter_key must be present in all states in iteration chain
    - Context variables persist through iteration stages
    - Each iteration branch processes through all stages independently
    - Contexts merge after all iterations complete
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        assistants=[
            data_generator("split_work"),
            item_processor("process_chunk"),
            data_validator("validate_chunk"),
            result_aggregator("merge_results"),
        ],
        states=[
            StateModel(
                id="split_work",
                assistant_id="split_work",
                task=(
                    "Output this JSON: "
                    '{"chunks": ['
                    '{"data": "chunk1", "metadata": "info1"}, '
                    '{"data": "chunk2", "metadata": "info2"}'
                    "]}"
                ),
                output_schema='{"chunks": [{"data": "string", "metadata": "string"}]}',
                next={
                    "state_id": "process_chunk",
                    "iter_key": "chunks",
                },
            ),
            StateModel(
                id="process_chunk",
                assistant_id="process_chunk",
                task=(
                    "Process chunk with data: {{data}}. "
                    "Say 'Processed {{data}}' and nothing else."
                ),
                next={
                    "state_id": "validate_chunk",
                    "iter_key": "chunks",
                },
            ),
            StateModel(
                id="validate_chunk",
                assistant_id="validate_chunk",
                task=(
                    "Validate the processed chunk metadata. "
                    "Say 'Validated {{metadata}}' and nothing else."
                ),
                next={"state_id": "merge_results"},
            ),
            StateModel(
                id="merge_results",
                assistant_id="merge_results",
                task="List all chunks that were processed and validated with their data and metadata.",
                next={"state_id": "end"},
            ),
        ],
    )

    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))
    created_workflow = workflow_utils.create_workflow(
        workflow_name=workflow_name,
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=yaml_content,
    )
    workflow_cleanup.append(created_workflow)

    output = workflow_utils.execute_workflow(
        created_workflow.id,
        execution_name="merge_results",
        user_input="Start processing",
    ).lower()

    # Verify both chunks were processed and validated
    assert_that(output, contains_string("chunk1"))
    assert_that(output, contains_string("chunk2"))
    assert_that(output, contains_string("info1"))
    assert_that(output, contains_string("info2"))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.iterator
def test_context_merging_after_iteration(
    data_generator,
    item_processor,
    result_aggregator,
    workflow_utils,
    workflow_cleanup,
):
    """Test that context is merged after iteration with mathematical validation.

    Scenario:
    1. First state outputs 10 items with id, value, and coefficient
    2. Each item is processed in parallel: value * coefficient
    3. After completion, aggregator calculates total sum
    4. Compare actual sum with expected sum calculated in test

    Expected behavior:
    - Contexts merge after all iterations complete
    - All multiplication results are properly aggregated
    - Total sum matches expected calculation
    """
    workflow_name = get_random_name()

    # Generate 10 items with random values and coefficients
    items = []
    expected_total = 0
    for i in range(1, 11):
        value = random.randint(10, 50)
        coefficient = random.randint(2, 5)
        items.append({"id": i, "value": value, "coefficient": coefficient})
        expected_total += value * coefficient

    # Convert items to JSON string for task
    items_json = json.dumps(items)

    workflow_yaml = WorkflowYamlModel(
        enable_summarization_node=False,
        # Set 10 max concurrency for test parallel processing
        max_concurrency=10,
        assistants=[
            data_generator("generate_items"),
            item_processor("process_item"),
            result_aggregator("aggregate_results"),
        ],
        states=[
            StateModel(
                id="generate_items",
                assistant_id="generate_items",
                task=f"Output exactly this JSON: {items_json}",
                output_schema='[{"id": "number", "value": "number", "coefficient": "number"}]',
                next={
                    "state_id": "process_item",
                    "iter_key": ".",
                },
            ),
            StateModel(
                id="process_item",
                assistant_id="process_item",
                task=(
                    "Calculate: {{value}} * {{coefficient}}. "
                    "Output only the result number and nothing else."
                ),
                next={"state_id": "aggregate_results"},
            ),
            StateModel(
                id="aggregate_results",
                assistant_id="aggregate_results",
                task=(
                    "Sum all the multiplication results from the previous steps. "
                    "Return only the total sum as a number."
                ),
                next={"state_id": "end"},
            ),
        ],
    )

    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))
    created_workflow = workflow_utils.create_workflow(
        workflow_name=workflow_name,
        workflow_type=WorkflowMode.SEQUENTIAL,
        workflow_yaml=yaml_content,
    )
    workflow_cleanup.append(created_workflow)

    output = workflow_utils.execute_workflow(
        created_workflow.id,
        execution_name="aggregate_results",
        user_input="Start processing",
    )

    # Verify the actual total matches expected total
    assert_that(int(output), equal_to(expected_total))


# ============================================================================
# NEGATIVE TESTS: Invalid iter_key combinations
# ============================================================================


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.iterator
def test_iter_key_cannot_combine_with_parallel_transitions(
    data_generator,
    workflow_utils,
    workflow_cleanup,
):
    """Test that iter_key cannot be combined with state_ids (parallel transitions).

    Scenario:
    1. Attempt to create workflow with both iter_key and state_ids in next
    2. Expect workflow creation to fail with validation error

    Expected behavior:
    - Workflow creation should fail
    - Error message should indicate invalid combination
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        assistants=[
            data_generator("generate_items"),
            data_generator("process_a"),
            data_generator("process_b"),
        ],
        states=[
            StateModel(
                id="generate_items",
                assistant_id="generate_items",
                task='Output this JSON: ["item1", "item2"]',
                output_schema='["string"]',
                next={
                    "state_ids": ["process_a", "process_b"],  # Parallel transition
                    "iter_key": ".",  # Invalid: cannot combine with state_ids
                },
            ),
            StateModel(
                id="process_a",
                assistant_id="process_a",
                task="Process A",
                next={"state_id": "end"},
            ),
            StateModel(
                id="process_b",
                assistant_id="process_b",
                task="Process B",
                next={"state_id": "end"},
            ),
        ],
    )

    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))

    request = WorkflowCreateRequest(
        name=workflow_name,
        description="Invalid workflow with iter_key and state_ids",
        project=PROJECT,
        yaml_config=yaml_content,
    )

    # Attempt to create workflow - should fail
    response = workflow_utils.send_request_to_create_workflow_endpoint(request)

    # Verify error response
    assert_that("error" in response, "Expected error in response")
    error_details = response.get("error", {}).get("details", "")

    # Error message should indicate the invalid combination
    assert_that(
        "'states[0].next': 'state_ids' and 'iter_key' cannot be set at the same time"
        in error_details
    )


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.iterator
def test_iter_key_cannot_combine_with_condition(
    data_generator, workflow_utils, workflow_cleanup
):
    """Test that iter_key cannot be combined with condition (conditional transitions).

    Scenario:
    1. Attempt to create workflow with both iter_key and condition in next
    2. Expect workflow creation to fail with validation error

    Expected behavior:
    - Workflow creation should fail
    - Error message should indicate invalid combination
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        assistants=[
            data_generator("generate_items"),
            data_generator("process_true"),
            data_generator("process_false"),
        ],
        states=[
            StateModel(
                id="generate_items",
                assistant_id="generate_items",
                task='Output this JSON: {"items": ["item1", "item2"], "count": 2}',
                output_schema='{"items": ["string"], "count": "number"}',
                next={
                    "condition": {  # Conditional transition
                        "expression": "count > 1",
                        "then": "process_true",
                        "otherwise": "process_false",
                    },
                    "iter_key": "items",  # Invalid: cannot combine with condition
                },
            ),
            StateModel(
                id="process_true",
                assistant_id="process_true",
                task="Process true branch",
                next={"state_id": "end"},
            ),
            StateModel(
                id="process_false",
                assistant_id="process_false",
                task="Process false branch",
                next={"state_id": "end"},
            ),
        ],
    )

    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))

    request = WorkflowCreateRequest(
        name=workflow_name,
        description="Invalid workflow with iter_key and condition",
        project=PROJECT,
        yaml_config=yaml_content,
    )

    # Attempt to create workflow - should fail
    response = workflow_utils.send_request_to_create_workflow_endpoint(request)

    # Verify error response
    assert_that("error" in response, "Expected error in response")
    error_details = response.get("error", {}).get("details", "")

    # Error message should indicate the invalid combination
    assert_that(
        "In 'states[0].next': 'iter_key' and 'condition' cannot be set at the same time"
        in error_details
    )


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.workflow
@pytest.mark.api
@pytest.mark.iterator
def test_iter_key_cannot_combine_with_switch(
    data_generator, workflow_utils, workflow_cleanup
):
    """Test that iter_key cannot be combined with switch (switch/case transitions).

    Scenario:
    1. Attempt to create workflow with both iter_key and switch in next
    2. Expect workflow creation to fail with validation error

    Expected behavior:
    - Workflow creation should fail
    - Error message should indicate invalid combination
    """
    workflow_name = get_random_name()

    workflow_yaml = WorkflowYamlModel(
        assistants=[
            data_generator("generate_items"),
            data_generator("process_success"),
            data_generator("process_warning"),
            data_generator("process_error"),
        ],
        states=[
            StateModel(
                id="generate_items",
                assistant_id="generate_items",
                task='Output this JSON: {"items": ["item1", "item2"], "status": "success"}',
                output_schema='{"items": ["string"], "status": "string"}',
                next={
                    "switch": {  # Switch/case transition
                        "cases": [
                            {
                                "condition": "status == 'success'",
                                "state_id": "process_success",
                            },
                            {
                                "condition": "status == 'warning'",
                                "state_id": "process_warning",
                            },
                            {
                                "condition": "status == 'error'",
                                "state_id": "process_error",
                            },
                        ],
                        "default": "process_error",
                    },
                    "iter_key": "items",  # Invalid: cannot combine with switch
                },
            ),
            StateModel(
                id="process_success",
                assistant_id="process_success",
                task="Process success",
                next={"state_id": "end"},
            ),
            StateModel(
                id="process_warning",
                assistant_id="process_warning",
                task="Process warning",
                next={"state_id": "end"},
            ),
            StateModel(
                id="process_error",
                assistant_id="process_error",
                task="Process error",
                next={"state_id": "end"},
            ),
        ],
    )

    yaml_content = prepare_yaml_content(workflow_yaml.model_dump(exclude_none=True))

    request = WorkflowCreateRequest(
        name=workflow_name,
        description="Invalid workflow with iter_key and switch",
        project=PROJECT,
        yaml_config=yaml_content,
    )

    # Attempt to create workflow - should fail
    response = workflow_utils.send_request_to_create_workflow_endpoint(request)

    # Verify error response
    assert_that("error" in response, "Expected error in response")
    error_details = response.get("error", {}).get("details", "")

    # Error message should indicate the invalid combination
    assert_that(
        "In 'states[0].next': 'iter_key' and 'switch' cannot be set at the same time"
        in error_details
    )
