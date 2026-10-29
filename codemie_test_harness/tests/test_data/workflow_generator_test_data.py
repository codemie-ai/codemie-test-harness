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

"""Test data for the workflow-generation (NL to workflow) API tests.

Representative, valid natural-language workflow descriptions and the schema
keys expected on a successful ``WorkflowGeneratorResponse`` / generated
``workflow_config``. LLM-generated content itself is never asserted verbatim
here (see the generator's own non-determinism guidance) — only structure.
"""

# A representative, valid NL description used for the "happy path" generate tests.
VALID_NL_WORKFLOW_DESCRIPTION = (
    "Create a workflow that receives a support ticket description as input, "
    "analyzes its content, and produces a short summary of the ticket."
)

# A second representative description used where a distinct prompt is useful
# (e.g. persist=true tests) to reduce any chance of accidental caching/coupling.
ALTERNATE_NL_WORKFLOW_DESCRIPTION = (
    "Create a workflow with a single assistant that reviews a block of text and "
    "produces a one-sentence summary of it."
)

# Deterministic NL description for TC-08: the workflow's own job is to emit a
# random number, so only the *shape* of the output (an integer within range)
# is ever asserted, never an exact value.
RANDOM_NUMBER_NL_WORKFLOW_DESCRIPTION = (
    "Create a workflow that returns a random number from 0 to 10 and nothing else."
)

# Top-level keys expected on the generated workflow_config (mirrors the
# backend's CreateWorkflowRequest / the SDK's WorkflowGeneratorConfig).
EXPECTED_WORKFLOW_CONFIG_KEYS = {
    "name",
    "description",
    "mode",
    "states",
    "assistants",
}
