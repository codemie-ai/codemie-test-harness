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

"""Tests for project search behavior when a project has no description.

Covers:
  AC-8 — a project with no description is still found by a search term matching its
         name or display_name.
  AC-9 — a project with no description is excluded from a non-matching search, and no
         error occurs.

The COALESCE + ilike search path (application_repository.py:63) predates this MR; what is
newly-reachable here is a null-description project actually reaching it — this ticket made
a description-less project a routine, not theoretical, case for that shared search endpoint.
"""

import pytest
from hamcrest import assert_that, is_in, is_not, none

from codemie_test_harness.tests.utils.base_utils import get_random_name


@pytest.mark.project
@pytest.mark.api
@pytest.mark.parametrize(
    "term_matches",
    [True, False],
    ids=[
        "matching_term_still_returns_the_project",
        "non_matching_term_excludes_it_with_no_error",
    ],
)
def test_search_on_project_with_no_description(project_utils, project, term_matches):
    """TC_008 / TC_009 — a project created with an empty
    description (normalizes server-side to None, project_service.py:389) is still returned
    by a search term matching its name (TC-008), and is excluded — with no error raised — by
    a search term matching nothing on it (TC-009).
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
        "searchability is exercised",
    )

    search_term = name[:8] if term_matches else get_random_name()

    # Independent-channel check: the search call is a separate HTTP round trip from both
    # the create call and the get_project_detail call above.
    response = project_utils.list_projects(search=search_term)
    result_names = [p.name for p in response.data]

    if term_matches:
        assert_that(
            name,
            is_in(result_names),
            "A project with no description must still be returned by a search term "
            "matching its name",
        )
    else:
        # The list_projects call above completing normally (no HTTPError/exception from
        # the COALESCE+ilike path over a NULL description column) is itself part of this
        # Then — a defect that raised on a NULL description would surface as an exception
        # on that call, not merely as a wrong-but-successful result.
        assert_that(
            name,
            is_not(is_in(result_names)),
            "A project with no description must be excluded from a search term matching "
            "nothing on it",
        )
