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

"""Utility functions for project management tests."""

import logging
import time
from datetime import datetime
from typing import Callable, List, Optional
from uuid import UUID

from codemie_sdk.models.integration import IntegrationType
from codemie_sdk.models.project import (
    BulkAssignmentResponse,
    BulkAssignmentUserItem,
    CsvImportValidationResponse,
    PaginatedProjectListResponse,
    ProjectAssignmentResponse,
    ProjectBudgetItem,
    ProjectCreateResponse,
    ProjectDeleteResponse,
    ProjectDetailResponse,
    ProjectListItem,
    ProjectOwnershipUpdateResponse,
    ProjectUpdateResponse,
)
from codemie_test_harness.tests.utils.admin_project_budget_utils import (
    AdminProjectBudgetUtils,
)
from codemie_test_harness.tests.utils.base_utils import BaseUtils

_BUDGET_SPENDING_POLL_INTERVAL = 10
logger = logging.getLogger(__name__)


class ProjectUtils(BaseUtils):
    """Helper class for project management operations."""

    def create_project(
        self,
        name: str,
        description: Optional[str] = None,
        cost_center_id: Optional[UUID] = None,
        display_name: Optional[str] = None,
        cli_analytics_enabled: Optional[bool] = None,
    ) -> ProjectCreateResponse:
        """Create a new project.

        Args:
            name: Project name
            description: Project description (optional — omitted entirely when None)
            cost_center_id: Optional cost center ID
            display_name: Human-friendly display name (max 150 chars)
            cli_analytics_enabled: Enable CLI analytics ingestion (None = not sent)

        Returns:
            ProjectCreateResponse with created project details
        """
        return self.client.projects.create_project(
            name=name,
            description=description,
            cost_center_id=cost_center_id,
            display_name=display_name,
            cli_analytics_enabled=cli_analytics_enabled,
        )

    def list_projects(
        self,
        search: Optional[str] = None,
        page: int = 0,
        per_page: int = 20,
        include_counters: bool = True,
        include_budgets: bool = False,
        has_assigned_budgets: bool = False,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> PaginatedProjectListResponse:
        """List projects with pagination and filters.

        Args:
            search: Optional search string to filter projects by name
            page: Page number (0-indexed)
            per_page: Number of results per page (10-100)
            include_counters: Whether to include member and assistant counts
            include_budgets: Whether to include compact assigned budget summaries
            has_assigned_budgets: Return only projects with at least one active
                assigned project budget
            sort_by: Field to sort by ('name' or 'created_at')
            sort_order: Sort order ('asc' or 'desc')

        Returns:
            PaginatedProjectListResponse with list of projects and pagination info
        """
        return self.client.projects.list_projects(
            search=search,
            page=page,
            per_page=per_page,
            include_counters=include_counters,
            include_budgets=include_budgets,
            has_assigned_budgets=has_assigned_budgets,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def list_all_projects(
        self,
        search: Optional[str] = None,
        per_page: int = 10,
        include_counters: bool = True,
        include_budgets: bool = False,
        has_assigned_budgets: bool = False,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> List[ProjectListItem]:
        """List every project matching the given filters, across all pages.

        Args:
            search: Optional search string to filter projects by name
            per_page: Page size used while paginating (10-100)
            include_counters: Whether to include member and assistant counts
            include_budgets: Whether to include compact assigned budget summaries
            has_assigned_budgets: Return only projects with at least one active
                assigned project budget
            sort_by: Field to sort by ('name' or 'created_at')
            sort_order: Sort order ('asc' or 'desc')

        Returns:
            All matching projects, collected across every page
        """
        page = 0
        all_projects: List[ProjectListItem] = []
        while True:
            response = self.list_projects(
                search=search,
                page=page,
                per_page=per_page,
                include_counters=include_counters,
                include_budgets=include_budgets,
                has_assigned_budgets=has_assigned_budgets,
                sort_by=sort_by,
                sort_order=sort_order,
            )
            all_projects.extend(response.data)
            if len(all_projects) >= response.pagination.total:
                break
            page += 1
        return all_projects

    def wait_for_project_budget_spending(
        self,
        project_name: str,
        budget_category: str,
        timeout: int = 600,
    ) -> Optional[ProjectBudgetItem]:
        """Poll until the given budget category has non-null current_spending."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            projects = self.list_projects(
                include_budgets=True, search=project_name, per_page=10
            )
            if projects.data:
                budget = next(
                    (
                        b
                        for b in projects.data[0].budgets
                        if b.budget_category == budget_category
                        and b.current_spending is not None
                    ),
                    None,
                )
                if budget is not None:
                    return budget
            time.sleep(_BUDGET_SPENDING_POLL_INTERVAL)
        projects = self.list_projects(
            include_budgets=True, search=project_name, per_page=10
        )
        if not projects.data:
            return None
        return next(
            (
                b
                for b in projects.data[0].budgets
                if b.budget_category == budget_category
                and b.current_spending is not None
            ),
            None,
        )

    def get_project_detail(
        self,
        project_name: str,
    ) -> ProjectDetailResponse:
        """Get project detail with member list.

        Args:
            project_name: Name of the project

        Returns:
            ProjectDetailResponse with project details and member list
        """
        return self.client.projects.get_project_detail(
            project_name=project_name,
        )

    def enable_member_budget_tracking(self, project_name: str) -> ProjectUpdateResponse:
        """Enable per-member spend limit enforcement for a project."""
        return self.set_enforce_member_spend_limits(project_name, True)

    def set_enforce_member_spend_limits(
        self, project_name: str, enabled: bool
    ) -> ProjectUpdateResponse:
        """Set the enforce_member_spend_limits flag for a project."""
        return self.client.projects.update_project(
            project_name=project_name,
            enforce_member_spend_limits=enabled,
        )

    def update_project(
        self,
        project_name: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        clear_description: bool = False,
        cost_center_id: Optional[UUID] = None,
        clear_cost_center: bool = False,
        display_name: Optional[str] = None,
        chargeback_attribution: Optional[str] = None,
        cli_analytics_enabled: Optional[bool] = None,
    ) -> ProjectUpdateResponse:
        """Update a project.

        Args:
            project_name: Current project name
            name: New project name (optional)
            description: New project description (optional)
            clear_description: Set to True to remove the description (mutually
                exclusive with passing `description`)
            cost_center_id: New cost center ID (optional)
            clear_cost_center: Whether to clear the cost center
            display_name: Human-friendly display name (max 150 chars)
            chargeback_attribution: Chargeback attribution mode ("project" or "cost_center")
            cli_analytics_enabled: Enable/disable CLI analytics ingestion (None = not sent)

        Returns:
            ProjectUpdateResponse with updated project details
        """
        return self.client.projects.update_project(
            project_name=project_name,
            name=name,
            description=description,
            clear_description=clear_description,
            cost_center_id=cost_center_id,
            clear_cost_center=clear_cost_center,
            display_name=display_name,
            chargeback_attribution=chargeback_attribution,
            cli_analytics_enabled=cli_analytics_enabled,
        )

    def delete_project_with_all_members(self, project_name: str) -> None:
        """Remove every member, then delete the project.

        Projects created through the admin endpoint have no creator, so any remaining
        member blocks DELETE with 409 (unlike delete_project_cascade, nobody is spared).
        """
        for member in self.get_project_detail(project_name).members:
            self.remove_user_from_project(project_name, member.user_id)
        self.delete_project(project_name)

    def delete_project(self, project_name: str) -> ProjectDeleteResponse:
        """Delete a project.

        Args:
            project_name: Name of the project to delete

        Returns:
            ProjectDeleteResponse with deletion confirmation
        """
        return self.client.projects.delete_project(project_name=project_name)

    def assign_user_to_project(
        self,
        project_name: str,
        user_id: str,
        is_project_admin: bool,
    ) -> ProjectAssignmentResponse:
        """Assign a user to a project."""
        return self.client.projects.assign_user_to_project(
            project_name=project_name,
            user_id=user_id,
            is_project_admin=is_project_admin,
        )

    def transfer_ownership(
        self,
        project_name: str,
        user_id: str,
    ) -> ProjectOwnershipUpdateResponse:
        """Transfer ownership of a project to another active user."""
        return self.client.projects.transfer_ownership(
            project_name=project_name,
            user_id=user_id,
        )

    def wait_for_project_member(
        self, project_name: str, user_id: str, timeout: int = 60
    ) -> None:
        """Poll until user_id appears in the project member list."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            detail = self.get_project_detail(project_name)
            if any(m.user_id == user_id for m in detail.members):
                return
            time.sleep(5)

    def update_user_project_assignment(
        self,
        project_name: str,
        user_id: str,
        is_project_admin: bool,
    ) -> ProjectAssignmentResponse:
        """Update a user's project assignment role."""
        return self.client.projects.update_user_project_assignment(
            project_name=project_name,
            user_id=user_id,
            is_project_admin=is_project_admin,
        )

    def remove_all_project_members(self, project_name: str) -> None:
        """Remove all members from a project (required before deletion)."""
        detail = self.get_project_detail(project_name)
        for member in detail.members:
            try:
                self.remove_user_from_project(project_name, member.user_id)
            except Exception as e:
                logger.warning(
                    "Could not remove member %s from project %s (skipped): %s",
                    member.user_id,
                    project_name,
                    e,
                )

    def remove_all_project_integrations(self, project_name: str) -> None:
        """Remove all integration settings for a project (required before deletion)."""
        integrations = self.client.integrations.list(
            setting_type=IntegrationType.PROJECT,
            filters={"project": project_name},
            per_page=100,
        )
        for integration in integrations:
            try:
                self.client.integrations.delete(
                    setting_id=integration.id,
                    setting_type=IntegrationType.PROJECT,
                )
            except Exception as e:
                logger.warning(
                    "Could not remove integration %s from project %s (skipped): %s",
                    integration.id,
                    project_name,
                    e,
                )

    def _delete_matching(
        self,
        label: str,
        fetch,
        delete,
        get_id,
        get_name,
        project_name: str,
        per_page: int = 100,
    ) -> None:
        """Repeatedly fetch and delete matching entities until none remain.

        Loops rather than assuming one page is enough, and catches per-item
        failures (logged, not raised) so one bad delete doesn't abort the
        rest — same convention as remove_all_project_members/
        remove_all_project_integrations above.
        """
        while True:
            entities = fetch(per_page)
            if not entities:
                break
            for entity in entities:
                try:
                    delete(entity)
                except Exception as e:
                    logger.warning(
                        "Could not delete %s %s (%s) from project %s (skipped): %s",
                        label,
                        get_name(entity),
                        get_id(entity),
                        project_name,
                        e,
                    )
            if len(entities) < per_page:
                break

    def delete_project_budgets(self, project_name: str) -> None:
        """Delete every budget group assigned to a project (required before
        deletion — DELETE /v1/projects/{name} 409s if any remain). Project
        budgets are only ever created via budget groups now, and deleting a
        group cascades to all of its category budgets.
        """
        budget_utils = AdminProjectBudgetUtils(self.client)

        response = self.client.project_budget_groups.list_by_project(project_name)
        for group in response.get("items", []):
            try:
                budget_utils.delete_budget_group(group["group_id"])
            except Exception as e:
                logger.warning(
                    "Could not delete budget group %s from project %s (skipped): %s",
                    group["group_id"],
                    project_name,
                    e,
                )

    def delete_project_scoped_entities(self, project_name: str) -> None:
        """Delete every assistant, workflow, datasource, and skill scoped to
        a project (required before deletion — DELETE /v1/projects/{name}
        409s if any remain). Fixtures use this cascade instead of a
        one-off sweep script.
        """

        def _fetch_assistants(per_page):
            # scope="visible_to_user" surfaces assistants owned by/visible to
            # this client; scope="marketplace" surfaces shared assistants
            # regardless of this client's project membership. Neither alone
            # covers every assistant in the project, so union both by id.
            by_id = {}
            for scope in ("visible_to_user", "marketplace"):
                for a in self.client.assistants.list(
                    filters={"project": [project_name]},
                    scope=scope,
                    per_page=per_page,
                ):
                    by_id[a.id] = a
            return list(by_id.values())

        self._delete_matching(
            "assistant",
            _fetch_assistants,
            lambda a: self.client.assistants.delete(assistant_id=a.id),
            get_id=lambda a: a.id,
            get_name=lambda a: a.name,
            project_name=project_name,
        )
        self._delete_matching(
            "workflow",
            lambda per_page: self.client.workflows.list(
                filters={"project": [project_name]}, per_page=per_page
            ),
            lambda w: self.client.workflows.delete(workflow_id=w.id),
            get_id=lambda w: w.id,
            get_name=lambda w: w.name,
            project_name=project_name,
        )
        self._delete_matching(
            "datasource",
            lambda per_page: self.client.datasources.list(
                filters={"project": [project_name]}, per_page=per_page
            ),
            lambda d: self.client.datasources.delete(datasource_id=d.id),
            get_id=lambda d: d.id,
            get_name=lambda d: d.name,
            project_name=project_name,
        )
        self._delete_matching(
            "skill",
            lambda per_page: self.client.skills.list(
                filters={"project": [project_name]}, per_page=per_page
            ).skills,
            lambda s: self.client.skills.delete(s.id),
            get_id=lambda s: s.id,
            get_name=lambda s: s.name,
            project_name=project_name,
        )

    def remove_extra_project_members(self, project_name: str) -> None:
        """Unassign every project member except the earliest-added one,
        treated as the creator (there's no reliable created_by on
        test-created projects).
        """
        detail = self.get_project_detail(project_name)
        if len(detail.members) <= 1:
            return
        creator = min(detail.members, key=lambda m: m.date or datetime.min)
        for member in detail.members:
            if member.user_id == creator.user_id:
                continue
            try:
                self.remove_user_from_project(project_name, member.user_id)
            except Exception as e:
                logger.warning(
                    "Could not remove member %s from project %s (skipped): %s",
                    member.user_id,
                    project_name,
                    e,
                )

    def delete_project_cascade(self, project_name: str) -> None:
        """Fully tear down a project for deletion: unassign every member
        except the creator, delete every budget/budget-group and every
        assistant/workflow/datasource/skill scoped to it, then delete the
        project itself.

        Integrations are intentionally NOT removed first — DELETE
        /v1/projects/{name} does not block on them.
        """
        self.remove_extra_project_members(project_name)
        self.delete_project_budgets(project_name)
        self.delete_project_scoped_entities(project_name)
        self.delete_project(project_name)

    def delete_matching_projects(
        self, name_predicate: Callable[[str], bool], search: Optional[str] = None
    ) -> int:
        """Cascade-delete every project whose name satisfies name_predicate.

        `search` narrows the initial list_all_projects call server-side
        (e.g. to this session's own random prefix); name_predicate is
        always re-checked client-side since search is a substring match,
        not a full naming-pattern match. Per-project failures are logged
        and skipped so one bad delete doesn't abort the rest of the sweep.

        Projects whose name contains "@" are never touched, regardless of
        name_predicate: on this platform, personal projects are named
        after a real user's email (e.g. "someone@example.com"), and a bare
        substring predicate (a session's random 3-letter prefix, or any
        other loose match) can coincidentally match one by chance on a
        shared, multi-tenant environment. This guard is unconditional —
        callers cannot opt out of it.
        """
        projects = self.list_all_projects(search=search)
        count = 0
        for project in projects:
            if "@" in project.name:
                if name_predicate(project.name):
                    logger.warning(
                        "Refusing to delete project %s: looks like a real user's "
                        "email-based project, not a test artifact (matched by "
                        "predicate but excluded unconditionally)",
                        project.name,
                    )
                continue
            if not name_predicate(project.name):
                continue
            try:
                self.delete_project_cascade(project.name)
                count += 1
            except Exception as e:
                logger.warning(
                    "Could not delete project %s (skipped): %s", project.name, e
                )
        return count

    def remove_user_from_project(
        self,
        project_name: str,
        user_id: str,
    ) -> ProjectAssignmentResponse:
        """Remove a user from a project."""
        return self.client.projects.remove_user_from_project(
            project_name=project_name,
            user_id=user_id,
        )

    def bulk_assign_users_to_project(
        self,
        project_name: str,
        users: list[BulkAssignmentUserItem],
    ) -> BulkAssignmentResponse:
        """Bulk assign users to a project."""
        return self.client.projects.bulk_assign_users_to_project(
            project_name=project_name,
            users=users,
        )

    def bulk_remove_users_from_project(
        self,
        project_name: str,
        user_ids: list[str],
    ) -> BulkAssignmentResponse:
        """Bulk remove users from a project."""
        return self.client.projects.bulk_remove_users_from_project(
            project_name=project_name,
            user_ids=user_ids,
        )

    def validate_users_from_csv(
        self,
        project_name: str,
        file_content: bytes,
        filename: str = "users.csv",
    ) -> CsvImportValidationResponse:
        """Validate CSV file for user import."""
        return self.client.projects.validate_users_from_csv(
            project_name=project_name,
            file_content=file_content,
            filename=filename,
        )

    def import_users_from_csv(
        self,
        project_name: str,
        file_content: bytes,
        filename: str = "users.csv",
    ) -> BulkAssignmentResponse:
        """Import users from CSV file."""
        return self.client.projects.import_users_from_csv(
            project_name=project_name,
            file_content=file_content,
            filename=filename,
        )
