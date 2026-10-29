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

import time
from typing import List, Optional

from requests import HTTPError

from codemie_sdk.models.user import (
    AdminUserListItem,
    AdminUserProject,
    CodeMieUserDetail,
    PaginatedUserListResponse,
)
from codemie_test_harness.tests.utils.base_utils import BaseUtils


class UserUtils(BaseUtils):
    def get_about_me(self):
        return self.client.users.about_me()

    def get_user_data(self):
        return self.client.users.get_data()

    def list_admin_users(
        self,
        page: int = 0,
        per_page: int = 20,
        search: Optional[str] = None,
        filters: Optional[str] = None,
    ) -> PaginatedUserListResponse:
        return self.client.users.list_admin_users(
            page=page, per_page=per_page, search=search, filters=filters
        )

    def list_all_admin_users(
        self,
        search: Optional[str] = None,
        filters: Optional[str] = None,
    ) -> List[AdminUserListItem]:
        per_page = 1000
        page = 0
        all_users: List[AdminUserListItem] = []
        while True:
            response = self.list_admin_users(
                page=page, per_page=per_page, search=search, filters=filters
            )
            all_users.extend(response.data)
            if len(all_users) >= response.pagination.total:
                break
            page += 1
        return all_users

    def get_admin_user(self, user_id: str) -> CodeMieUserDetail:
        return self.client.users.get_admin_user(user_id)

    def update_admin_user(self, user_id: str, **kwargs) -> CodeMieUserDetail:
        return self.client.users.update_admin_user(user_id, **kwargs)

    def get_user_projects(self, user_id: str) -> List[AdminUserProject]:
        return self.client.users.get_user_projects(user_id)

    def get_user_project_names(self, user_id: str) -> List[str]:
        return [p.project_name for p in self.get_user_projects(user_id)]

    def assign_user_to_project(
        self, user_id: str, project_name: str, is_project_admin: bool = False
    ) -> dict:
        return self.client.users.assign_user_to_project(
            user_id=user_id,
            project_name=project_name,
            is_project_admin=is_project_admin,
        )

    def remove_user_from_project(self, user_id: str, project_name: str) -> None:
        self.client.users.remove_user_from_project(
            user_id=user_id, project_name=project_name
        )

    def update_user_project_role(
        self, user_id: str, project_name: str, is_project_admin: bool
    ) -> None:
        self.client.users.update_user_project_role(
            user_id=user_id,
            project_name=project_name,
            is_project_admin=is_project_admin,
        )

    def set_default_project(self, user_id: str, project_name: str) -> dict:
        return self.client.users.set_default_project(
            user_id=user_id, project_name=project_name
        )

    def clear_default_project(self, user_id: str, project_name: str) -> dict:
        return self.client.users.clear_default_project(
            user_id=user_id, project_name=project_name
        )

    def get_default_project_names(self, user_id: str) -> List[str]:
        return [p.project_name for p in self.get_user_projects(user_id) if p.is_default]

    def get_default_project_names_from_detail(self, user_id: str) -> List[str]:
        detail = self.get_admin_user(user_id)
        return [p.name for p in detail.projects if p.is_default]

    def get_default_project_names_from_list(
        self, user_id: str, search: str
    ) -> List[str]:
        rows = [u for u in self.list_admin_users(search=search).data if u.id == user_id]
        assert rows, f"User {user_id} not found in the users list for search '{search}'"
        return [p.name for p in rows[0].projects if p.is_default]

    def get_default_project_names_from_profile(self) -> List[str]:
        return [p.name for p in self.get_about_me().projects if p.is_default]

    def set_default_project_status_code(self, user_id: str, project_name: str) -> int:
        try:
            self.set_default_project(user_id, project_name)
            return 200
        except HTTPError as e:
            return e.response.status_code

    def clear_default_project_status_code(self, user_id: str, project_name: str) -> int:
        try:
            self.clear_default_project(user_id, project_name)
            return 200
        except HTTPError as e:
            return e.response.status_code

    def wait_until_user_management_effective(
        self, consecutive: int = 4, timeout: int = 120, interval: int = 2
    ) -> None:
        """Wait until this client's admin/maintainer role is active on every backend replica.

        Role changes reach a replica only after its user cache refreshes. The probe is 403 for
        users who cannot manage users and 404 (unknown user) for those who can; requiring several
        consecutive 404s makes it unlikely that a single fresh replica answered them all.
        """
        deadline = time.monotonic() + timeout
        streak = 0
        while time.monotonic() < deadline:
            status = self.clear_default_project_status_code(
                "nonexistent-user-id-000000", "nonexistent-project"
            )
            streak = streak + 1 if status == 404 else 0
            if streak >= consecutive:
                return
            time.sleep(interval)
        raise TimeoutError("User management role did not become effective in time")

    def deactivate_user(self, user_id: str) -> None:
        self.client.users.deactivate_user(user_id=user_id)

    def reactivate_user(self, user_id: str) -> CodeMieUserDetail:
        return self.client.users.reactivate_user(user_id=user_id)

    def get_admin_user_status_code(self, user_id: str) -> int:
        try:
            self.client.users.get_admin_user(user_id)
            return 200
        except HTTPError as e:
            return e.response.status_code

    def update_admin_user_status_code(self, user_id: str, **kwargs) -> int:
        try:
            self.client.users.update_admin_user(user_id, **kwargs)
            return 200
        except HTTPError as e:
            return e.response.status_code

    def deactivate_user_status_code(self, user_id: str) -> int:
        try:
            self.client.users.deactivate_user(user_id)
            return 200
        except HTTPError as e:
            return e.response.status_code

    def list_admin_users_status_code(self, **kwargs) -> int:
        try:
            self.client.users.list_admin_users(**kwargs)
            return 200
        except HTTPError as e:
            return e.response.status_code
