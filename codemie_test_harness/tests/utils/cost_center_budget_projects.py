"""Create projects with budgets that are linked to a cost center, and tear them down."""

import logging
import secrets

import requests

from codemie_test_harness.tests.test_data.budget_test_data import (
    BUDGET_CACHE_DELAY,
    PROJECT_BUDGET_TRACKING_DELAY,
    project_key_alias,
)
from codemie_test_harness.tests.utils.base_utils import poll_until
from codemie_test_harness.tests.utils.project_budget_groups import (
    ProjectBudget,
    ProjectBudgetGroups,
)
from codemie_test_harness.tests.utils.project_utils import ProjectUtils

logger = logging.getLogger(__name__)

_BUDGET_CATEGORIES = ("platform", "cli", "premium_models")
_POLL_INTERVAL = 5.0
# Upper bounds only: the waits end as soon as the backend is ready.
_GROUP_ACCEPTED_TIMEOUT = 2 * PROJECT_BUDGET_TRACKING_DELAY
_BUDGETS_USABLE_TIMEOUT = 2 * BUDGET_CACHE_DELAY
_INACTIVE_SYNC_STATUSES = ("pending", "failed")


class CostCenterBudgetProjects:
    """Creates projects with a budget group, linked to a cost center.

    A project is created by ``creator_utils`` (the admin by default) and linked to the cost
    center by the admin. Pass a user's ``ProjectUtils`` to make that user the project's only
    member, which a test needs when the user spends through the project.
    Teardown deletes the LiteLLM keys and cascades the project away, which also removes its
    budget groups; the ``project_budget_groups`` fixture then removes what is left.
    """

    def __init__(
        self,
        admin_project_utils: ProjectUtils,
        project_budget_groups: ProjectBudgetGroups,
        lite_llm_budget_utils,
    ):
        self._admin = admin_project_utils
        self._groups = project_budget_groups
        self._lite_llm = lite_llm_budget_utils
        self._project_names: list[str] = []

    def create(
        self,
        cost_center_id,
        categories: dict,
        budget_duration: str = "30d",
        creator_utils: ProjectUtils | None = None,
        track_members: bool = False,
    ) -> ProjectBudget:
        """Create a project linked to the cost center and give it a budget group.

        Args:
            cost_center_id: Cost center the project is linked to.
            categories: Category name to ``{"max_budget", "soft_budget"}``.
            budget_duration: Reset window of the budget group, e.g. ``"30d"``.
            creator_utils: ``ProjectUtils`` of the user that creates the project; the admin
                when omitted.
            track_members: Enable per-member budget tracking before the group is created, so
                members spend against the project budget.
        """
        project_name = f"autotest-project-{secrets.token_hex(4)}"
        (creator_utils or self._admin).create_project(
            name=project_name, description="Autotest cost center rollup project"
        )
        self._project_names.append(project_name)
        self._admin.update_project(project_name, cost_center_id=cost_center_id)
        if track_members:
            self._admin.enable_member_budget_tracking(project_name)
            return self._create_group_when_accepted(
                project_name, categories, budget_duration
            )
        return self._create_group(project_name, categories, budget_duration)

    def _create_group(
        self, project_name: str, categories: dict, budget_duration: str
    ) -> ProjectBudget:
        return self._groups.create(
            project_name,
            categories,
            name_prefix="autotest-ccroll",
            budget_duration=budget_duration,
        )

    def _create_group_when_accepted(
        self, project_name: str, categories: dict, budget_duration: str
    ) -> ProjectBudget:
        """Create the group, retrying while the budget group API refuses it.

        Member budget tracking takes a moment to settle after it is enabled, and a group
        created before that is refused. Only a refusal from the budget group API is retried;
        any other failure surfaces at once.
        """

        def attempt():
            try:
                return self._create_group(
                    project_name, categories, budget_duration
                ), None
            except requests.HTTPError as error:
                url = getattr(error.request, "url", "") or ""
                if "/project-budget-groups" not in url:
                    raise
                return None, error

        budget, error = poll_until(
            attempt,
            lambda result: result[0] is not None,
            timeout=_GROUP_ACCEPTED_TIMEOUT,
            interval=_POLL_INTERVAL,
        )
        if budget is None:
            raise TimeoutError(
                f"Budget group for project {project_name} was still refused after "
                f"{_GROUP_ACCEPTED_TIMEOUT:.0f}s of member budget tracking: {error}"
            ) from error
        return budget

    def wait_until_budgets_usable(self, *budgets: ProjectBudget) -> None:
        """Wait until every project's budget is readable through the projects API with its
        members allocated and its provider sync done, so members can spend against it."""

        def usable() -> dict[str, bool]:
            return {b.project_name: self._platform_budget_usable(b) for b in budgets}

        state = poll_until(
            usable,
            lambda by_project: all(by_project.values()),
            timeout=_BUDGETS_USABLE_TIMEOUT,
            interval=_POLL_INTERVAL,
        )
        not_ready = [name for name, ready in state.items() if not ready]
        if not_ready:
            raise TimeoutError(
                f"Budgets of projects {not_ready} were not usable after "
                f"{_BUDGETS_USABLE_TIMEOUT:.0f}s: no platform budget with allocated "
                f"members and finished provider sync in the projects API."
            )

    def _platform_budget_usable(self, budget: ProjectBudget) -> bool:
        projects = self._admin.list_projects(
            include_budgets=True, search=budget.project_name, per_page=10
        )
        item = next(
            (
                b
                for p in projects.data
                if p.name == budget.project_name
                for b in (p.budgets or [])
                if b.budget_category == "platform"
            ),
            None,
        )
        return (
            item is not None
            and item.member_count >= 1
            and (item.provider_sync_status or "").lower() not in _INACTIVE_SYNC_STATUSES
        )

    def cleanup(self) -> None:
        for project_name in reversed(self._project_names):
            for category in _BUDGET_CATEGORIES:
                try:
                    self._lite_llm.delete_key_by_alias(
                        project_key_alias(project_name, category)
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to delete LiteLLM key for project {project_name} "
                        f"category {category}: {e}"
                    )
            try:
                self._admin.delete_project_cascade(project_name)
            except Exception as e:
                logger.warning(f"Failed to delete project {project_name}: {e}")
