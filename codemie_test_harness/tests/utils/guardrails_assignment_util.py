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

"""Utility functions for assigning guardrails to CodeMie entities."""

from codemie_sdk.models.guardrails import (
    GuardrailAssignmentRequest,
    GuardrailAssignmentEntity,
    GuardrailAssignmentSetting,
    GuardrailAssignmentResponse,
)
from codemie_test_harness.tests.utils.base_utils import BaseUtils
from codemie_test_harness.tests.utils.logger_util import setup_logger

logger = setup_logger(__name__)


class GuardrailsAssignmentUtils(BaseUtils):
    """Utility class for assigning guardrails to CodeMie entities."""

    def assign_guardrail_to_all_assistants(
        self,
        guardrail_id: str,
        source: str = "input",
    ) -> GuardrailAssignmentResponse:
        """Assign guardrail to all project assistants.

        Args:
            guardrail_id: ID of the guardrail to assign (AI run ID from installation)
            source: Source type ('input' or 'output')

        Returns:
            GuardrailAssignmentResponse with success status
        """
        logger.info(f"Assigning guardrail {guardrail_id} to all project assistants")

        assignment = GuardrailAssignmentRequest(
            project=GuardrailAssignmentEntity(settings=[], items=[]),
            assistants=GuardrailAssignmentEntity(
                settings=[GuardrailAssignmentSetting(mode="all", source=source)],
                items=[],
            ),
            workflows=GuardrailAssignmentEntity(settings=[], items=[]),
            datasources=GuardrailAssignmentEntity(settings=[], items=[]),
        )

        response = self.client.codemie_guardrails.assign_guardrails(
            guardrail_id=guardrail_id, assignment=assignment
        )

        if response.success:
            logger.info(
                f"Successfully assigned guardrail {guardrail_id} to all assistants"
            )
        else:
            logger.warning(
                f"Failed to assign guardrail {guardrail_id} to all assistants"
            )

        return response

    def assign_guardrail_to_all_workflows(
        self,
        guardrail_id: str,
        source: str = "input",
    ) -> GuardrailAssignmentResponse:
        """Assign guardrail to all project workflows.

        Args:
            guardrail_id: ID of the guardrail to assign (AI run ID from installation)
            source: Source type ('input' or 'output')

        Returns:
            GuardrailAssignmentResponse with success status
        """
        logger.info(f"Assigning guardrail {guardrail_id} to all project workflows")

        assignment = GuardrailAssignmentRequest(
            project=GuardrailAssignmentEntity(settings=[], items=[]),
            assistants=GuardrailAssignmentEntity(settings=[], items=[]),
            workflows=GuardrailAssignmentEntity(
                settings=[GuardrailAssignmentSetting(mode="all", source=source)],
                items=[],
            ),
            datasources=GuardrailAssignmentEntity(settings=[], items=[]),
        )

        response = self.client.codemie_guardrails.assign_guardrails(
            guardrail_id=guardrail_id, assignment=assignment
        )

        if response.success:
            logger.info(
                f"Successfully assigned guardrail {guardrail_id} to all workflows"
            )
        else:
            logger.warning(
                f"Failed to assign guardrail {guardrail_id} to all workflows"
            )

        return response

    def assign_guardrail_to_all_datasources(
        self,
        guardrail_id: str,
        source: str = "input",
    ) -> GuardrailAssignmentResponse:
        """Assign guardrail to all project datasources.

        Args:
            guardrail_id: ID of the guardrail to assign (AI run ID from installation)
            source: Source type ('input' or 'output')

        Returns:
            GuardrailAssignmentResponse with success status
        """
        logger.info(f"Assigning guardrail {guardrail_id} to all project datasources")

        assignment = GuardrailAssignmentRequest(
            project=GuardrailAssignmentEntity(settings=[], items=[]),
            assistants=GuardrailAssignmentEntity(settings=[], items=[]),
            workflows=GuardrailAssignmentEntity(settings=[], items=[]),
            datasources=GuardrailAssignmentEntity(
                settings=[GuardrailAssignmentSetting(mode="all", source=source)],
                items=[],
            ),
        )

        response = self.client.codemie_guardrails.assign_guardrails(
            guardrail_id=guardrail_id, assignment=assignment
        )

        if response.success:
            logger.info(
                f"Successfully assigned guardrail {guardrail_id} to all datasources"
            )
        else:
            logger.warning(
                f"Failed to assign guardrail {guardrail_id} to all datasources"
            )

        return response

    def assign_guardrail_to_all_project_entities(
        self,
        guardrail_id: str,
        source: str = "input",
    ) -> GuardrailAssignmentResponse:
        """Assign guardrail to all project entities (assistants, workflows, and datasources).

        Args:
            guardrail_id: ID of the guardrail to assign (AI run ID from installation)
            source: Source type ('input' or 'output')

        Returns:
            GuardrailAssignmentResponse with success status
        """
        logger.info(f"Assigning guardrail {guardrail_id} to all project entities")

        setting = GuardrailAssignmentSetting(mode="all", source=source)

        assignment = GuardrailAssignmentRequest(
            project=GuardrailAssignmentEntity(settings=[setting], items=[]),
            assistants=GuardrailAssignmentEntity(settings=[], items=[]),
            workflows=GuardrailAssignmentEntity(settings=[], items=[]),
            datasources=GuardrailAssignmentEntity(settings=[], items=[]),
        )

        response = self.client.codemie_guardrails.assign_guardrails(
            guardrail_id=guardrail_id, assignment=assignment
        )

        if response.success:
            logger.info(
                f"Successfully assigned guardrail {guardrail_id} to all project entities"
            )
        else:
            logger.warning(
                f"Failed to assign guardrail {guardrail_id} to all project entities"
            )

        return response
