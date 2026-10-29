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

"""Admin utilities for managing applications/projects."""

from typing import Optional, List

from codemie_sdk.models.admin import AdminUserListItem, ApplicationCreateRequest

from codemie_test_harness.tests.utils.base_utils import BaseUtils


class AdminUtils(BaseUtils):
    """Utility class for admin operations on applications/projects."""

    def list_projects(self, name_filter: Optional[str] = None) -> List[str]:
        """Get list of all projects/applications.

        Args:
            name_filter: Optional project name to filter by

        Returns:
            List of application names
        """
        return self.client.admin.list_applications(project_name=name_filter)

    def create_project(self, project_name: str) -> str:
        """Create a new project/application.

        Args:
            project_name: Name of the project to create

        Returns:
            Created application name
        """
        request = ApplicationCreateRequest(name=project_name)
        return self.client.admin.create_application(request)

    def list_users(
        self, search: Optional[str] = None, page: int = 0, per_page: int = 20
    ) -> List[AdminUserListItem]:
        """List users through the admin client, in the order the backend returns them."""
        return self.client.admin.list_users(search=search, page=page, per_page=per_page)
