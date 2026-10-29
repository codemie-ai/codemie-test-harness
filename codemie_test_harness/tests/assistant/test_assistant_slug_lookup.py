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

"""Assistant slug lookup across projects.

Assistant slugs are unique only per project, so the same slug can exist in several
projects. ``GET /v1/assistants/slug/{slug}`` without ``project`` used to return a
normal 200 with one arbitrary match (it could flip between projects). The contract
pinned here:

* no ``project`` + ambiguous slug         -> 422 "Ambiguous slug" with the match count
  and a pointer to the ``project`` query parameter
* ``project=<name>``                      -> 200 with that project's assistant
* ``project`` that does not hold the slug -> 404 (no fallback to another project)

Coverage: steps 1-3, AC1, AC2, AC4
Excluded: AC3 (un-automatable: static-display — documentation-only criterion; its only observable is static OpenAPI description text, and an assertion on it was dropped as brittle (stays green with the fix unshipped))
  Case steps: 1 = create/identify the same slug in several projects, 2 = call the slug
  endpoint without ``project`` repeatedly, 3 = observe which project's assistant comes
  back. AC1 = ambiguity signal or stable disambiguation, AC2 = total matches or requires
  ``project``, AC3 = documentation emphasizes project-scoped uniqueness (excluded above),
  AC4 = regression test covering duplicate slugs across projects (this module).
"""

import logging
from types import SimpleNamespace

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_entries,
    is_not,
)

from codemie_test_harness.tests.utils.base_utils import (
    assert_error_details,
    get_random_name,
)

logger = logging.getLogger(__name__)

UNPROCESSABLE_ENTITY = 422
NOT_FOUND = 404
OK = 200


@pytest.fixture
def duplicate_slug_assistants(request, project_utils, assistant_utils):
    """Same assistant slug in two freshly created projects (case step 1).

    Both projects are registered for teardown BEFORE the create request is sent, and
    the teardown cascades by project name (server-side listing), so an assistant whose
    create call errored after committing is still removed with its project.
    """
    slug = get_random_name()
    project_names = []

    def _teardown():
        for name in reversed(project_names):
            try:
                project_utils.delete_project_cascade(name)
            except Exception as e:  # noqa: BLE001 - keep the test's own failure intact
                logger.warning(f"Failed to delete project {name}: {e}")

    request.addfinalizer(_teardown)

    assistants = {}
    for key in ("a", "b"):
        project_name = get_random_name()
        project_names.append(project_name)
        project_utils.create_project(project_name)
        assistants[key] = assistant_utils.create_assistant(
            assistant_name=get_random_name(), slug=slug, project_name=project_name
        )

    return SimpleNamespace(
        slug=slug,
        project_a=project_names[0],
        project_b=project_names[1],
        assistant_a=assistants["a"],
        assistant_b=assistants["b"],
    )


@pytest.mark.assistant
@pytest.mark.api
def test_slug_lookup_without_project_reports_ambiguity(
    assistant_utils, duplicate_slug_assistants
):
    """Steps 2-3, AC1, AC2: ambiguous slug without ``project`` is rejected.

    The same slug exists in two projects. A lookup without ``project`` must return the
    explicit ambiguity error (never a 200 with one arbitrary project's assistant), and
    the error must report the number of matches and tell the caller to pass ``project``.
    """
    slug = duplicate_slug_assistants.slug

    response = assistant_utils.get_assistant_by_slug_response(slug)
    assert_error_details(response, UNPROCESSABLE_ENTITY, "2 assistants")

    error = response.json()["error"]
    assert_that(error["message"], equal_to("Ambiguous slug"))
    assert_that(error["details"], contains_string(slug))
    assert_that(error["details"], contains_string("project"))
    assert_that(error["help"], contains_string("?project="))


@pytest.mark.assistant
@pytest.mark.api
def test_slug_lookup_with_project_is_deterministic(
    assistant_utils, duplicate_slug_assistants
):
    """Step 3, AC1: ``project`` resolves the duplicate slug deterministically.

    Each project's lookup returns that project's own assistant (id and project match),
    and the two projects resolve to different assistants. A project that does not hold
    the slug yields 404 (no fallback to another project's assistant that happens to
    share the slug).
    """
    data = duplicate_slug_assistants
    expected = {
        data.project_a: data.assistant_a.id,
        data.project_b: data.assistant_b.id,
    }
    assert_that(data.assistant_a.id, is_not(equal_to(data.assistant_b.id)))

    for project, assistant_id in expected.items():
        response = assistant_utils.get_assistant_by_slug_response(
            data.slug, project=project
        )
        assert_that(
            response.status_code,
            equal_to(OK),
            f"slug '{data.slug}' in project '{project}': {response.text[:300]}",
        )
        assert_that(
            response.json(),
            has_entries(id=assistant_id, slug=data.slug, project=project),
        )

    unrelated_project = get_random_name()
    response = assistant_utils.get_assistant_by_slug_response(
        data.slug, project=unrelated_project
    )
    assert_error_details(response, NOT_FOUND, unrelated_project)
