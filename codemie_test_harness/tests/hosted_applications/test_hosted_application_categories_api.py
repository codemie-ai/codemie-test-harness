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

"""Hosted applications API: categories on an application, required at publication, used as a
catalog filter, and protecting a category from deletion while a live application carries it.

The categories are created by the test (an administrator's client does it) and deleted after it,
once the applications that carry them are gone.
"""

import logging

import pytest
from codemie_sdk.models.hosted_application import HostedApplicationCategory
from hamcrest import (
    assert_that,
    contains_exactly,
    contains_inanyorder,
    contains_string,
    empty,
    equal_to,
    has_item,
    is_,
    is_not,
)
from requests import HTTPError

from codemie_test_harness.tests.test_data.hosted_application_test_data import (
    CATEGORY_IN_USE,
    CONFLICT,
    IDEMPOTENCY_CONFLICT_CODE,
    INVALID_CATEGORIES_CODE,
    INVALID_FILTER_CODE,
    PUBLISH_REFUSALS,
    PUBLISHED_NEEDS_CATEGORY,
    UNPROCESSABLE,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.hosted_application_utils import (
    error_code,
    error_field_messages,
    error_message,
    error_status,
)

CAPABILITY = "features:hostedApplications"

logger = logging.getLogger(__name__)


@pytest.fixture
def hosted_category_factory(categories_utils):
    """Factory: create platform categories; each is deleted after the test.

    Request it before the user fixtures: the applications that carry a category must be
    deleted first, and fixtures set up later are torn down earlier.
    """
    created: list[str] = []

    def create():
        category = categories_utils.create_category()
        created.append(category.id)
        return category

    yield create
    for category_id in created:
        try:
            categories_utils.delete_category(category_id)
        except Exception as error:
            logger.warning(f"Failed to delete category {category_id}: {error}")


@pytest.fixture
def category_owner(hosted_category_factory, hosted_user_factory):
    """A plain user who owns the applications of the test; the categories outlive their applications."""
    return hosted_user_factory()


@pytest.fixture
def categories(hosted_category_factory):
    """Three categories created for the test."""
    return [hosted_category_factory() for _ in range(3)]


def as_reply(category) -> HostedApplicationCategory:
    """A category the way an application lists it."""
    return HostedApplicationCategory(id=category.id, name=category.name)


def category_ids(app) -> list[str]:
    """The ids of the categories an application lists, in order."""
    return [category.id for category in app.categories]


def refusal_text(error: HTTPError) -> str:
    """Everything the platform says about a refused request."""
    return " | ".join([error_message(error), *error_field_messages(error)])


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_created_application_lists_its_categories_by_id_and_name(
    category_owner, categories
):
    # @case hosted-applications-categories_TC_001
    chosen = categories[:2]

    app = category_owner.apps.create_app(
        category_owner.personal_project, categories=[category.id for category in chosen]
    )

    assert_that(
        app.categories,
        contains_exactly(*[as_reply(category) for category in chosen]),
        "the reply lists the chosen categories with their names, in the order sent",
    )
    assert_that(
        category_owner.apps.get_app(app.id).categories,
        equal_to(app.categories),
        "reading the application again gives the same categories",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_application_created_without_categories_lists_none(category_owner):
    # @case hosted-applications-categories_TC_002
    app = category_owner.apps.create_app(category_owner.personal_project)

    assert_that(
        category_owner.apps.get_app(app.id).categories,
        is_(empty()),
        "an application is not obliged to have a category",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_creating_an_application_with_an_unknown_category_is_refused(category_owner):
    # @case hosted-applications-categories_TC_003
    with pytest.raises(HTTPError) as refused:
        category_owner.apps.create_app(
            category_owner.personal_project, categories=["autotest-no-such-category"]
        )

    assert_that(error_status(refused.value), equal_to(UNPROCESSABLE), "refused")
    assert_that(
        error_code(refused.value),
        equal_to(INVALID_CATEGORIES_CODE),
        "the platform names the problem",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_patch_replaces_the_categories_of_an_application(category_owner, categories):
    # @case hosted-applications-categories_TC_004
    first, second, third = categories
    app = category_owner.apps.create_app(
        category_owner.personal_project, categories=[first.id]
    )

    patched = category_owner.apps.patch_app(app.id, categories=[second.id, third.id])

    assert_that(
        patched.categories,
        contains_exactly(as_reply(second), as_reply(third)),
        "the new list replaces the old one",
    )

    cleared = category_owner.apps.patch_app(app.id, categories=[])

    assert_that(
        cleared.categories,
        is_(empty()),
        "a private application may have no category",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize(
    "refusal", PUBLISH_REFUSALS, ids=[item.id for item in PUBLISH_REFUSALS]
)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_publish_with_missing_or_invalid_categories_is_refused(category_owner, refusal):
    # @case hosted-applications-categories_TC_005
    app = category_owner.apps.create_app(category_owner.personal_project)

    with pytest.raises(HTTPError) as refused:
        category_owner.apps.publish_as_given(app.id, refusal.categories)

    assert_that(error_status(refused.value), equal_to(UNPROCESSABLE), "refused")
    assert_that(error_code(refused.value), equal_to(refusal.code), "the error code")
    assert_that(
        refusal_text(refused.value),
        contains_string(refusal.message_part),
        "the platform says what is wrong",
    )
    assert_that(
        category_owner.apps.get_app(app.id).is_global,
        is_(False),
        "the application stays out of the marketplace",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_publish_sets_exactly_the_categories_sent(category_owner, categories):
    # @case hosted-applications-categories_TC_006
    first, second, third = categories
    app = category_owner.apps.create_app(
        category_owner.personal_project, categories=[first.id]
    )

    published = category_owner.apps.publish(app.id, [second.id, third.id])

    assert_that(
        published.categories,
        contains_exactly(as_reply(second), as_reply(third)),
        "publishing replaces the categories with the ones sent",
    )
    stored = category_owner.apps.get_app(app.id)
    assert_that(stored.is_global, is_(True), "the application is in the marketplace")
    assert_that(
        stored.categories,
        equal_to(published.categories),
        "and keeps those categories",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_publish_retried_with_the_same_key_and_other_categories_conflicts(
    category_owner, categories
):
    # @case hosted-applications-categories_TC_007
    first, second, _ = categories
    app = category_owner.apps.create_app(category_owner.personal_project)
    key = get_random_name()
    category_owner.apps.publish(app.id, [first.id], idempotency_key=key)

    with pytest.raises(HTTPError) as conflict:
        category_owner.apps.publish(app.id, [second.id], idempotency_key=key)

    assert_that(error_status(conflict.value), equal_to(CONFLICT), "refused")
    assert_that(
        error_code(conflict.value),
        equal_to(IDEMPOTENCY_CONFLICT_CODE),
        "the key was used for a different change",
    )
    assert_that(
        category_ids(category_owner.apps.get_app(app.id)),
        contains_exactly(first.id),
        "the first publication stands",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_patch_cannot_leave_a_published_application_without_a_category(
    category_owner, categories
):
    # @case hosted-applications-categories_TC_008
    app = category_owner.apps.create_app(category_owner.personal_project)
    category_owner.apps.publish(app.id, [categories[0].id])

    with pytest.raises(HTTPError) as refused:
        category_owner.apps.patch_app(app.id, categories=[])

    assert_that(error_status(refused.value), equal_to(UNPROCESSABLE), "refused")
    assert_that(
        error_code(refused.value),
        equal_to(INVALID_CATEGORIES_CODE),
        "the platform names the problem",
    )
    assert_that(
        refusal_text(refused.value),
        contains_string(PUBLISHED_NEEDS_CATEGORY),
        "the platform says why",
    )
    assert_that(
        category_ids(category_owner.apps.get_app(app.id)),
        contains_exactly(categories[0].id),
        "the category stays",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_unpublish_keeps_the_categories(category_owner, categories):
    # @case hosted-applications-categories_TC_009
    chosen = [categories[0].id, categories[1].id]
    app = category_owner.apps.create_app(category_owner.personal_project)
    category_owner.apps.publish(app.id, chosen)

    category_owner.apps.unpublish(app.id)

    stored = category_owner.apps.get_app(app.id)
    assert_that(stored.is_global, is_(False), "the application left the marketplace")
    assert_that(
        category_ids(stored),
        contains_exactly(*chosen),
        "the categories are the same as when it was published",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_catalog_category_filter_lists_only_matching_applications(
    category_owner, categories
):
    # @case hosted-applications-categories_TC_010
    first, second, _ = categories
    prefix = get_random_name()
    project = category_owner.personal_project
    in_first = category_owner.apps.create_app(
        project, categories=[first.id], name=f"{prefix}-first"
    )
    in_second = category_owner.apps.create_app(
        project, categories=[second.id], name=f"{prefix}-second"
    )
    in_both = category_owner.apps.create_app(
        project, categories=[first.id, second.id], name=f"{prefix}-both"
    )
    uncategorized = category_owner.apps.create_app(project, name=f"{prefix}-none")

    assert_that(
        category_owner.apps.all_app_ids("mine", q=prefix),
        contains_inanyorder(in_first.id, in_second.id, in_both.id, uncategorized.id),
        "without the filter every application is listed",
    )
    assert_that(
        category_owner.apps.all_app_ids("mine", q=prefix, category=[first.id]),
        contains_inanyorder(in_first.id, in_both.id),
        "one category lists the applications that carry it",
    )
    assert_that(
        category_owner.apps.all_app_ids(
            "mine", q=prefix, category=[first.id, second.id]
        ),
        contains_inanyorder(in_first.id, in_second.id, in_both.id),
        "several categories list the applications that carry any of them",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_marketplace_category_filter_lists_only_published_applications_in_it(
    category_owner, hosted_user_factory, categories
):
    # @case hosted-applications-categories_TC_011
    first, second, _ = categories
    reader = hosted_user_factory()
    prefix = get_random_name()
    project = category_owner.personal_project
    in_first = category_owner.apps.create_app(project, name=f"{prefix}-first")
    in_second = category_owner.apps.create_app(project, name=f"{prefix}-second")
    category_owner.apps.publish(in_first.id, [first.id])
    category_owner.apps.publish(in_second.id, [second.id])

    assert_that(
        reader.apps.all_app_ids("marketplace", q=prefix, category=[first.id]),
        contains_exactly(in_first.id),
        "another user finds only the application published in that category",
    )
    assert_that(
        reader.apps.all_app_ids("marketplace", q=prefix, category=[second.id]),
        contains_exactly(in_second.id),
        "and the other application under the other category",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_catalog_filter_by_an_unknown_category_is_refused(category_owner):
    # @case hosted-applications-categories_TC_012
    with pytest.raises(HTTPError) as refused:
        category_owner.apps.all_app_ids("mine", category=["autotest-no-such-category"])

    assert_that(error_status(refused.value), equal_to(UNPROCESSABLE), "refused")
    assert_that(
        error_code(refused.value),
        equal_to(INVALID_FILTER_CODE),
        "the filter is invalid",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_category_deletion_is_refused_while_a_hosted_application_carries_it(
    category_owner, hosted_category_factory, categories_utils
):
    # @case hosted-applications-categories_TC_013
    category = hosted_category_factory()
    app = category_owner.apps.create_app(
        category_owner.personal_project, categories=[category.id]
    )

    with pytest.raises(HTTPError) as refused:
        categories_utils.delete_category(category.id)

    assert_that(error_status(refused.value), equal_to(CONFLICT), "refused")
    assert_that(
        refused.value.response.text,
        contains_string(CATEGORY_IN_USE),
        "the platform says the category is in use",
    )
    assert_that(
        category_ids(category_owner.apps.get_app(app.id)),
        contains_exactly(category.id),
        "the application keeps its category",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_category_can_be_deleted_once_its_hosted_application_is_deleted(
    category_owner, hosted_category_factory, categories_utils
):
    # @case hosted-applications-categories_TC_014
    category = hosted_category_factory()
    app = category_owner.apps.create_app(
        category_owner.personal_project, categories=[category.id]
    )
    category_owner.apps.delete_app(app.id)

    categories_utils.delete_category(category.id)

    assert_that(
        [item.id for item in categories_utils.get_categories()],
        is_not(has_item(category.id)),
        "the category is gone",
    )
