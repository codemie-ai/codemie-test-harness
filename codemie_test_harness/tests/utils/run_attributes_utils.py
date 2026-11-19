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

"""Helpers for the run attributes tests: the two kinds of run that carry attributes."""

import uuid

from codemie_sdk.models.analytics import TabularResponse

from codemie_test_harness.tests.test_data.run_attributes_test_data import (
    ANALYTICS_MAX_PAGES,
    ANALYTICS_PAGE_SIZE,
    ANALYTICS_PERIOD,
    ANALYTICS_ROW_INTERVAL,
    ANALYTICS_ROW_TIMEOUT,
    RUN_PROMPT,
)
from codemie_test_harness.tests.utils.base_utils import poll_until


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

    def analytics_page(
        self, attributes: str | dict | None = None, page: int = 0
    ) -> TabularResponse:
        raise NotImplementedError

    def analytics_rows(self, attributes: str | dict | None = None) -> list[dict]:
        """All rows of the endpoint narrowed by ``attributes``, following the pages."""
        rows: list[dict] = []
        for page in range(ANALYTICS_MAX_PAGES):
            response = self.analytics_page(attributes, page)
            rows.extend(response.data.rows)
            has_more = (
                response.pagination.has_more
                if response.pagination
                else len(response.data.rows) == ANALYTICS_PAGE_SIZE
            )
            if not has_more:
                break
        return rows

    def run_ids(self, attributes: str | dict | None = None) -> set[str]:
        return {row[self.id_column] for row in self.analytics_rows(attributes)}

    def wait_for_run_ids_by_filter(
        self, expected_by_filter: list[tuple[str | dict | None, set[str]]]
    ) -> list[set[str]]:
        """Poll until every filter lists exactly its expected runs, all checked in one poll.

        Returns the ids last seen per filter, in order, so a mismatch is reported by the
        caller's assertions. One poll keeps the wait bounded by ``ANALYTICS_ROW_TIMEOUT``
        however many filters there are.
        """
        expected = [run_ids for _, run_ids in expected_by_filter]
        return poll_until(
            lambda: [self.run_ids(attributes) for attributes, _ in expected_by_filter],
            lambda seen: seen == expected,
            timeout=ANALYTICS_ROW_TIMEOUT,
            interval=ANALYTICS_ROW_INTERVAL,
        )

    def wait_for_row(self, run_id: str, attributes=None) -> dict | None:
        """Poll until the analytics row of ``run_id`` appears; None when it never does.

        ``attributes`` narrows the search to runs that carry them, which keeps the row
        within reach on a stand where other runs are going on; a run without attributes
        is found by following the pages instead.
        """
        rows = poll_until(
            lambda: self.analytics_rows(attributes),
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

    def analytics_page(self, attributes=None, page: int = 0) -> TabularResponse:
        return self._analytics_utils.get_assistants_requests(
            assistant_id=self.assistant.id,
            time_period=ANALYTICS_PERIOD,
            page=page,
            per_page=ANALYTICS_PAGE_SIZE,
            attributes=attributes,
        )


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

    def analytics_page(self, attributes=None, page: int = 0) -> TabularResponse:
        # The endpoint lists the executions of the whole tenant, so a run is found by
        # its attributes or by following the pages, not by its place in the first one.
        return self._analytics_utils.get_workflows_executions(
            time_period=ANALYTICS_PERIOD,
            page=page,
            per_page=ANALYTICS_PAGE_SIZE,
            attributes=attributes,
        )
