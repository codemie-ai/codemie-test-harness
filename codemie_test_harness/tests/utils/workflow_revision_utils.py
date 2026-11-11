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

"""Helpers for the workflow revision history and rollback API."""

from codemie_sdk.models.workflow import WorkflowUpdateRequest

from codemie_test_harness.tests.utils.workflow_utils import WorkflowUtils


class WorkflowRevisionUtils(WorkflowUtils):
    def save_workflow_yaml(self, workflow, yaml_config):
        """Save a new ``yaml_config``; a semantic change adds one revision to the history.

        Unlike ``update_workflow`` it does not wait on the workflow list, so it stays
        cheap when a test builds a history of more than twenty revisions.
        """
        request = WorkflowUpdateRequest(
            name=workflow.name,
            project=workflow.project,
            description=workflow.description,
            yaml_config=yaml_config,
            mode=workflow.mode,
            shared=workflow.shared,
        )
        return self.send_update_workflow_request(workflow.id, request=request)

    def list_workflow_versions(self, workflow_id, page=None, per_page=None):
        """List the saved revisions, newest first. Raises HTTPError on a non-2xx answer."""
        return self.client.workflows.list_versions(
            workflow_id, page=page, per_page=per_page
        )

    def rollback_workflow(self, workflow_id, revision_index, change_notes=None):
        """Roll the workflow back to ``revision_index``. Raises HTTPError on a non-2xx answer."""
        return self.client.workflows.rollback(
            workflow_id, revision_index, change_notes=change_notes
        )
