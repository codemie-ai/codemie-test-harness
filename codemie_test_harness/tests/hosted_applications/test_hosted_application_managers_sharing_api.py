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

"""Hosted applications API: every manager of an application shares it and manages who has access.

The managers are its creator, the admins of its project, platform admins and maintainers. Anyone
else is refused on every sharing route, and a suspended application takes no new access while its
managers may still take access away. The activity log names the manager who acted.
"""

from functools import partial

import pytest
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
    not_none,
)
from requests import HTTPError

from codemie_test_harness.tests.test_data.hosted_application_test_data import (
    APP_SUSPENDED_CODE,
    APP_SUSPENDED_STATUS,
    CAN_SHARE_PERSONAS,
    GRANT_ADDED_EVENT,
    GRANT_REMOVALS,
    GRANT_REMOVED_EVENT,
    LINK_CREATED_EVENT,
    LINK_REVOKED_EVENT,
    NON_CREATOR_MANAGERS,
    REFUSED_SHARE_INPUTS,
    REVOCATION_WAIT_SECONDS,
    SESSION_ENDED_STATUS,
    SHARE_SUSPENDED_MESSAGE,
    SHARING_MANAGERS,
    SHARING_REFUSALS,
    SHARING_ROUTES,
    SHARING_SUSPENSION_REASON,
)
from codemie_test_harness.tests.utils.base_utils import poll_until
from codemie_test_harness.tests.utils.hosted_application_utils import (
    error_code,
    error_message,
    error_status,
)
from codemie_test_harness.tests.utils.hosted_content_utils import (
    HostedContentSession,
)
from codemie_test_harness.tests.utils.hosted_sharing_utils import (
    activity_event,
    shared_ids,
)

CAPABILITY = "features:hostedApplications"


def should_refuse(call, status: int, code, message: str, what: str) -> None:
    """``call`` fails with exactly this status, platform error code and message."""
    with pytest.raises(HTTPError) as refused:
        call()
    assert_that(error_status(refused.value), equal_to(status), f"{what}: the status")
    assert_that(error_code(refused.value), equal_to(code), f"{what}: the error code")
    assert_that(error_message(refused.value), equal_to(message), f"{what}: the message")


def page_after_revocation(session: HostedContentSession):
    """The session's page once a stale replica no longer serves it; the last answer if that never happens."""
    return poll_until(
        session.page,
        lambda response: response.status_code == SESSION_ENDED_STATUS,
        timeout=REVOCATION_WAIT_SECONDS,
        interval=1.0,
    )


def should_refuse_every_sharing_route(service, app_id: str, user_id: str, refusal):
    """Each sharing route answers the caller behind ``service`` with the refusal of ``refusal``."""
    for route in SHARING_ROUTES:
        should_refuse(
            partial(route.call, service, app_id, user_id),
            refusal.status,
            refusal.code,
            refusal.message,
            f"the '{route.id}' route",
        )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize(
    "persona", CAN_SHARE_PERSONAS, ids=[item.id for item in CAN_SHARE_PERSONAS]
)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_application_tells_each_reader_whether_they_may_share_it(
    sharing_world, persona
):
    # @case hosted-app-managers-share_TC_001
    world = sharing_world(shared=persona.shared, published=persona.published)
    reader = world.person(persona.role)

    app = reader.service.get_application(world.app_id)

    assert_that(app.id, equal_to(world.app_id), "the person reads the application")
    assert_that(
        app.can_share,
        is_(persona.can_share),
        f"can_share tells the {persona.role} whether they may share the application",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize("manager_role", NON_CREATOR_MANAGERS, ids=NON_CREATOR_MANAGERS)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_manager_who_is_not_the_creator_shares_by_name_and_the_log_names_them(
    sharing_world, hosted_activity, manager_role
):
    # @case hosted-app-managers-share_TC_002
    world = sharing_world()
    manager = world.person(manager_role)
    recipient = world.people.user()

    shared = manager.service.share_with_users(world.app_id, [recipient.user_id])

    assert_that(
        shared_ids(shared),
        contains_exactly(recipient.user_id),
        "the share answer lists the person the manager chose",
    )
    HostedContentSession.open(recipient.service, world.app_id).should_serve(
        world.artifact.marker
    )
    event = activity_event(
        hosted_activity,
        world.app_id,
        GRANT_ADDED_EVENT,
        principal_id=recipient.user_id,
    )
    assert_that(event, not_none(), "the activity log records the new grant")
    assert_that(
        event.actor_id,
        equal_to(manager.user_id),
        "the activity log names the manager who shared",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize(
    "removal", GRANT_REMOVALS, ids=[item.id for item in GRANT_REMOVALS]
)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_manager_removes_a_person_whoever_added_them_and_access_ends_on_the_next_request(
    sharing_world, hosted_activity, removal
):
    # @case hosted-app-managers-share_TC_003
    world = sharing_world()
    granter = world.person(removal.granter)
    remover = world.person(removal.remover)
    person = world.people.user()
    granter.service.share_with_users(world.app_id, [person.user_id])
    session = HostedContentSession.open(person.service, world.app_id)
    session.should_serve(world.artifact.marker)

    assert_that(
        shared_ids(remover.service.shared_with(world.app_id)),
        has_item(person.user_id),
        f"the {removal.remover} sees the person the {removal.granter} added",
    )

    after = remover.service.unshare(world.app_id, [person.user_id])

    assert_that(
        shared_ids(after),
        is_not(has_item(person.user_id)),
        "the answer no longer lists the person",
    )
    refused = page_after_revocation(session)
    assert_that(
        refused.status_code,
        equal_to(SESSION_ENDED_STATUS),
        "the person's open viewing session is refused on its next request",
    )
    assert_that(
        refused.text,
        is_not(contains_string(world.artifact.marker)),
        "no content of the application is served after the removal",
    )
    event = activity_event(
        hosted_activity,
        world.app_id,
        GRANT_REMOVED_EVENT,
        principal_id=person.user_id,
    )
    assert_that(event, not_none(), "the activity log records the removal")
    assert_that(
        event.actor_id,
        equal_to(remover.user_id),
        "the activity log names the manager who removed the person",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize("manager_role", NON_CREATOR_MANAGERS, ids=NON_CREATOR_MANAGERS)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_manager_reuses_and_revokes_the_creators_share_link_and_the_log_names_them(
    sharing_world, hosted_activity, manager_role
):
    # @case hosted-app-managers-share_TC_004
    world = sharing_world()
    manager = world.person(manager_role)
    creators_link = world.creator.service.create_share_link(world.app_id).link
    visitor = world.people.user()
    opened = visitor.service.open_share_link(creators_link.token)
    assert_that(
        opened.app_id, equal_to(world.app_id), "the link leads to the application"
    )
    session = HostedContentSession.open(visitor.service, world.app_id)
    session.should_serve(world.artifact.marker)

    read = manager.service.get_share_link(world.app_id).link
    assert_that(read, not_none(), "the manager reads the live link")
    assert_that(
        read.token,
        equal_to(creators_link.token),
        "the manager reads the link the creator made",
    )

    again = manager.service.create_share_link(world.app_id).link
    assert_that(
        again.id,
        equal_to(creators_link.id),
        "creating a link returns the live one instead of a second link",
    )
    assert_that(again.token, equal_to(creators_link.token), "with the creator's token")

    revoked = manager.service.delete_share_link(world.app_id)

    assert_that(revoked.link, is_(None), "the application has no live link any more")
    assert_that(
        page_after_revocation(session).status_code,
        equal_to(SESSION_ENDED_STATUS),
        "the visitor's next content request is refused",
    )

    fresh = manager.service.create_share_link(world.app_id).link
    assert_that(
        fresh.token,
        is_not(equal_to(creators_link.token)),
        "a link made after the revocation has a new token",
    )
    revoked_event = activity_event(
        hosted_activity, world.app_id, LINK_REVOKED_EVENT, link_id=creators_link.id
    )
    assert_that(revoked_event, not_none(), "the activity log records the revocation")
    assert_that(
        revoked_event.actor_id,
        equal_to(manager.user_id),
        "the revocation names the manager",
    )
    created_event = activity_event(
        hosted_activity, world.app_id, LINK_CREATED_EVENT, link_id=fresh.id
    )
    assert_that(created_event, not_none(), "the activity log records the new link")
    assert_that(
        created_event.actor_id,
        equal_to(manager.user_id),
        "the new link names the manager",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize(
    "refusal", SHARING_REFUSALS, ids=[item.id for item in SHARING_REFUSALS]
)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_non_manager_is_refused_on_every_sharing_route(sharing_world, refusal):
    # @case hosted-app-managers-share_TC_005
    world = sharing_world(shared=refusal.shared, published=refusal.published)
    bystander = world.people.user()
    world.creator.service.share_with_users(world.app_id, [bystander.user_id])
    world.creator.service.create_share_link(world.app_id)
    outsider = world.person(refusal.role)
    grants_before = world.shared_with_ids()
    link_before = world.live_link_token()
    assert_that(
        grants_before, has_item(bystander.user_id), "the application has a grant"
    )
    assert_that(link_before, not_none(), "the application has a live link")

    should_refuse_every_sharing_route(
        outsider.service, world.app_id, bystander.user_id, refusal
    )

    assert_that(
        world.shared_with_ids(),
        equal_to(grants_before),
        "the refused calls left the grants as they were",
    )
    assert_that(
        world.live_link_token(),
        equal_to(link_before),
        "the refused calls left the live link as it was",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_people_search_leaves_out_the_creator_and_offers_admins_and_people_to_add(
    sharing_world,
):
    # @case hosted-app-managers-share_TC_006
    world = sharing_world()
    project_admin = world.person("project_admin")
    platform_admin = world.person("platform_admin")
    ordinary = world.people.user()

    by_creator = project_admin.service.sharable_users(world.app_id, world.creator.email)
    by_admin = project_admin.service.sharable_users(world.app_id, platform_admin.email)

    assert_that(
        [user["id"] for user in by_creator.users],
        is_not(has_item(world.creator.user_id)),
        "searching the creator's e-mail never offers the creator",
    )
    assert_that(
        [user["id"] for user in by_admin.users],
        has_item(platform_admin.user_id),
        "the same search offers another admin",
    )

    shared = project_admin.service.share_with_users(
        world.app_id, [platform_admin.user_id, ordinary.user_id]
    )

    assert_that(
        shared_ids(shared),
        contains_inanyorder(platform_admin.user_id, ordinary.user_id),
        "the admin and an ordinary person are both added",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize(
    "share_input", REFUSED_SHARE_INPUTS, ids=[item.id for item in REFUSED_SHARE_INPUTS]
)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_share_naming_the_creator_or_an_unsharable_id_is_refused_whole(
    sharing_world, share_input
):
    # @case hosted-app-managers-share_TC_006
    world = sharing_world()
    project_admin = world.person("project_admin")
    user_ids = share_input.recipients(world)

    should_refuse(
        lambda: project_admin.service.share_with_users(world.app_id, user_ids),
        share_input.status,
        share_input.code,
        share_input.message(user_ids),
        f"sharing '{share_input.id}'",
    )

    assert_that(
        world.shared_with_ids(),
        empty(),
        "nobody named in the refused request is granted",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize("manager_role", SHARING_MANAGERS, ids=SHARING_MANAGERS)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_suspended_application_refuses_new_access_and_lets_a_manager_remove_access(
    sharing_world, manager_role
):
    # @case hosted-app-managers-share_TC_007
    world = sharing_world()
    recipient = world.people.user()
    world.creator.service.share_with_users(world.app_id, [recipient.user_id])
    link = world.creator.service.create_share_link(world.app_id).link
    manager = world.person(manager_role)
    reviewer = world.people.user(admin=True)
    reviewer.service.suspend_application(world.app_id, SHARING_SUSPENSION_REASON)
    newcomer = world.people.user()

    should_refuse(
        lambda: manager.service.share_with_users(world.app_id, [newcomer.user_id]),
        APP_SUSPENDED_STATUS,
        APP_SUSPENDED_CODE,
        SHARE_SUSPENDED_MESSAGE,
        "sharing a suspended application with a new person",
    )
    should_refuse(
        lambda: manager.service.create_share_link(world.app_id),
        APP_SUSPENDED_STATUS,
        APP_SUSPENDED_CODE,
        SHARE_SUSPENDED_MESSAGE,
        "creating a share link of a suspended application",
    )

    assert_that(
        shared_ids(manager.service.shared_with(world.app_id)),
        contains_exactly(recipient.user_id),
        "shared-with still answers, and the refused share granted nobody",
    )
    live = manager.service.get_share_link(world.app_id).link
    assert_that(live, not_none(), "the share link still answers")
    assert_that(live.id, equal_to(link.id), "with the creator's live link")

    after_unshare = manager.service.unshare(world.app_id, [recipient.user_id])
    revoked = manager.service.delete_share_link(world.app_id)

    assert_that(shared_ids(after_unshare), empty(), "the manager removes the person")
    assert_that(revoked.link, is_(None), "the manager revokes the link")
    assert_that(
        manager.service.get_share_link(world.app_id).link,
        is_(None),
        "no live link remains",
    )
