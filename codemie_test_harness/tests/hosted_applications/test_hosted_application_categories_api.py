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

"""Hosted applications API: the categories of an application, on create, edit, publish and
unpublish, the category filter of the catalog, and the guard on deleting a category."""

from uuid import uuid4

import pytest
from hamcrest import (
    assert_that,
    contains_exactly,
    contains_inanyorder,
    contains_string,
    empty,
    equal_to,
    has_item,
    has_length,
    is_,
    is_not,
    not_none,
)
from requests import HTTPError

from codemie_test_harness.tests.test_data.hosted_application_category_test_data import (
    ASSIGNED_APPLICATIONS_TEXT,
    CATALOG_SCOPES,
    CATEGORY_IN_USE_MESSAGE,
    CONFLICT_STATUS,
    IDEMPOTENCY_CONFLICT_CODE,
    INVALID_CATEGORIES_CODE,
    INVALID_CURSOR_CODE,
    INVALID_FILTER_CODE,
    INVALID_FILTER_TEXT,
    INVALID_FILTERS,
    PUBLISH_REFUSALS,
    PUBLISHED_NEEDS_ONE_TEXT,
    REFUSED_STATUS,
    SAVE_REFUSALS,
)
from codemie_test_harness.tests.utils.base_utils import (
    assert_error_details,
    get_random_name,
)
from codemie_test_harness.tests.utils.hosted_application_utils import (
    category_ids,
    category_pairs,
    error_code,
    error_status,
    error_text,
)

CAPABILITY = "features:hostedApplications"


def pairs(categories) -> list[tuple[str, str]]:
    """The ``(id, name)`` of platform categories, in the given order."""
    return [(category.id, category.name) for category in categories]


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize("count", [1, 3], ids=["one_category", "three_categories"])
@pytest.mark.hosted_applications
@pytest.mark.api
def test_publish_stores_exactly_the_sent_categories(
    hosted_owner, hosted_reader, hosted_categories, count
):
    # @case hosted-app-categories_TC_001
    sent = hosted_categories[:count]
    app = hosted_owner.apps.create_app(hosted_owner.personal_project)

    published = hosted_owner.apps.publish(app.id, [category.id for category in sent])

    assert_that(published.is_global, is_(True), "the reply says the app is published")
    assert_that(
        category_pairs(published),
        equal_to(pairs(sent)),
        "the reply lists the sent categories in the sent order",
    )
    assert_that(
        category_pairs(hosted_owner.apps.get_app(app.id)),
        equal_to(pairs(sent)),
        "the app carries exactly the sent categories when read back",
    )
    assert_that(
        hosted_reader.apps.all_app_ids("marketplace", q=app.name),
        has_item(app.id),
        "the marketplace lists the published app",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize(
    "refusal", PUBLISH_REFUSALS, ids=[item.id for item in PUBLISH_REFUSALS]
)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_publish_with_invalid_categories_is_refused_and_the_app_stays_unpublished(
    hosted_owner, hosted_categories, refusal
):
    # @case hosted-app-categories_TC_002
    kept = hosted_categories[0]
    app = hosted_owner.apps.create_app(
        hosted_owner.personal_project, categories=[kept.id]
    )

    with pytest.raises(HTTPError) as refused:
        hosted_owner.service.marketplace_publish(
            app.id, app.etag, categories=refusal.ids(hosted_categories)
        )

    assert_that(error_status(refused.value), equal_to(REFUSED_STATUS), "the status")
    assert_that(error_code(refused.value), equal_to(refusal.code), "the error code")
    assert_that(error_text(refused.value), contains_string(refusal.text), "the reason")
    reread = hosted_owner.apps.get_app(app.id)
    assert_that(reread.is_global, is_(False), "the app is still unpublished")
    assert_that(
        category_ids(reread), equal_to([kept.id]), "its categories are unchanged"
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize("count", [0, 3], ids=["no_category", "three_categories"])
@pytest.mark.hosted_applications
@pytest.mark.api
def test_create_with_zero_or_three_categories_lists_them_in_the_reply(
    hosted_owner, hosted_categories, count
):
    # @case hosted-app-categories_TC_003
    sent = hosted_categories[:count]

    app = hosted_owner.apps.create_app(
        hosted_owner.personal_project, categories=[category.id for category in sent]
    )

    assert_that(
        category_pairs(app), equal_to(pairs(sent)), "the create reply lists them"
    )
    assert_that(
        category_pairs(hosted_owner.apps.get_app(app.id)),
        equal_to(pairs(sent)),
        "a fresh read lists the same categories in the same order",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize(
    "refusal", SAVE_REFUSALS, ids=[item.id for item in SAVE_REFUSALS]
)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_create_with_invalid_categories_is_refused_and_creates_no_app(
    hosted_owner, hosted_categories, refusal
):
    # @case hosted-app-categories_TC_004
    name = get_random_name()

    with pytest.raises(HTTPError) as refused:
        hosted_owner.service.create_application(
            name,
            "Application created by an automated test",
            hosted_owner.personal_project,
            categories=refusal.ids(hosted_categories),
        )

    assert_that(error_status(refused.value), equal_to(REFUSED_STATUS), "the status")
    assert_that(error_code(refused.value), equal_to(refusal.code), "the error code")
    assert_that(error_text(refused.value), contains_string(refusal.text), "the reason")
    assert_that(
        hosted_owner.apps.all_app_ids("mine", q=name),
        empty(),
        "no application was created",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize(
    "refusal", SAVE_REFUSALS, ids=[item.id for item in SAVE_REFUSALS]
)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_edit_with_invalid_categories_is_refused_and_leaves_the_app_unchanged(
    hosted_owner, hosted_categories, refusal
):
    # @case hosted-app-categories_TC_004
    kept = hosted_categories[0]
    app = hosted_owner.apps.create_app(
        hosted_owner.personal_project, categories=[kept.id]
    )

    with pytest.raises(HTTPError) as refused:
        hosted_owner.service.update_application(
            app.id, app.etag, categories=refusal.ids(hosted_categories)
        )

    assert_that(error_status(refused.value), equal_to(REFUSED_STATUS), "the status")
    assert_that(error_code(refused.value), equal_to(refusal.code), "the error code")
    assert_that(error_text(refused.value), contains_string(refusal.text), "the reason")
    assert_that(
        category_ids(hosted_owner.apps.get_app(app.id)),
        equal_to([kept.id]),
        "the app keeps its categories",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_edit_of_an_unpublished_app_sets_changes_and_clears_its_categories(
    hosted_owner, hosted_categories
):
    # @case hosted-app-categories_TC_005
    first, second, third = hosted_categories
    app = hosted_owner.apps.create_app(hosted_owner.personal_project)

    two = hosted_owner.apps.update_categories(app.id, [first.id, second.id])
    one = hosted_owner.apps.update_categories(app.id, [third.id])
    none = hosted_owner.apps.update_categories(app.id, [])

    assert_that(
        category_pairs(two),
        equal_to(pairs([first, second])),
        "the first edit sets two categories",
    )
    assert_that(
        category_pairs(one),
        equal_to(pairs([third])),
        "the second edit replaces them with a different one",
    )
    assert_that(category_pairs(none), empty(), "the third edit clears them")
    assert_that(
        category_pairs(hosted_owner.apps.get_app(app.id)),
        empty(),
        "a fresh read has none",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_edit_of_a_published_app_must_keep_a_category_and_accepts_one_to_three(
    hosted_owner, hosted_categories
):
    # @case hosted-app-categories_TC_006
    first, second, third = hosted_categories
    app = hosted_owner.apps.create_app(hosted_owner.personal_project)
    published = hosted_owner.apps.publish(app.id, [first.id, second.id])

    with pytest.raises(HTTPError) as refused:
        hosted_owner.service.update_application(app.id, published.etag, categories=[])

    assert_that(error_status(refused.value), equal_to(REFUSED_STATUS), "the status")
    assert_that(
        error_code(refused.value), equal_to(INVALID_CATEGORIES_CODE), "the error code"
    )
    assert_that(
        error_text(refused.value),
        contains_string(PUBLISHED_NEEDS_ONE_TEXT),
        "the reason",
    )
    reread = hosted_owner.apps.get_app(app.id)
    assert_that(reread.is_global, is_(True), "the app is still published")
    assert_that(
        category_pairs(reread),
        equal_to(pairs([first, second])),
        "its two categories are unchanged",
    )

    edited = hosted_owner.apps.update_categories(app.id, [third.id])

    assert_that(
        category_pairs(edited), equal_to(pairs([third])), "one category is accepted"
    )
    assert_that(edited.is_global, is_(True), "the app stays published")


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_unpublish_keeps_the_categories_of_the_app(hosted_owner, hosted_categories):
    # @case hosted-app-categories_TC_007
    sent = hosted_categories[:2]
    app = hosted_owner.apps.create_app(hosted_owner.personal_project)
    hosted_owner.apps.publish(app.id, [category.id for category in sent])

    unpublished = hosted_owner.apps.unpublish(app.id)

    assert_that(unpublished.is_global, is_(False), "the app is no longer published")
    assert_that(
        category_pairs(unpublished),
        equal_to(pairs(sent)),
        "the unpublish reply keeps the categories",
    )
    assert_that(
        category_ids(hosted_owner.apps.get_app(app.id)),
        equal_to([category.id for category in sent]),
        "a fresh read still lists both",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_publish_retried_with_other_categories_under_the_same_key_is_a_conflict(
    hosted_owner, hosted_categories
):
    # @case hosted-app-categories_TC_008
    first, second, _ = hosted_categories
    key = str(uuid4())
    app = hosted_owner.apps.create_app(hosted_owner.personal_project)

    published = hosted_owner.service.marketplace_publish(
        app.id, app.etag, idempotency_key=key, categories=[first.id]
    )

    with pytest.raises(HTTPError) as conflict:
        hosted_owner.service.marketplace_publish(
            app.id, app.etag, idempotency_key=key, categories=[second.id]
        )
    replay = hosted_owner.service.marketplace_publish(
        app.id, app.etag, idempotency_key=key, categories=[first.id]
    )

    assert_that(
        category_ids(published), equal_to([first.id]), "the first call published [A]"
    )
    assert_that(
        error_status(conflict.value), equal_to(CONFLICT_STATUS), "the conflict status"
    )
    assert_that(
        error_code(conflict.value),
        equal_to(IDEMPOTENCY_CONFLICT_CODE),
        "the retry with other categories is not a replay",
    )
    assert_that(replay.id, equal_to(published.id), "the same request replays the app")
    assert_that(
        category_ids(replay), equal_to([first.id]), "the replay is the first result"
    )
    assert_that(
        category_ids(hosted_owner.apps.get_app(app.id)),
        equal_to([first.id]),
        "the conflicting retry changed nothing",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize(
    "category_world", CATALOG_SCOPES, indirect=True, ids=CATALOG_SCOPES
)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_category_filter_lists_only_apps_carrying_a_selected_category(
    category_world, hosted_categories
):
    # @case hosted-app-categories_TC_009
    world = category_world
    first, second = hosted_categories[0].id, hosted_categories[1].id
    both_name = world.name_of("both")

    assert_that(
        world.listed(),
        contains_inanyorder(*world.ids(*world.unfiltered)),
        "with no category selected the scope lists what it did before",
    )
    assert_that(
        world.listed(category=[first]),
        contains_inanyorder(*world.ids("alpha", "both")),
        "one category lists the apps that carry it",
    )
    assert_that(
        world.listed(category=[first, second]),
        contains_inanyorder(*world.ids("alpha", "beta", "both")),
        "two categories list the apps that carry either",
    )
    assert_that(
        world.listed(q=both_name, category=[first]),
        contains_exactly(*world.ids("both")),
        "a name search narrows the filtered list",
    )
    assert_that(
        world.listed(category=[first, second]),
        is_not(has_item(world.apps["plain"].id)),
        "the app without a category is not listed under a category filter",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_paging_under_a_category_filter_covers_each_app_once_and_refuses_a_foreign_cursor(
    hosted_owner, hosted_categories
):
    # @case hosted-app-categories_TC_010
    first, second = hosted_categories[0], hosted_categories[1]
    tagged = [
        hosted_owner.apps.create_app(
            hosted_owner.personal_project, categories=[first.id]
        ).id
        for _ in range(3)
    ]

    pages = hosted_owner.apps.pages(1, category=[first.id])
    page_ids = [app_id for page in pages for app_id in page]
    first_page = hosted_owner.service.list_applications(
        scope="mine", limit=1, category=[first.id]
    )

    assert_that(
        page_ids, contains_inanyorder(*tagged), "the pages cover the three apps"
    )
    assert_that(set(page_ids), has_length(len(page_ids)), "no app repeats")
    assert_that(first_page.next_cursor, not_none(), "the first page has a next page")
    with pytest.raises(HTTPError) as refused:
        hosted_owner.service.list_applications(
            scope="mine",
            limit=1,
            cursor=first_page.next_cursor,
            category=[second.id],
        )
    assert_that(error_status(refused.value), equal_to(REFUSED_STATUS), "the status")
    assert_that(
        error_code(refused.value),
        equal_to(INVALID_CURSOR_CODE),
        "a cursor of another selection is refused",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize(
    "invalid", INVALID_FILTERS, ids=[item.id for item in INVALID_FILTERS]
)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_unknown_or_oversized_category_filter_is_an_invalid_filter(
    hosted_owner, invalid
):
    # @case hosted-app-categories_TC_011
    with pytest.raises(HTTPError) as refused:
        hosted_owner.service.list_applications(scope="mine", category=invalid.ids())

    assert_that(error_status(refused.value), equal_to(REFUSED_STATUS), "the status")
    assert_that(
        error_code(refused.value), equal_to(INVALID_FILTER_CODE), "the error code"
    )
    assert_that(
        error_text(refused.value), contains_string(INVALID_FILTER_TEXT), "the reason"
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_category_in_use_by_a_live_app_cannot_be_deleted_until_the_app_is_deleted(
    hosted_temp_category, hosted_owner, categories_utils
):
    # @case hosted-app-categories_TC_012
    category = hosted_temp_category()
    app = hosted_owner.apps.create_app(
        hosted_owner.personal_project, categories=[category.id]
    )

    with pytest.raises(HTTPError) as refused:
        categories_utils.delete_category(category.id)

    assert_error_details(
        refused.value.response, CONFLICT_STATUS, CATEGORY_IN_USE_MESSAGE, "message"
    )
    assert_error_details(
        refused.value.response, CONFLICT_STATUS, ASSIGNED_APPLICATIONS_TEXT
    )
    assert_error_details(refused.value.response, CONFLICT_STATUS, app.name)

    hosted_owner.apps.delete_app(app.id)
    categories_utils.delete_category(category.id)

    assert_that(
        [item.id for item in categories_utils.get_categories()],
        is_not(has_item(category.id)),
        "the category is gone once the app is deleted",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_create_retry_with_the_same_key_replays_the_app_with_or_without_empty_categories(
    hosted_owner,
):
    # @case hosted-app-categories_TC_013
    key = str(uuid4())
    app = hosted_owner.apps.create_app(
        hosted_owner.personal_project, idempotency_key=key
    )

    replay = hosted_owner.service.create_application(
        app.name,
        app.description,
        hosted_owner.personal_project,
        idempotency_key=key,
        categories=[],
    )

    assert_that(replay.id, equal_to(app.id), "the retry is the same application")
    assert_that(
        hosted_owner.apps.all_app_ids("mine", q=app.name),
        equal_to([app.id]),
        "only one application was created",
    )
