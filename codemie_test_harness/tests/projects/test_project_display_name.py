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

"""Tests for project display_name feature.

Covers:
  AC-1 — create + persist, max 150 chars, unicode
  AC-2 — update display_name, validation
  AC-3 — API/SDK models expose display_name
  AC-5 — fallback: projects without display_name have display_name=None
  AC-6 — existing projects unaffected; field is optional
"""

import pytest
from hamcrest import (
    assert_that,
    any_of,
    equal_to,
    greater_than,
    instance_of,
    none,
    not_none,
)
from pydantic import ValidationError

from codemie_test_harness.tests.test_data.projects_test_data import (
    DISPLAY_NAME_MAX,
    DISPLAY_NAME_TOO_LONG,
    DISPLAY_NAME_UNICODE,
    get_project_create_data,
    get_project_create_data_with_display_name,
    get_project_update_data_with_display_name,
)


# ── AC-1: Create + persist ────────────────────────────────────────────────────


@pytest.mark.smoke
@pytest.mark.project
@pytest.mark.api
def test_create_project_with_display_name_returns_value(project_utils, project):
    """TC-001: Create project with display_name — response contains the submitted value."""
    data = get_project_create_data_with_display_name()
    response = project(
        name=data["name"],
        description=data["description"],
        display_name=data["display_name"],
    )

    assert_that(
        response.display_name,
        equal_to(data["display_name"]),
        "Create response must echo back the submitted display_name",
    )


@pytest.mark.project
@pytest.mark.api
def test_create_project_display_name_persists_to_detail(project_utils, project):
    """TC-002: Create project with display_name, then get_project_detail — value persists."""
    data = get_project_create_data_with_display_name()
    created = project(
        name=data["name"],
        description=data["description"],
        display_name=data["display_name"],
    )

    detail = project_utils.get_project_detail(created.name)

    assert_that(
        detail.display_name,
        equal_to(data["display_name"]),
        "display_name must be persisted and retrievable via get_project_detail",
    )


@pytest.mark.project
@pytest.mark.api
def test_create_project_display_name_exactly_150_chars(project_utils, project):
    """TC-003: Create project with display_name of exactly 150 chars (boundary) — succeeds."""
    data = get_project_create_data()
    response = project(
        name=data["name"],
        description=data["description"],
        display_name=DISPLAY_NAME_MAX,
    )

    assert_that(
        response.display_name,
        equal_to(DISPLAY_NAME_MAX),
        "Exactly-150-char display_name must be accepted",
    )


@pytest.mark.project
@pytest.mark.api
def test_create_project_display_name_unicode(project_utils, project):
    """TC-004: Create project with unicode display_name (Cyrillic + emoji + CJK) — persists."""
    data = get_project_create_data()
    response = project(
        name=data["name"],
        description=data["description"],
        display_name=DISPLAY_NAME_UNICODE,
    )

    assert_that(
        response.display_name,
        equal_to(DISPLAY_NAME_UNICODE),
        "Unicode display_name must be accepted and persisted without modification",
    )


@pytest.mark.project
@pytest.mark.api
def test_create_project_display_name_too_long_rejected(project_utils):
    """TC-005: Create project with display_name of 151 chars — rejected by SDK (ValidationError).

    Design note: The SDK's Pydantic model enforces max_length=150 client-side, raising
    pydantic.ValidationError before any HTTP call is made. This is intentional SDK behaviour:
    the client prevents an invalid payload from reaching the server. If server-side HTTP 422
    enforcement needs separate verification, a raw-HTTP companion test would be required.
    """
    data = get_project_create_data()

    with pytest.raises(ValidationError):
        project_utils.create_project(
            name=data["name"],
            description=data["description"],
            display_name=DISPLAY_NAME_TOO_LONG,
        )


# ── AC-2: Update display_name ────────────────────────────────────────────────


@pytest.mark.smoke
@pytest.mark.project
@pytest.mark.api
def test_update_project_display_name_returns_new_value(project_utils, project):
    """TC-006: Update display_name on an existing project — response contains the new value."""
    created = project()
    update_data = get_project_update_data_with_display_name()

    response = project_utils.update_project(
        project_name=created.name,
        description=update_data["description"],
        display_name=update_data["display_name"],
    )

    assert_that(
        response.display_name,
        equal_to(update_data["display_name"]),
        "Update response must reflect the new display_name",
    )


@pytest.mark.project
@pytest.mark.api
def test_update_project_display_name_to_empty_clears_field(project_utils, project):
    """TC-007: Update display_name to empty string — field becomes falsy in the response."""
    data = get_project_create_data_with_display_name()
    created = project(
        name=data["name"],
        description=data["description"],
        display_name=data["display_name"],
    )

    response = project_utils.update_project(
        project_name=created.name,
        display_name="",
    )

    # Server may return None or "" when the field is cleared; both are accepted.
    assert_that(
        response.display_name,
        any_of(none(), equal_to("")),
        "After updating display_name to empty string the field must be None or empty",
    )


@pytest.mark.project
@pytest.mark.api
def test_update_project_display_name_exactly_150_chars(project_utils, project):
    """TC-008: Update display_name to exactly 150 chars (boundary) — succeeds."""
    created = project()

    response = project_utils.update_project(
        project_name=created.name,
        display_name=DISPLAY_NAME_MAX,
    )

    assert_that(
        response.display_name,
        equal_to(DISPLAY_NAME_MAX),
        "Exactly-150-char display_name update must succeed",
    )


@pytest.mark.project
@pytest.mark.api
def test_update_project_display_name_too_long_rejected(project_utils, project):
    """TC-009: Update display_name to 151 chars — rejected by SDK (ValidationError).

    Design note: Same SDK-level Pydantic validation as TC-005. The SDK's update model
    enforces max_length=150 client-side before any HTTP call is made. This is intentional
    SDK behaviour. If server-side HTTP 422 enforcement needs separate verification, a
    raw-HTTP companion test would be required.
    """
    created = project()

    with pytest.raises(ValidationError):
        project_utils.update_project(
            project_name=created.name,
            display_name=DISPLAY_NAME_TOO_LONG,
        )


# ── AC-3: API/SDK models expose display_name ────────────────────────────────


@pytest.mark.smoke
@pytest.mark.project
@pytest.mark.api
def test_list_projects_items_expose_display_name_attribute(project_utils):
    """TC-010: list_projects — each ProjectListItem exposes a display_name attribute."""
    response = project_utils.list_projects(per_page=10)

    assert_that(response.data, instance_of(list))
    assert_that(
        len(response.data),
        greater_than(0),
        "list_projects returned 0 items — display_name attribute cannot be verified",
    )
    for item in response.data:
        # Attribute must exist; value may be None for projects without display_name
        assert_that(
            hasattr(item, "display_name"),
            equal_to(True),
            f"ProjectListItem '{item.name}' is missing the display_name attribute",
        )


@pytest.mark.project
@pytest.mark.api
def test_get_project_detail_exposes_display_name_field(project_utils, project):
    """TC-011: get_project_detail — ProjectDetailResponse contains display_name field."""
    data = get_project_create_data_with_display_name()
    created = project(
        name=data["name"],
        description=data["description"],
        display_name=data["display_name"],
    )

    detail = project_utils.get_project_detail(created.name)

    assert_that(
        detail.display_name,
        not_none(),
        "get_project_detail must return display_name field",
    )


@pytest.mark.project
@pytest.mark.api
def test_create_project_response_contains_display_name_field(project_utils, project):
    """TC-012: Create-project response (ProjectCreateResponse) contains display_name field."""
    data = get_project_create_data_with_display_name()
    response = project(
        name=data["name"],
        description=data["description"],
        display_name=data["display_name"],
    )

    assert_that(
        hasattr(response, "display_name"),
        equal_to(True),
        "ProjectCreateResponse must expose the display_name attribute",
    )
    assert_that(
        response.display_name,
        equal_to(data["display_name"]),
    )


@pytest.mark.project
@pytest.mark.api
def test_update_project_response_contains_display_name_field(project_utils, project):
    """TC-013: Update-project response (ProjectUpdateResponse) contains display_name field."""
    data = get_project_create_data_with_display_name()
    created = project(
        name=data["name"],
        description=data["description"],
        display_name=data["display_name"],
    )
    new_display = f"Updated {data['display_name'][:30]}"

    response = project_utils.update_project(
        project_name=created.name,
        display_name=new_display,
    )

    assert_that(
        hasattr(response, "display_name"),
        equal_to(True),
        "ProjectUpdateResponse must expose the display_name attribute",
    )
    assert_that(response.display_name, equal_to(new_display))


# ── AC-5: Fallback — projects without display_name ──────────────────────────


@pytest.mark.project
@pytest.mark.api
def test_create_project_without_display_name_returns_none(project_utils, project):
    """TC-014: Create project without display_name — display_name is None in create response."""
    response = project()

    assert_that(
        response.display_name,
        none(),
        "Projects created without display_name must have display_name=None in response",
    )


@pytest.mark.project
@pytest.mark.api
def test_get_project_detail_without_display_name_returns_none(project_utils, project):
    """TC-015: get_project_detail for a project created without display_name — field is None."""
    created = project()
    detail = project_utils.get_project_detail(created.name)

    assert_that(
        detail.display_name,
        none(),
        "Projects created without display_name must have display_name=None in detail response",
    )


# ── AC-6: Existing projects unaffected; field is optional ────────────────────


@pytest.mark.project
@pytest.mark.api
def test_list_projects_without_display_name_pagination_unaffected(
    project_utils, project
):
    """TC-016: list_projects for projects without display_name — pagination and data unaffected."""
    created = project()

    response = project_utils.list_projects(search=created.name[:5], per_page=10)

    assert_that(response.data, instance_of(list))
    assert_that(
        response.pagination.total,
        instance_of(int),
        "Pagination total must be an integer",
    )


@pytest.mark.smoke
@pytest.mark.project
@pytest.mark.api
def test_create_project_omitting_display_name_succeeds(project_utils, project):
    """TC-017: Create project omitting display_name entirely — creation succeeds (field is optional)."""
    response = project()

    assert_that(
        response.name,
        not_none(),
        "Project created without display_name must have a name",
    )
    assert_that(response.display_name, none())
