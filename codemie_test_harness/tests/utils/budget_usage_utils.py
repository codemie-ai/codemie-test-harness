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

"""Read the personal spending page and the admin per-project spending table through the SDK."""

import logging
import time
from dataclasses import dataclass, field

from codemie_test_harness.tests.test_data.budget_test_data import (
    CLI_CLIENT_HEADER,
    CLI_PROJECT_HEADER,
    MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE,
    budget_chat_prompt_bigger,
)
from codemie_test_harness.tests.test_data.budget_usage_project_rows_test_data import (
    KEY_SPEND_SETTLE_TIMEOUT,
    MIN_VISIBLE_SPEND,
    MONEY_TOLERANCE,
    PERCENT_TOLERANCE,
    ROW_WAIT_INTERVAL,
    ROW_WAIT_TIMEOUT,
    SPEND_MAX_BATCHES,
    SPEND_POLL_INTERVAL,
    SPEND_POLL_TIMEOUT,
    SPEND_REQUEST_MAX_TOKENS,
    SPEND_REQUEST_TIMEOUT,
    SPEND_REQUESTS_PER_BATCH,
    SPEND_SETTLE_CHECKS,
    SPEND_STABLE_READS,
    STORED_ROW_POLL_INTERVAL,
    STORED_ROW_WAIT_TIMEOUT,
    USAGE_WAIT_TIMEOUT,
    VISIBLE_AT_TWO_DECIMALS,
)
from codemie_test_harness.tests.utils.base_utils import BaseUtils, poll_until
from codemie_test_harness.tests.utils.project_budget_groups import ProjectBudget

logger = logging.getLogger(__name__)


@dataclass
class MemberProject:
    """A project owned by one user with one assigned member and, optionally, more members.

    ``budget`` is None for a project created without a budget group.
    """

    name: str
    member_id: str
    member_email: str
    budget: ProjectBudget | None = None
    owner_id: str | None = None
    extra_member_ids: list[str] = field(default_factory=list)

    @property
    def platform_budget_id(self) -> str:
        return self.budget.budget_ids["platform"]

    @property
    def user_ids(self) -> list[str]:
        """Owner, member and extra members: everybody who can hold an allocation."""
        owner = [self.owner_id] if self.owner_id else []
        return [*owner, self.member_id, *self.extra_member_ids]


def row_names(rows: list[dict]) -> list[str]:
    return [row["project_name"] for row in rows]


class BudgetUsageUtils(BaseUtils):
    """Reads of the calling client's budget usage and of the admin user-project-spending table."""

    def get_rows(self) -> list[dict]:
        return self.client.analytics.get_budget_usage().data.rows

    def get_column_ids(self) -> list[str]:
        return [
            column.id
            for column in self.client.analytics.get_budget_usage().data.columns
        ]

    def get_row_names(self) -> list[str]:
        return row_names(self.get_rows())

    def get_row_names_among(self, labels: list[str]) -> list[str]:
        """Names of the rows whose name is one of ``labels``, in response order."""
        return [name for name in self.get_row_names() if name in labels]

    def get_row_names_with_prefix(self, prefix: str) -> list[str]:
        """Names of the rows starting with ``prefix``, in response order."""
        return [name for name in self.get_row_names() if name.startswith(prefix)]

    def get_row_names_outside(self, labels: list[str]) -> list[str]:
        """Names of the rows whose name is none of ``labels``, in response order."""
        return [name for name in self.get_row_names() if name not in labels]

    def wait_for_row_names_among(
        self, labels: list[str], count: int, timeout: float = ROW_WAIT_TIMEOUT
    ) -> list[str]:
        """Poll until ``count`` rows named in ``labels`` exist; returns the last read."""
        return poll_until(
            lambda: self.get_row_names_among(labels),
            lambda names: len(names) >= count,
            timeout=timeout,
            interval=ROW_WAIT_INTERVAL,
        )

    def get_row(self, row_name: str) -> dict | None:
        return next(
            (row for row in self.get_rows() if row["project_name"] == row_name), None
        )

    def wait_for_row(self, row_name: str, timeout: float = ROW_WAIT_TIMEOUT):
        """Poll until the row exists; returns the last read, which is None if it never appeared."""
        return poll_until(
            lambda: self.get_row(row_name),
            lambda row: row is not None,
            timeout=timeout,
            interval=ROW_WAIT_INTERVAL,
        )

    def wait_for_row_where(
        self, row_name: str, predicate, timeout: float = USAGE_WAIT_TIMEOUT
    ):
        """Poll until ``predicate(row)`` holds for the row; returns the last read (None if absent)."""
        return poll_until(
            lambda: self.get_row(row_name),
            lambda row: row is not None and predicate(row),
            timeout=timeout,
            interval=ROW_WAIT_INTERVAL,
        )

    def wait_for_rows_where(self, predicate, timeout: float = ROW_WAIT_TIMEOUT):
        """Poll until ``predicate(rows)`` holds for the whole response; returns the last read."""
        return poll_until(
            self.get_rows,
            predicate,
            timeout=timeout,
            interval=ROW_WAIT_INTERVAL,
        )

    def wait_for_budget_limit(
        self,
        row_name: str,
        budget_limit: float,
        timeout: float = ROW_WAIT_TIMEOUT,
    ):
        """Poll until the row shows ``budget_limit``; returns the last read row."""
        return poll_until(
            lambda: self.get_row(row_name),
            lambda row: row is not None and row["budget_limit"] == budget_limit,
            timeout=timeout,
            interval=ROW_WAIT_INTERVAL,
        )

    def wait_for_current_spending(
        self, row_name: str, timeout: float = ROW_WAIT_TIMEOUT
    ):
        """Poll until the row shows a non-zero current_spending; returns the last read row."""
        return poll_until(
            lambda: self.get_row(row_name),
            lambda row: row is not None and row["current_spending"] > 0,
            timeout=timeout,
            interval=ROW_WAIT_INTERVAL,
        )

    def wait_for_user_project_limit(
        self, email: str, project_name: str, timeout: float = ROW_WAIT_TIMEOUT
    ):
        """Poll until the admin row shows a platform limit; returns the last read row."""
        return poll_until(
            lambda: self.get_user_project_spending_row(email, project_name),
            lambda row: row is not None and row["platform_limit"] is not None,
            timeout=timeout,
            interval=ROW_WAIT_INTERVAL,
        )

    def wait_for_user_project_spend(
        self, email: str, project_name: str, timeout: float = ROW_WAIT_TIMEOUT * 2
    ):
        """Poll until the admin row shows platform spend that survives 2-decimal rounding."""
        return poll_until(
            lambda: self.get_user_project_spending_row(email, project_name),
            lambda row: row is not None and row["platform"] >= VISIBLE_AT_TWO_DECIMALS,
            timeout=timeout,
            interval=ROW_WAIT_INTERVAL,
        )

    def get_user_project_spending_rows(self, email: str) -> list[dict]:
        return self.client.analytics.get_user_project_spending(email).data.rows

    def get_user_project_spending_row(self, email: str, project_name: str):
        return next(
            (
                row
                for row in self.get_user_project_spending_rows(email)
                if row["project_name"] == project_name
            ),
            None,
        )


def _member_customer_spend(lite_llm_budget_utils, customer_id: str) -> float:
    customer = lite_llm_budget_utils.get_customer_info(customer_id)
    return float(customer.get("spend", 0)) if customer else 0.0


def member_customer_spend(
    lite_llm_budget_utils, project_name: str, user_id: str, category: str = "platform"
) -> float:
    """Spend of the member's customer on the project category at the provider, read now."""
    return _member_customer_spend(
        lite_llm_budget_utils,
        MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
            project_name=project_name, category=category, user_id=user_id
        ),
    )


def generate_member_spend(
    proxy_utils,
    lite_llm_budget_utils,
    model: str,
    project_name: str,
    user_id: str,
    category: str = "platform",
    target_spend: float = MIN_VISIBLE_SPEND,
) -> float:
    """Spend on a project budget category as one of its members, in bounded batches of long requests.

    The requests carry the CLI client and project headers. The backend routes them to the
    project's cli key when the project has a cli budget and to its platform key otherwise, so
    ``category`` must name the key that receives them.

    Returns the member's LiteLLM customer spend once it stopped changing; it is below
    ``target_spend`` when the stand did not record that much within the bounded batches.
    """
    customer_id = MEMBER_OVERRIDE_CUSTOMER_ID_TEMPLATE.format(
        project_name=project_name, category=category, user_id=user_id
    )
    headers = {**CLI_CLIENT_HEADER, CLI_PROJECT_HEADER: project_name}
    spend = 0.0
    for _ in range(SPEND_MAX_BATCHES):
        for _ in range(SPEND_REQUESTS_PER_BATCH):
            proxy_utils.send_messages_request(
                model=model,
                messages=[{"role": "user", "content": budget_chat_prompt_bigger()}],
                max_tokens=SPEND_REQUEST_MAX_TOKENS,
                timeout=SPEND_REQUEST_TIMEOUT,
                extra_headers=headers,
            ).raise_for_status()
        spend = poll_until(
            lambda: _member_customer_spend(lite_llm_budget_utils, customer_id),
            lambda value: value >= target_spend,
            timeout=SPEND_POLL_TIMEOUT,
            interval=SPEND_POLL_INTERVAL,
        )
        if spend >= target_spend:
            break
    for _ in range(SPEND_SETTLE_CHECKS):
        time.sleep(SPEND_POLL_INTERVAL)
        current = _member_customer_spend(lite_llm_budget_utils, customer_id)
        if current == spend:
            break
        spend = current
    return spend


def generate_member_platform_spend(
    proxy_utils,
    lite_llm_budget_utils,
    model: str,
    project: MemberProject,
    target_spend: float = MIN_VISIBLE_SPEND,
) -> float:
    """Spend on the project's platform budget as its member; see ``generate_member_spend``."""
    return generate_member_spend(
        proxy_utils,
        lite_llm_budget_utils,
        model,
        project.name,
        project.member_id,
        target_spend=target_spend,
    )


def wait_for_settled_key_spend(
    lite_llm_budget_utils,
    alias: str,
    timeout: float = KEY_SPEND_SETTLE_TIMEOUT,
) -> float:
    """Spend of the project key once it is above zero and unchanged over several reads.

    This is the project total the personal page measures against the hard limit. Returns the
    last read when ``timeout`` elapses first, so a caller asserting on it fails with the value.
    """
    state = {"previous": None, "stable": 0}

    def read() -> float:
        current = lite_llm_budget_utils.get_key_spend_by_alias(alias)
        state["stable"] = state["stable"] + 1 if current == state["previous"] else 0
        state["previous"] = current
        return current

    return poll_until(
        read,
        lambda value: value > 0 and state["stable"] >= SPEND_STABLE_READS - 1,
        timeout=timeout,
        interval=SPEND_POLL_INTERVAL,
    )


def get_member_allocations(
    admin_project_budget_utils, budget_id: str
) -> dict[str, dict]:
    """The budget's member allocations by user id."""
    budget = admin_project_budget_utils.get_budget(budget_id)
    return {a["user_id"]: a for a in budget["member_allocations"]}


def wait_for_member_allocation(
    admin_project_budget_utils,
    budget_id: str,
    user_id: str,
    allocated_max_budget: float,
    timeout: float = ROW_WAIT_TIMEOUT,
) -> dict[str, dict]:
    """Poll until the member's allocated max budget equals ``allocated_max_budget``.

    Returns all allocations of the last read.
    """
    return poll_until(
        lambda: get_member_allocations(admin_project_budget_utils, budget_id),
        lambda allocations: user_id in allocations
        and allocations[user_id]["allocated_max_budget"] == allocated_max_budget,
        timeout=timeout,
        interval=ROW_WAIT_INTERVAL,
    )


def expected_total(numerator: float, limit: float) -> float:
    """The page's total: ``numerator`` as a percentage of ``limit``, 0.0 for no or a zero limit."""
    return round(numerator / limit * 100, 2) if limit and limit > 0 else 0.0


def expected_override_limit(
    override: float, own_spend: float, project_limit: float, project_total: float
) -> float:
    """Limit of a member with an override while enforcement is off.

    The override, capped by what the member already spent plus what is left of the project budget.
    """
    return min(override, own_spend + max(0.0, project_limit - project_total))


def wait_for_row_matching(
    usage: BudgetUsageUtils,
    row_name: str,
    measure,
    expected,
    timeout: float = STORED_ROW_WAIT_TIMEOUT,
):
    """Poll until the row shows the values expected from freshly measured provider spend.

    A row can lag the provider: the page serves the stored values until they are older than the
    backend staleness threshold, and the provider itself writes spend in batches. So both sides
    are read on every attempt, the row first and then ``measure()``, and the row has to match
    what was measured after it. ``expected(measured)`` returns ``(spend, limit, total)``; they
    are compared with the same tolerances the assertions use (``MONEY_TOLERANCE`` for spend and
    limit, ``PERCENT_TOLERANCE`` for total), none of them loosened.

    Returns ``(row, measured)`` of the last attempt. When ``timeout`` elapses first the last
    attempt is logged and returned unmatched, so the caller's assertions fail with the observed
    row and the measured values.
    """

    def attempt():
        return usage.get_row(row_name), measure()

    def matches(result) -> bool:
        row, measured = result
        if row is None:
            return False
        spend, limit, total = expected(measured)
        return (
            abs(row["current_spending"] - round(spend, 2)) <= MONEY_TOLERANCE
            and row["budget_limit"] is not None
            and abs(row["budget_limit"] - round(limit, 2)) <= MONEY_TOLERANCE
            and abs(row["total"] - total) <= PERCENT_TOLERANCE
        )

    started = time.monotonic()
    result = poll_until(
        attempt, matches, timeout=timeout, interval=STORED_ROW_POLL_INTERVAL
    )
    elapsed = time.monotonic() - started
    if matches(result):
        logger.info(
            "Row %r matched the measured spend after %.1fs (row=%s measured=%s)",
            row_name,
            elapsed,
            result[0],
            result[1],
        )
    else:
        logger.warning(
            "Row %r never matched the measured spend within %ss: row=%s measured=%s expected=%s",
            row_name,
            timeout,
            result[0],
            result[1],
            expected(result[1]),
        )
    return result
