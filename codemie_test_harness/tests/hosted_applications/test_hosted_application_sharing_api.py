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

"""Hosted applications API: sharing by name, project, marketplace and link, and what a viewing
session keeps once the access behind it is taken away."""

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
)
from requests import HTTPError

from codemie_test_harness.tests.test_data.hosted_application_test_data import (
    GRANTEE_SCOPE_VIEWS,
    HIDDEN_FROM_READER,
    NOT_FOUND_CODE,
    REVOCATIONS,
    SESSION_ENDED_STATUS,
    html_artifact,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.hosted_application_utils import (
    error_code,
    error_status,
)
from codemie_test_harness.tests.utils.hosted_content_utils import (
    HostedContentSession,
)

CAPABILITY = "features:hostedApplications"


def should_be_hidden_from(user, app_id: str) -> None:
    """The application neither loads nor launches for ``user``."""
    for call in (user.service.get_application, user.service.launch):
        with pytest.raises(HTTPError) as hidden:
            call(app_id)
        assert_that(
            error_status(hidden.value),
            equal_to(HIDDEN_FROM_READER),
            "the application does not exist for this user",
        )
        assert_that(
            error_code(hidden.value),
            equal_to(NOT_FOUND_CODE),
            "the refusal does not tell the application exists",
        )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_named_recipient_opens_live_version_and_unlisted_user_gets_nothing(
    hosted_live_app, hosted_owner, hosted_reader, hosted_user_factory
):
    # @case hosted-applications-upload-share-view_TC_009
    app, artifact = hosted_live_app
    unlisted = hosted_user_factory()

    shared = hosted_owner.service.share_with_users(app.id, [hosted_reader.user_id])

    assert_that(
        [item["id"] for item in shared.shared_with],
        contains_exactly(hosted_reader.user_id),
        "the share list holds the one chosen person",
    )
    HostedContentSession.open(hosted_reader.service, app.id).should_serve(
        artifact.marker
    )
    should_be_hidden_from(unlisted, app.id)


@pytest.fixture
def published_app(hosted_live_app, hosted_owner):
    """The live application of ``hosted_live_app``, published to the marketplace."""
    app, artifact = hosted_live_app
    hosted_owner.apps.publish(app.id)
    return hosted_owner.apps.get_app(app.id), artifact


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_unpublished_application_leaves_the_marketplace_scope(
    published_app, hosted_owner, hosted_reader
):
    # @case hosted-applications-upload-share-view_TC_010
    app, _ = published_app

    assert_that(
        hosted_reader.apps.all_app_ids("marketplace", q=app.name),
        has_item(app.id),
        "other users find the published application in the marketplace",
    )

    hosted_owner.apps.unpublish(app.id)

    assert_that(
        hosted_reader.apps.all_app_ids("marketplace", q=app.name),
        is_not(has_item(app.id)),
        "the marketplace no longer lists it",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_unpublished_application_stays_open_only_to_a_named_recipient(
    published_app, hosted_owner, hosted_reader, hosted_user_factory
):
    # @case hosted-applications-upload-share-view_TC_010
    app, artifact = published_app
    without_grant = hosted_user_factory()
    hosted_owner.service.share_with_users(app.id, [hosted_reader.user_id])

    hosted_owner.apps.unpublish(app.id)

    should_be_hidden_from(without_grant, app.id)
    HostedContentSession.open(hosted_reader.service, app.id).should_serve(
        artifact.marker
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize(
    "revocation", REVOCATIONS, ids=[item.id for item in REVOCATIONS]
)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_open_viewing_session_is_denied_after_access_is_revoked(
    hosted_live_app, hosted_owner, hosted_reader, revocation
):
    # @case hosted-applications-upload-share-view_TC_011
    app, artifact = hosted_live_app
    revocation.grant(hosted_owner, hosted_reader, app.id)
    session = HostedContentSession.open(hosted_reader.service, app.id)
    session.should_serve(artifact.marker)

    revocation.revoke(hosted_owner, hosted_reader, app.id)

    after = session.page()
    assert_that(
        after.status_code,
        equal_to(SESSION_ENDED_STATUS),
        "the same session cookie is refused on the next request",
    )
    assert_that(
        after.text,
        is_not(contains_string(artifact.marker)),
        "no byte of the application is served after the revocation",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_new_version_stays_hidden_from_recipients_until_it_is_released(
    hosted_live_app, hosted_owner, hosted_reader
):
    # @case hosted-applications-upload-share-view_TC_012
    app, first = hosted_live_app
    second = html_artifact()
    hosted_owner.service.share_with_users(app.id, [hosted_reader.user_id])
    HostedContentSession.open(hosted_reader.service, app.id).should_serve(first.marker)

    version = hosted_owner.apps.upload_accepted_version(app.id, second)

    assert_that(
        hosted_owner.apps.get_app(app.id).active_version_id,
        equal_to(app.active_version_id),
        "the accepted version is not live yet",
    )
    still_first = HostedContentSession.open(hosted_reader.service, app.id).page()
    assert_that(
        still_first.text,
        contains_string(first.marker),
        "the recipient still gets the first version",
    )
    assert_that(
        still_first.text,
        is_not(contains_string(second.marker)),
        "and nothing of the new one",
    )

    hosted_owner.apps.activate(app.id, version.id)

    released = hosted_reader.service.get_application(app.id)
    assert_that(released.id, equal_to(app.id), "the application id did not change")
    now_second = HostedContentSession.open(hosted_reader.service, app.id).page()
    assert_that(
        now_second.text,
        contains_string(second.marker),
        "the same application now shows the released version",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_project_members_open_a_project_shared_application_and_outsiders_do_not(
    hosted_user_factory, hosted_project_factory
):
    # @case hosted-applications-upload-share-view_TC_026
    owner, member, outsider = (hosted_user_factory() for _ in range(3))
    project = hosted_project_factory(owner, member)
    artifact = html_artifact()
    app = owner.apps.create_app(project, shared=True)
    owner.apps.go_live(app.id, artifact)

    assert_that(
        member.service.get_application(app.id).id,
        equal_to(app.id),
        "a member of the project reads the application",
    )
    HostedContentSession.open(member.service, app.id).should_serve(artifact.marker)
    should_be_hidden_from(outsider, app.id)


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_share_link_grants_access_until_the_owner_revokes_it(
    hosted_live_app, hosted_owner, hosted_reader
):
    # @case hosted-applications-upload-share-view_TC_027
    app, artifact = hosted_live_app

    link = hosted_owner.service.create_share_link(app.id).link
    assert_that(link.token, is_not(empty()), "the owner gets a link token")

    opened = hosted_reader.service.open_share_link(link.token)
    assert_that(opened.app_id, equal_to(app.id), "the link leads to the application")
    session = HostedContentSession.open(hosted_reader.service, app.id)
    session.should_serve(artifact.marker)

    revoked = hosted_owner.service.delete_share_link(app.id)

    assert_that(revoked.link, is_(None), "the application has no link any more")
    assert_that(
        session.page().status_code,
        equal_to(SESSION_ENDED_STATUS),
        "the next content request of the visitor is denied",
    )
    should_be_hidden_from(hosted_reader, app.id)


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_owner_lists_private_and_shared_applications_under_mine(
    hosted_owner, hosted_reader
):
    # @case hosted-applications-upload-share-view_TC_028
    prefix = get_random_name()
    private = hosted_owner.apps.create_app(
        hosted_owner.personal_project, name=f"{prefix}-private"
    )
    shared = hosted_owner.apps.create_app(
        hosted_owner.personal_project, name=f"{prefix}-shared"
    )
    hosted_owner.service.share_with_users(shared.id, [hosted_reader.user_id])

    assert_that(
        hosted_owner.apps.all_app_ids("mine", q=prefix),
        contains_inanyorder(private.id, shared.id),
        "both applications are the owner's own",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize(
    "view", GRANTEE_SCOPE_VIEWS, ids=[item.id for item in GRANTEE_SCOPE_VIEWS]
)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_catalog_scope_lists_only_what_a_named_recipient_may_open(
    hosted_owner, hosted_reader, view
):
    # @case hosted-applications-upload-share-view_TC_028
    prefix = get_random_name()
    ids = {
        suffix: hosted_owner.apps.create_app(
            hosted_owner.personal_project, name=f"{prefix}-{suffix}"
        ).id
        for suffix in ("private", "shared")
    }
    hosted_owner.service.share_with_users(ids["shared"], [hosted_reader.user_id])

    assert_that(
        hosted_reader.apps.all_app_ids(view.scope, q=prefix),
        equal_to([ids[suffix] for suffix in view.visible]),
        f"the '{view.scope}' scope lists only what the user may open",
    )
