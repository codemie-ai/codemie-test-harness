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

"""Helpers for the run attributes tests: the two kinds of run and the error message check."""

import uuid

from hamcrest import assert_that, contains_string, equal_to

from codemie_test_harness.tests.test_data.run_attributes_test_data import (
    ANALYTICS_PAGE_SIZE,
    ANALYTICS_PERIOD,
    ANALYTICS_ROW_INTERVAL,
    ANALYTICS_ROW_TIMEOUT,
    RUN_PROMPT,
)
from codemie_test_harness.tests.utils.base_utils import poll_until


def assert_error_message(response, status_code, message):
    """The response has ``status_code`` and its error message contains ``message``.

    The message of a body validation error is prefixed with the field and the validator
    ("attributes: Value error, ..."), so it is matched as a part, not as the whole.
    """
    assert_that(
        response.status_code, equal_to(status_code), "Status code is not expected."
    )
    assert_that(
        response.json()["error"]["message"],
        contains_string(message),
        "Error message is not expected.",
    )


def usage_counts(rows: list[dict]) -> dict[str, tuple[int, int]]:
    """Runs per attribute value of an attributes-usage table: (conversations, workflow executions)."""
    return {
        row["value"]: (row["conversations"], row["workflow_executions"]) for row in rows
    }


class RunSurface:
    """A kind of run that carries attributes, started and read through one interface.

    ``start`` runs it and returns the run id, ``stored_attributes`` reads the attributes
    of the stored record and ``analytics_rows`` lists the rows of the analytics endpoint
    of that kind. ``id_column`` names the column that holds the run id in those rows.
    """

    id_column: str

    def __init__(self, analytics_utils):
        self._analytics_utils = analytics_utils

    def start(self, attributes=None) -> str:
        raise NotImplementedError

    def stored_attributes(self, run_id: str):
        raise NotImplementedError

    def analytics_rows(self, attributes: str | dict | None = None) -> list[dict]:
        raise NotImplementedError

    def run_ids(self, attributes: str | dict | None = None) -> set[str]:
        return {row[self.id_column] for row in self.analytics_rows(attributes)}

    def wait_for_run_ids(self, expected: set[str], attributes=None) -> set[str]:
        """Poll until the rows narrowed by ``attributes`` are exactly the ``expected`` runs.

        Returns the last ids seen, so a mismatch is reported by the caller's assertion.
        """
        return poll_until(
            lambda: self.run_ids(attributes),
            lambda run_ids: run_ids == expected,
            timeout=ANALYTICS_ROW_TIMEOUT,
            interval=ANALYTICS_ROW_INTERVAL,
        )

    def wait_for_row(self, run_id: str) -> dict | None:
        """Poll until the analytics row of ``run_id`` appears; None when it never does."""
        rows = poll_until(
            self.analytics_rows,
            lambda found: any(row[self.id_column] == run_id for row in found),
            timeout=ANALYTICS_ROW_TIMEOUT,
            interval=ANALYTICS_ROW_INTERVAL,
        )
        return next((row for row in rows if row[self.id_column] == run_id), None)


class ChatRunSurface(RunSurface):
    """A chat with an assistant: one conversation, one analytics row per request."""

    id_column = "conversation_id"

    def __init__(self, analytics_utils, assistant, assistant_utils, conversation_utils):
        super().__init__(analytics_utils)
        self.assistant = assistant
        self._assistant_utils = assistant_utils
        self._conversation_utils = conversation_utils

    def start(self, attributes=None) -> str:
        conversation_id = str(uuid.uuid4())
        self._assistant_utils.ask_assistant(
            self.assistant,
            RUN_PROMPT,
            conversation_id=conversation_id,
            attributes=attributes,
        )
        return conversation_id

    def stored_attributes(self, run_id: str):
        return self._conversation_utils.get_conversation_by_id(run_id).attributes

    def analytics_rows(self, attributes=None) -> list[dict]:
        response = self._analytics_utils.get_assistants_requests(
            assistant_id=self.assistant.id,
            time_period=ANALYTICS_PERIOD,
            per_page=ANALYTICS_PAGE_SIZE,
            attributes=attributes,
        )
        return response.data.rows


class WorkflowRunSurface(RunSurface):
    """A workflow execution: one execution, one analytics row per execution."""

    id_column = "execution_id"

    def __init__(self, analytics_utils, workflow, workflow_utils):
        super().__init__(analytics_utils)
        self.workflow = workflow
        self._workflow_utils = workflow_utils

    def start(self, attributes=None) -> str:
        execution = self._workflow_utils.create_workflow_execution(
            self.workflow.id, user_input=RUN_PROMPT, attributes=attributes
        )
        return execution.execution_id

    def stored_attributes(self, run_id: str):
        return self._workflow_utils.get_workflow_execution(
            self.workflow.id, run_id
        ).attributes

    def analytics_rows(self, attributes=None) -> list[dict]:
        # Rows come newest activity first, so an execution that just ran is on the first page.
        response = self._analytics_utils.get_workflows_executions(
            time_period=ANALYTICS_PERIOD,
            per_page=ANALYTICS_PAGE_SIZE,
            attributes=attributes,
        )
        return response.data.rows
