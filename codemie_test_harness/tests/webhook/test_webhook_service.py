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

"""Webhook integration tests for CodeMie.

This module contains tests for webhook functionality including:
- Basic webhook operations with different resource types (assistant, workflow, datasource)
- Error handling and validation
- Webhook triggering verification
"""

import pytest
from codemie_sdk.models.datasource import DataSourceStatus
from requests import HTTPError

from codemie_sdk.models.workflow import ExecutionStatus
from hamcrest import (
    assert_that,
    equal_to,
    greater_than,
    has_length,
    has_item,
    any_of,
)
from codemie_test_harness.tests.utils.base_utils import (
    get_random_name,
    wait_for_entity,
)
from codemie_test_harness.tests.test_data.webhook_cross_user_test_data import (
    cross_user_execution_visibility_test_data,
)


@pytest.mark.webhook
@pytest.mark.api
class TestWebhookBasicOperations:
    """Basic webhook operations tests - verify webhook creation and triggering for different resource types."""

    def test_webhook_with_assistant(
        self, assistant, webhook_integration, webhook_utils, conversation_utils
    ):
        """Test webhook can be created with assistant and triggers conversation creation."""
        webhook_id = get_random_name()
        message = f"Test message for {webhook_id}"

        # Create assistant
        assistant = assistant()

        # Create webhook integration
        webhook_integration(webhook_id, "assistant", assistant.id)

        # Trigger webhook
        response = webhook_utils.trigger_webhook(webhook_id, data=message)
        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json()["message"], equal_to("Webhook invoked successfully")
        )

        # Wait for conversation
        conversation = wait_for_entity(
            lambda: conversation_utils.list_conversations(),
            entity_name=f"Webhook: {assistant.id}",
        )

        # Verify conversation details
        assert_that(conversation.name.strip('"'), equal_to(f"Webhook: {assistant.id}"))
        assert_that(conversation.initial_assistant_id, equal_to(assistant.id))
        assert_that(conversation.assistant_ids, has_item(assistant.id))

    def test_webhook_with_workflow(
        self,
        workflow_with_virtual_assistant,
        default_llm,
        webhook_integration,
        webhook_utils,
        workflow_utils,
    ):
        """Test webhook can be created with workflow and triggers workflow execution."""
        webhook_id = get_random_name()
        message = f"Test message for {webhook_id}"

        # Create a simple workflow
        workflow = workflow_with_virtual_assistant(webhook_id)

        # Create webhook integration
        webhook_integration(webhook_id, "workflow", workflow.id)

        # Trigger webhook
        response = webhook_utils.trigger_webhook(webhook_id, data=message)
        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json()["message"], equal_to("Webhook invoked successfully")
        )

        # Verify workflow execution was created
        executions = workflow_utils.get_executions(workflow)
        assert_that(
            executions,
            has_length(greater_than(0)),
            "Workflow execution should be created",
        )

        # Verify execution details
        execution = executions[0]

        assert_that(execution.prompt.strip('""'), equal_to(message))
        assert_that(execution.workflow_id, equal_to(workflow.id))
        assert_that(execution.status, equal_to(ExecutionStatus.IN_PROGRESS))

    @pytest.mark.requires_capability("retrieval")
    @pytest.mark.parametrize(
        "datasource_fixture",
        [
            pytest.param("jira_datasource", marks=pytest.mark.requires_setting("jira")),
            pytest.param(
                "confluence_datasource",
                marks=pytest.mark.requires_setting("confluence"),
            ),
            pytest.param(
                "code_datasource",
                marks=pytest.mark.requires_setting("gitlab", "github"),
            ),
            pytest.param(
                "xwiki_datasource",
                marks=[
                    pytest.mark.xwiki,
                    pytest.mark.skip(
                        reason="No xwiki test environment configured"
                    ),  # red_lock
                    pytest.mark.xfail(
                        reason=(
                            "xWiki is in UNSUPPORTED_WEBHOOK_DATASOURCE_TYPES by design "
                            "(settings_request_validator.py:69) — product conflict. "
                            "Desired behavior asserted here: webhook trigger "
                            "should succeed like the other datasource types; currently "
                            "rejected with HTTP 422 at webhook_integration(...) creation. "
                            "strict=True so this fails loudly (not a silent xpass) if the "
                            "exclusion is ever lifted without updating this marker."
                        ),
                        strict=True,
                    ),
                ],
            ),
        ],
    )
    def test_webhook_with_datasource(
        self,
        request,
        datasource_fixture,
        webhook_integration,
        webhook_utils,
        datasource_utils,
    ):
        """Test webhook can be created with datasource and triggers successfully.

        This test verifies webhook works with datasource as the resource type.
        After triggering the webhook, it verifies that datasource indexing is in progress.

        Test is parametrized to work with different datasource types:
        - jira_datasource
        - confluence_datasource
        - code_datasource
        - xwiki_datasource — marked xfail(strict=True):
          asserts the desired behavior (webhook trigger succeeds), not the shipped
          exclusion. Cron/scheduler-triggered reindex works for xWiki instead — see
          test_scheduler_with_datasource.
        """

        # Get the datasource from the fixture
        datasource = request.getfixturevalue(datasource_fixture)

        # Create webhook integration with datasource
        webhook_id = get_random_name()
        webhook_integration(webhook_id, "datasource", datasource.id)

        # Trigger webhook
        triggered_datasource = datasource_utils.get_datasource(datasource.id)
        response = webhook_utils.trigger_webhook(webhook_id)
        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json()["message"], equal_to("Webhook invoked successfully")
        )

        # Verify datasource exists and check its status (indexing should be in progress)
        triggered_datasource = datasource_utils.wait_for_update_date_change(
            datasource_id=datasource.id,
            initial_update_date=triggered_datasource.update_date,
        )

        assert_that(triggered_datasource.id, equal_to(datasource.id))
        assert_that(triggered_datasource.name, equal_to(datasource.name))
        assert_that(
            triggered_datasource.status,
            any_of(
                equal_to(DataSourceStatus.COMPLETED),
                equal_to(DataSourceStatus.IN_PROGRESS),
                equal_to(DataSourceStatus.FETCHING),
            ),
        )


@pytest.mark.webhook
@pytest.mark.api
class TestWebhookErrorHandling:
    """Tests for webhook error handling - invalid IDs and disabled webhooks."""

    def test_webhook_trigger_with_invalid_id(self, webhook_utils):
        """Test that triggering webhook with invalid ID returns error."""
        invalid_webhook_id = "non_existent_webhook_" + get_random_name()

        response = webhook_utils.trigger_webhook(invalid_webhook_id)

        # Should return a 400 identifying the missing webhook (not a generic 500 -
        # the router previously let a broad `except Exception` swallow the
        # HTTPException raised for this case and flatten it to 500; fixed to let
        # HTTPException propagate with its real status code and detail).
        assert_that(response.status_code, equal_to(400))
        assert_that(
            response.json()["detail"],
            equal_to(
                f"Webhook with ID '{invalid_webhook_id}' not found or not enabled"
            ),
        )

    def test_webhook_trigger_with_disabled_webhook(
        self, assistant, webhook_integration, webhook_utils, conversation_utils
    ):
        """Test that disabled webhook cannot be triggered."""
        assistant = assistant()
        webhook_id = get_random_name()
        message = f"Test message for {webhook_id}"

        # Create webhook in disabled state
        webhook_integration(webhook_id, "assistant", assistant.id, is_enabled=False)

        # Try to trigger disabled webhook
        response = webhook_utils.trigger_webhook(webhook_id, data=message)

        # Should return a 400 identifying the disabled webhook (not 200, and not a
        # generic 500 - see test_webhook_trigger_with_invalid_id for why).
        assert_that(response.status_code, equal_to(400))
        assert_that(
            response.json()["detail"],
            equal_to(f"Webhook with ID '{webhook_id}' not found or not enabled"),
        )

        conversations = conversation_utils.get_conversation_by_assistant_id(
            assistant.id
        )
        assert_that(len(conversations), equal_to(0))

    @pytest.mark.parametrize(
        "resource_type, error",
        [
            ("assistant", "Assistant not found"),
            ("workflow", "Workflow not found"),
            ("datasource", "Datasource not found"),
        ],
    )
    def test_webhook_invalid_resource_id(
        self, webhook_integration, resource_type, error
    ):
        """Test that creating a webhook with a non-existent resource ID returns 404."""
        webhook_id = get_random_name()
        invalid_resource_id = "invalid_resource_" + get_random_name()

        with pytest.raises(HTTPError) as exc_info:
            webhook_integration(webhook_id, resource_type, invalid_resource_id)

        assert_that(exc_info.value.response.status_code, equal_to(404))
        assert_that(
            exc_info.value.response.json()["error"]["message"],
            equal_to(error),
        )

    @pytest.mark.requires_capability("retrieval")
    def test_webhook_with_file_datasource(
        self,
        file_datasource,
        webhook_integration,
    ):
        """Test that creating a webhook with an unsupported datasource type returns 422."""
        webhook_id = get_random_name()

        with pytest.raises(HTTPError) as exc_info:
            webhook_integration(webhook_id, "datasource", file_datasource.id)

        assert_that(exc_info.value.response.status_code, equal_to(422))
        assert_that(
            exc_info.value.response.json()["error"]["message"],
            equal_to("Datasource type does not support triggering by webhook"),
        )


_ALL_MR_ACTIONS = [
    ("open", "open"),
    ("update", "update"),
    ("close", "close"),
    ("reopen", "reopen"),
    ("merge", "merge"),
    ("approved", "approved,unapproved"),
    ("unapproved", "approved,unapproved"),
]

_CONFIG_ROUNDTRIP_CASES = [
    "open",
    "update",
    "close",
    "reopen",
    "merge",
    "approved,unapproved",
    "open,merge",
]


@pytest.mark.webhook
@pytest.mark.integration
@pytest.mark.api
class TestGitLabWebhookEventFilter:
    """Tests for GitLab merge-request event filtering on webhook integrations."""

    @pytest.mark.parametrize("action,filter_value", _ALL_MR_ACTIONS)
    def test_allowed_mr_action_triggers_workflow(
        self,
        assistant,
        webhook_integration,
        webhook_utils,
        conversation_utils,
        action,
        filter_value,
    ):
        """Each of the 6 MR action types triggers the workflow when it is listed in the filter."""
        _assistant = assistant()
        webhook_id = get_random_name()
        token = get_random_name()

        webhook_integration(
            webhook_id,
            "assistant",
            _assistant.id,
            extra_credentials={
                "gitlab_webhook_token": token,
                "gitlab_event_filter": filter_value,
            },
        )

        response = webhook_utils.trigger_gitlab_webhook(
            webhook_id, token=token, action=action
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json()["message"], equal_to("Webhook invoked successfully")
        )
        wait_for_entity(
            lambda: conversation_utils.list_conversations(),
            entity_name=f"Webhook: {_assistant.id}",
        )

    @pytest.mark.parametrize("filter_value", _CONFIG_ROUNDTRIP_CASES)
    def test_event_filter_config_roundtrip(
        self, assistant, webhook_integration, integration_utils, filter_value
    ):
        """Event filter set during creation is returned verbatim by a subsequent GET."""
        _assistant = assistant()
        webhook_id = get_random_name()
        token = get_random_name()

        integration = webhook_integration(
            webhook_id,
            "assistant",
            _assistant.id,
            extra_credentials={
                "gitlab_webhook_token": token,
                "gitlab_event_filter": filter_value,
            },
        )

        fetched = integration_utils.get_integration_by_alias(
            integration.alias, integration.setting_type
        )
        stored_filter = next(
            (
                cv.value
                for cv in fetched.credential_values
                if cv.key == "gitlab_event_filter"
            ),
            None,
        )
        assert_that(stored_filter, equal_to(filter_value))

    @pytest.mark.parametrize(
        "blocked_action",
        ["update", "close", "reopen", "merge", "approved", "unapproved"],
    )
    def test_disallowed_mr_action_is_acknowledged_without_invoking_resource(
        self,
        assistant,
        webhook_integration,
        webhook_utils,
        conversation_utils,
        blocked_action,
    ):
        """Each non-open MR action is ACKed with 200 and never triggers the webhook
        when the filter is set to open-only.

        The backend must not surface a filter mismatch as 4xx: GitLab
        auto-deactivates webhook endpoints after repeated non-2xx responses,
        so routine filter rejections stay in the 2xx range (see codemie
        webhook.py — WEBHOOK_EVENT_FILTERED). No downstream conversation
        must be created.
        """
        assistant = assistant()
        webhook_id = get_random_name()
        token = get_random_name()

        webhook_integration(
            webhook_id,
            "assistant",
            assistant.id,
            extra_credentials={
                "gitlab_webhook_token": token,
                "gitlab_event_filter": "open",
            },
        )

        response = webhook_utils.trigger_gitlab_webhook(
            webhook_id, token=token, action=blocked_action
        )

        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json()["message"], equal_to("Webhook received, event filtered out")
        )
        conversations = conversation_utils.get_conversation_by_assistant_id(
            assistant.id
        )
        assert_that(len(conversations), equal_to(0))

    def test_empty_filter_allows_all_actions(
        self, assistant, webhook_integration, webhook_utils, conversation_utils
    ):
        """No filter configured means every MR action triggers the webhook (no regression)."""
        assistant = assistant()
        webhook_id = get_random_name()
        token = get_random_name()

        webhook_integration(
            webhook_id,
            "assistant",
            assistant.id,
            extra_credentials={"gitlab_webhook_token": token},
        )

        response = webhook_utils.trigger_gitlab_webhook(
            webhook_id, token=token, action="update"
        )

        assert_that(response.status_code, equal_to(200))
        wait_for_entity(
            lambda: conversation_utils.list_conversations(),
            entity_name=f"Webhook: {assistant.id}",
        )

    def test_invalid_gitlab_token_is_rejected(
        self, assistant, webhook_integration, webhook_utils
    ):
        """A wrong X-Gitlab-Token is rejected with 401, regardless of the filter."""
        assistant = assistant()
        webhook_id = get_random_name()

        webhook_integration(
            webhook_id,
            "assistant",
            assistant.id,
            extra_credentials={"gitlab_webhook_token": get_random_name()},
        )

        response = webhook_utils.trigger_gitlab_webhook(
            webhook_id, token="wrong-token", action="open"
        )

        assert_that(response.status_code, equal_to(401))


@pytest.mark.webhook
@pytest.mark.api
class TestMicrosoftGraphWebhookValidation:
    """Tests for Microsoft Graph subscription validation handshake.

    When creating a Microsoft Graph subscription with a CodeMie webhook as
    the notificationUrl, MS Graph sends a POST with ?validationToken=<token>.
    The endpoint must echo the exact token back as plain text (HTTP 200,
    Content-Type: text/plain).  See bug: webhook-autobtemail.
    """

    def test_msgraph_validation_returns_200(
        self, assistant, webhook_integration, webhook_utils
    ):
        """Validation request returns HTTP 200."""
        webhook_id = get_random_name()
        webhook_integration(webhook_id, "assistant", assistant().id)

        response = webhook_utils.simulate_msgraph_validation(
            webhook_id, "test-validation-token"
        )

        assert_that(response.status_code, equal_to(200))

    def test_msgraph_validation_content_type_is_plain_text(
        self, assistant, webhook_integration, webhook_utils
    ):
        """Validation response Content-Type must be text/plain."""
        webhook_id = get_random_name()
        webhook_integration(webhook_id, "assistant", assistant().id)

        response = webhook_utils.simulate_msgraph_validation(
            webhook_id, "test-validation-token"
        )

        assert_that(
            response.headers.get("Content-Type", ""),
            equal_to("text/plain; charset=utf-8"),
        )

    def test_msgraph_validation_body_is_exact_token(
        self, assistant, webhook_integration, webhook_utils
    ):
        """Validation response body must be the exact unmodified token."""
        webhook_id = get_random_name()
        token = "ExactToken_" + get_random_name()
        webhook_integration(webhook_id, "assistant", assistant().id)

        response = webhook_utils.simulate_msgraph_validation(webhook_id, token)

        assert_that(response.text, equal_to(token))


@pytest.mark.webhook
@pytest.mark.api
class TestWebhookCrossUserScenarios:
    """Regression tests for cross-user webhook-workflow scenarios."""

    @pytest.mark.parametrize(
        "is_platform_admin,is_project_admin",
        cross_user_execution_visibility_test_data,
    )
    def test_member_can_see_webhook_triggered_execution(
        self,
        is_platform_admin,
        is_project_admin,
        project_with_member_factory,
        workflow_with_virtual_assistant,
        webhook_integration,
        webhook_utils,
        workflow_utils,
    ):
        """Project member sees webhook-triggered execution regardless of platform/project role combo.

        AC: Members with any combination of platform role (admin / default)
        and project role (project admin / project user) see the same workflow execution
        history as the platform admin who triggered the webhook.
        """
        project_name, member_workflow_utils = project_with_member_factory(
            is_platform_admin, is_project_admin
        )

        webhook_id = get_random_name()
        workflow = workflow_with_virtual_assistant(
            assistant_and_state_name=webhook_id,
            project_name=project_name,
        )
        webhook_integration(
            webhook_id, "workflow", workflow.id, project_name=project_name
        )

        response = webhook_utils.trigger_webhook(
            webhook_id, data=f"Test for {webhook_id}"
        )
        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json()["message"], equal_to("Webhook invoked successfully")
        )

        admin_executions = workflow_utils.wait_for_executions(workflow)
        assert_that(admin_executions, has_length(greater_than(0)))

        member_executions = member_workflow_utils.get_executions(workflow)
        assert_that(
            member_executions,
            has_length(equal_to(len(admin_executions))),
            "Member should see the same number of executions as the platform admin",
        )

    def test_webhook_triggers_workflow_created_by_different_user(
        self,
        project_with_non_admin_member,
        member_workflow_with_virtual_assistant,
        webhook_integration,
        webhook_utils,
        workflow_utils,
    ):
        """Webhook created by admin triggers workflow owned by non-admin member.

        AC: Webhook-triggered workflow execution succeeds when
        the webhook creator (admin) and the workflow owner (non-admin member) are
        different users in the same project.
        """
        project_name, _ = project_with_non_admin_member

        webhook_id = get_random_name()
        workflow = member_workflow_with_virtual_assistant(
            assistant_and_state_name=webhook_id,
            project_name=project_name,
        )
        webhook_integration(
            webhook_id, "workflow", workflow.id, project_name=project_name
        )

        response = webhook_utils.trigger_webhook(
            webhook_id, data=f"Test for {webhook_id}"
        )
        assert_that(response.status_code, equal_to(200))
        assert_that(
            response.json()["message"], equal_to("Webhook invoked successfully")
        )

        executions = workflow_utils.wait_for_executions(workflow)
        assert_that(
            executions,
            has_length(greater_than(0)),
            "Workflow execution should be created even when webhook creator differs from workflow owner",
        )
