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

from typing import Any, Dict

from codemie_test_harness.tests.utils.base_utils import BaseUtils, get_random_name


class WebhookUtils(BaseUtils):
    """Utility class for webhook operations in CodeMie test harness."""

    def trigger_webhook(self, webhook_id: str, data: Dict[str, Any] = None):
        return self.client.webhook.trigger(webhook_id, data)

    def simulate_msgraph_validation(self, webhook_id: str, validation_token: str):
        return self.client.webhook.validate_msgraph_subscription(
            webhook_id, validation_token
        )

    def trigger_gitlab_webhook(
        self,
        webhook_id: str,
        token: str,
        action: str,
        event: str = "Merge Request Hook",
    ):
        """Trigger a webhook with a GitLab merge_request payload and headers.

        Args:
            webhook_id: Webhook ID to trigger
            token: Value sent in the X-Gitlab-Token header (must match the
                integration's configured gitlab_webhook_token to authenticate)
            action: GitLab MR action (open, close, merge, update, reopen,
                approved, unapproved)
            event: Value sent in the X-Gitlab-Event header
        """
        payload = {
            "object_kind": "merge_request",
            "event_type": "merge_request",
            "user": {"id": 1, "name": "Test User", "username": "test_user"},
            "project": {
                "id": 1,
                "name": "test-project",
                "path_with_namespace": "group/test-project",
            },
            "object_attributes": {
                "id": 1,
                "iid": 1,
                "title": "Test MR",
                "action": action,
                "source_branch": "feature/test",
                "target_branch": "main",
                "state": "opened",
                "url": "https://gitlab.example.com/group/test-project/-/merge_requests/1",
            },
        }
        return self.client.webhook.trigger(
            webhook_id,
            data=payload,
            extra_headers={
                "X-Gitlab-Token": token,
                "X-Gitlab-Event": event,
                "X-Gitlab-Delivery": get_random_name(),
            },
        )
