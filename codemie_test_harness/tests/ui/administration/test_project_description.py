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

"""UI tests for the optional project description feature.

Covers:
  AC-1 — Create Project dialog: Description is not marked as required and no validation
         message appears while it is empty; submit is not blocked.
  AC-4 — a project with no description shows the "No description" placeholder on
         the details page.

All tests follow the E2E pattern:
  - API used for setup/teardown where a test needs a project as a precondition
  - Browser used to assert UI behaviour only
"""

from __future__ import annotations

import logging

import pytest
from hamcrest import assert_that, none

from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_management_page import (
    ProjectManagementPage,
)
from codemie_test_harness.tests.ui.pageobject.administration.project_modal_page import (
    ProjectModal,
)

logger = logging.getLogger(__name__)

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def created_project_names(project_utils):
    """Tracks project names created directly through the browser (Create Project dialog)
    and cleans them up via the API on teardown.

    Used instead of the ``project`` factory fixture when a test's precondition is that no
    project exists yet — the project is created by the test's own UI action, not by an
    API-side factory call.
    """
    names = []
    yield names
    for name in names:
        try:
            project_utils.delete_project_cascade(name)
        except Exception as e:
            logger.error(f"Failed to delete project {name}: {e}")


# ── AC-1: Create modal — Description is optional, no validation error, submit not blocked ──


@pytest.mark.project
@pytest.mark.ui
def test_create_project_modal_accepts_empty_description(
    page, project_utils, created_project_names
):
    """Leaving Description empty on Create shows no
    required-asterisk and no inline validation error, and does not block submit; an
    independent reload of the Project Management page shows the new project.
    """
    name = get_random_name()
    created_project_names.append(name)

    mgmt_page = ProjectManagementPage(page)
    modal = ProjectModal(page)

    mgmt_page.navigate_to()
    mgmt_page.click_create_project()
    modal.should_be_visible()

    # Description is not marked as required (no asterisk next to its label).
    modal.should_not_show_description_required_indicator()

    modal.fill_technical_name(name)
    # Description is deliberately left untouched — no fill_description call at all.

    # Immediately after leaving Description empty and before clicking Save, no validation
    # error is rendered for it.
    modal.should_not_show_description_validation_error()

    modal.click_save()

    # After Save, no validation error appeared for Description (the regression this case
    # hypothesizes would keep this node rendered and the modal open).
    modal.should_not_show_description_validation_error()

    # Independent-channel check: reload the Project Management page (a separate page
    # load/list-fetch from the Save click's own response) and confirm the project exists.
    mgmt_page.navigate_to()
    mgmt_page.should_see_project_technical_name_only(project_name=name)

    # Setup/teardown-independent confirmation via the API that the project was truly
    # created with no description, not merely visible in a stale client-side list.
    detail = project_utils.get_project_detail(name)
    assert_that(
        detail.description,
        none(),
        "A project created with Description left empty must have no description",
    )


# ── AC-4: Details page — "No description" placeholder for a null description ───────────


@pytest.mark.project
@pytest.mark.ui
def test_project_details_page_shows_no_description_placeholder(
    page, project_utils, project
):
    """A project created with an empty description (normalizes
    server-side to None) renders the "No description" placeholder on the details page,
    rather than an error or a blank gap.
    """
    name = get_random_name()
    created = project(name=name, description="")

    # Setup precondition, verified via an independent get_project_detail read (a separate
    # HTTP round trip from the create call): the description genuinely normalized to None.
    detail = project_utils.get_project_detail(created.name)
    assert_that(
        detail.description,
        none(),
        "Setup precondition: the project must have no description before its "
        "rendering is exercised",
    )

    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(created.name)
    details_page.should_be_on_project_details_page(created.name)

    # Independent-channel check: a browser-rendered DOM read, independent of the API call
    # used above to confirm the data.
    details_page.should_show_no_description_placeholder()
