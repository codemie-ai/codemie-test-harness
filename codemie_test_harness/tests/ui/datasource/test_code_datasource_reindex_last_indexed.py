"""
UI tests for the "Last indexed" value after a manual Full Reindex of a code
datasource.

Per the confirmed AC-2 resolution, "Last indexed" is the reindex trigger time,
not the completion time.
"""

from datetime import datetime

import pytest
from codemie_sdk.models.datasource import DataSourceStatus as ApiDataSourceStatus
from hamcrest import assert_that, equal_to, greater_than_or_equal_to

from codemie_test_harness.tests.ui.pageobject.datasources.datasource_page import (
    DataSourcePage,
)
from codemie_test_harness.tests.ui.pageobject.datasources.view_datasource_page import (
    ViewDatasourcePage,
)
from codemie_test_harness.tests.ui.test_data.datasource_test_data import (
    DataSourceStatus,
)

REINDEX_TIMEOUT_SECONDS = 180


def _open_details(datasource_page, datasource_name):
    """Open the datasource details from the list, once the row shows Completed."""
    datasource_page.navigate_to()
    datasource_page.should_see_table_row_with_values(
        name=datasource_name, status=DataSourceStatus.COMPLETED
    )
    datasource_page.click_datasource_row_by_name(datasource_name)


@pytest.mark.datasource
@pytest.mark.ui
def test_code_datasource_full_reindex_updates_last_indexed_to_trigger_time(
    page, datasource_utils, code_datasource
):
    """Full Reindex sets Last indexed to the trigger time and the value survives completion and reopening.

    Uses the shared, session-scoped `code_datasource` fixture (review comment on
    MR !798) instead of a dedicated one. Reindexing it is the same non-destructive
    convention already used by test_assistant_with_git_tools.py and friends, so
    `last_indexed_before` is read defensively: the fixture may already carry a
    value from an earlier test in this session.
    """
    datasource_page = DataSourcePage(page)
    view_page = ViewDatasourcePage(page)
    datasource_name = code_datasource.name
    update_date_before = code_datasource.update_date

    # Precondition: capture whatever "Last indexed" shows before this test's own
    # trigger. None when the shared fixture has not been reindexed yet this session.
    _open_details(datasource_page, datasource_name)
    last_indexed_before = view_page.try_get_last_indexed()

    # Step 1: start Full Reindex from the row action menu
    datasource_page.navigate_to()
    datasource_page.should_see_table_row_with_values(
        name=datasource_name, status=DataSourceStatus.COMPLETED
    )
    trigger_started = datetime.now()
    datasource_page.open_row_action_menu(datasource_name)
    datasource_page.should_see_full_reindex_menu_item()
    datasource_page.click_full_reindex()
    trigger_finished = datetime.now()

    # Step 2: wait until the reindex is processed and the datasource is Completed again
    datasource_utils.wait_for_update_date_change(
        code_datasource.id,
        timeout=REINDEX_TIMEOUT_SECONDS,
        initial_update_date=update_date_before,
    )
    completed = datasource_utils.wait_for_indexing(
        code_datasource.id, timeout=REINDEX_TIMEOUT_SECONDS
    )
    assert_that(
        completed.status,
        equal_to(ApiDataSourceStatus.COMPLETED),
        "Code datasource must return to COMPLETED after Full Reindex",
    )

    # Step 3: Last indexed now appears and equals this trigger's time
    _open_details(datasource_page, datasource_name)
    view_page.should_see_last_indexed()
    view_page.should_see_last_indexed_between(trigger_started, trigger_finished)
    last_indexed_after = view_page.get_last_indexed()
    if last_indexed_before is not None:
        assert_that(
            last_indexed_after,
            greater_than_or_equal_to(last_indexed_before),
            "Last indexed must not go backwards after a later reindex",
        )

    # Step 4: refresh and reopen the details; the value is not reverted
    page.reload()
    _open_details(datasource_page, datasource_name)
    view_page.should_see_last_indexed_equal_to(last_indexed_after)
