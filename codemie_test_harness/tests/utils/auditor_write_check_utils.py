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

"""Utilities for verifying 403 write-denial behaviour for the Auditor role.

These helpers make write-endpoint HTTP calls using the auditor's bearer token
and return the raw status code.  They intentionally use `requests` directly
(consistent with admin_budget_utils.py and admin_project_budget_utils.py) because
they need to inspect the HTTP status code rather than rely on SDK exception paths.
"""

import uuid

import requests

from codemie_test_harness.tests import API_DOMAIN, VERIFY_SSL
from codemie_test_harness.tests.utils.base_utils import BaseUtils


class AuditorWriteCheckUtils(BaseUtils):
    """Attempt write operations as the auditor and return HTTP status codes.

    Usage (in tests):
        utils = AuditorWriteCheckUtils(auditor_client)
        status = utils.attempt_create_project()
        assert_that(status, equal_to(403), "Project create must be denied for auditor")
    """

    def __init__(self, client):
        super().__init__(client)
        self._headers = {
            "Authorization": f"Bearer {client.token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _call(request_fn) -> "requests.Response":
        """Execute a requests callable and convert low-level errors to RuntimeError.

        Parity-comparison tests (TC-014) compare two status codes; an unhandled
        ``ConnectionError`` or ``Timeout`` would crash the test with a confusing
        traceback instead of a clear assertion failure.  Converting it to
        ``RuntimeError`` surfaces the root cause (API unreachable / slow) while
        still failing the test cleanly.
        """
        try:
            return request_fn()
        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError(
                f"API unreachable during auditor write-check "
                f"(is {API_DOMAIN} accessible?): {exc}"
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise RuntimeError(
                f"Request timed out during auditor write-check: {exc}"
            ) from exc

    # ── Project write operations ───────────────────────────────────────────────

    def attempt_create_project(self) -> int:
        """POST /v1/projects — returns HTTP status code.

        Uses a valid payload so that permission checks (not validation) determine the
        response code.  Expected: 403 for auditor (AC-7); 201 would indicate the
        backend has not yet implemented the auditor restriction for project creation.
        """
        payload = {
            "name": f"auditor-forbidden-{uuid.uuid4().hex[:8]}",
            "description": "Forbidden project creation by auditor",
            "type": "platform",
        }
        resp = self._call(
            lambda: requests.post(
                f"{API_DOMAIN}/v1/projects",
                json=payload,
                headers=self._headers,
                verify=VERIFY_SSL,
            )
        )
        # If the project was actually created (2xx), clean it up so the env stays clean.
        if resp.status_code in (200, 201):
            try:
                project_name = resp.json().get("name", "")
                if project_name:
                    requests.delete(
                        f"{API_DOMAIN}/v1/projects/{project_name}",
                        headers=self._headers,
                        verify=VERIFY_SSL,
                    )
            except Exception:
                pass
        return resp.status_code

    def attempt_edit_project(self, project_name: str) -> int:
        """PATCH /v1/projects/{project_name} — returns HTTP status code."""
        resp = self._call(
            lambda: requests.patch(
                f"{API_DOMAIN}/v1/projects/{project_name}",
                json={"description": "Auditor should not be able to edit"},
                headers=self._headers,
                verify=VERIFY_SSL,
            )
        )
        return resp.status_code

    def attempt_delete_project(self, project_name: str) -> int:
        """DELETE /v1/projects/{project_name} — returns HTTP status code."""
        resp = self._call(
            lambda: requests.delete(
                f"{API_DOMAIN}/v1/projects/{project_name}",
                headers=self._headers,
                verify=VERIFY_SSL,
            )
        )
        return resp.status_code

    def attempt_add_project_member(self, project_name: str, user_id: str) -> int:
        """POST /v1/projects/{project_name}/assignment — returns HTTP status code."""
        resp = self._call(
            lambda: requests.post(
                f"{API_DOMAIN}/v1/projects/{project_name}/assignment",
                json={"user_id": user_id, "role": "user"},
                headers=self._headers,
                verify=VERIFY_SSL,
            )
        )
        return resp.status_code

    # ── User write operations ──────────────────────────────────────────────────

    def attempt_create_user(self) -> int:
        """POST /v1/admin/users — returns HTTP status code."""
        payload = {
            "email": f"auditor-forbidden-{uuid.uuid4().hex[:8]}@test.invalid",
            "full_name": "Auditor Forbidden User",
            "password": "Forbidden123!",
        }
        resp = self._call(
            lambda: requests.post(
                f"{API_DOMAIN}/v1/admin/users",
                json=payload,
                headers=self._headers,
                verify=VERIFY_SSL,
            )
        )
        return resp.status_code

    def attempt_edit_user(self, user_id: str) -> int:
        """PUT /v1/admin/users/{user_id} — returns HTTP status code."""
        resp = self._call(
            lambda: requests.put(
                f"{API_DOMAIN}/v1/admin/users/{user_id}",
                json={"full_name": "Auditor Should Not Edit"},
                headers=self._headers,
                verify=VERIFY_SSL,
            )
        )
        return resp.status_code

    def attempt_deactivate_user(self, user_id: str) -> int:
        """DELETE /v1/admin/users/{user_id} — returns HTTP status code.

        Matches the SDK's ``deactivate_user`` which issues a DELETE.
        """
        resp = self._call(
            lambda: requests.delete(
                f"{API_DOMAIN}/v1/admin/users/{user_id}",
                headers=self._headers,
                verify=VERIFY_SSL,
            )
        )
        return resp.status_code

    def attempt_change_user_role(self, user_id: str) -> int:
        """PUT /v1/admin/users/{user_id} — returns HTTP status code.

        Matches the SDK's ``update_user`` which issues a PUT with role fields.
        """
        resp = self._call(
            lambda: requests.put(
                f"{API_DOMAIN}/v1/admin/users/{user_id}",
                json={"is_auditor": True},
                headers=self._headers,
                verify=VERIFY_SSL,
            )
        )
        return resp.status_code

    # ── Budget write operations ────────────────────────────────────────────────

    def attempt_create_budget(self) -> int:
        """POST /v1/admin/budgets — returns HTTP status code."""
        payload = {
            "budget_id": f"auditor-forbidden-{uuid.uuid4().hex[:8]}",
            "name": "Auditor Forbidden Budget",
            "soft_budget": 10.0,
            "max_budget": 20.0,
            "budget_duration": "30d",
            "budget_category": "platform",
        }
        resp = self._call(
            lambda: requests.post(
                f"{API_DOMAIN}/v1/admin/budgets",
                json=payload,
                headers=self._headers,
                verify=VERIFY_SSL,
            )
        )
        return resp.status_code

    def attempt_edit_budget(self, budget_id: str) -> int:
        """PATCH /v1/admin/budgets/{budget_id} — returns HTTP status code."""
        resp = self._call(
            lambda: requests.patch(
                f"{API_DOMAIN}/v1/admin/budgets/{budget_id}",
                json={"name": "Auditor Should Not Edit"},
                headers=self._headers,
                verify=VERIFY_SSL,
            )
        )
        return resp.status_code

    def attempt_sync_budgets(self) -> int:
        """POST /v1/admin/budgets/sync — returns HTTP status code."""
        resp = self._call(
            lambda: requests.post(
                f"{API_DOMAIN}/v1/admin/budgets/sync",
                headers=self._headers,
                verify=VERIFY_SSL,
            )
        )
        return resp.status_code

    def attempt_assign_budget(self, user_id: str, budget_id: str) -> int:
        """PUT /v1/admin/users/{user_id}/budgets — returns HTTP status code."""
        resp = self._call(
            lambda: requests.put(
                f"{API_DOMAIN}/v1/admin/users/{user_id}/budgets",
                json={"assignments": {"platform": budget_id}},
                headers=self._headers,
                verify=VERIFY_SSL,
            )
        )
        return resp.status_code
