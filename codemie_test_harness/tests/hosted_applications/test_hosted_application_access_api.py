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

"""Hosted applications API: who may reach an application, and who is refused."""

import pytest
from hamcrest import assert_that, equal_to, is_
from requests import HTTPError

from codemie_test_harness.cli.constants import PROVISIONING_READ_CLIENT_KEYS
from codemie_test_harness.tests.test_data.hosted_application_test_data import (
    HIDDEN_REQUESTS,
    HIDDEN_FROM_READER,
    INDEPENDENT_REVIEW_CODE,
    NOT_FOUND_CODE,
    NOT_SUSPENDED_CODE,
    SERVICE_ACCOUNT_REFUSAL,
    html_artifact,
)
from codemie_test_harness.tests.utils.hosted_application_utils import (
    error_code,
    error_status,
)
from codemie_test_harness.tests.utils.hosted_content_utils import (
    HostedContentSession,
)

CAPABILITY = "features:hostedApplications"
SUSPENSION_REASON = "Security review by an automated test"
REINSTATE_REASON = "Reviewed by an independent administrator in an automated test"
ACCOUNT_UNAVAILABLE_REASON = "Applications are not available for this account"


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.requires_setting(*PROVISIONING_READ_CLIENT_KEYS)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_service_account_sees_hosted_applications_as_unavailable(
    service_account_hosted,
):
    # @case hosted-applications-upload-share-view_TC_002
    capabilities = service_account_hosted.capabilities()

    assert_that(capabilities.view, is_(False), "the account may not open applications")
    assert_that(capabilities.create, is_(False), "the account may not create them")
    assert_that(
        capabilities.disabled_reason,
        equal_to(ACCOUNT_UNAVAILABLE_REASON),
        "the answer says the feature is unavailable for the account",
    )

    with pytest.raises(HTTPError) as refused:
        service_account_hosted.list_applications()

    assert_that(
        error_status(refused.value),
        equal_to(403),
        "the list is refused as forbidden, not as an expired sign-in",
    )
    assert_that(
        error_code(refused.value),
        equal_to(SERVICE_ACCOUNT_REFUSAL),
        "the refusal names the account kind",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize(
    "reader_request", HIDDEN_REQUESTS, ids=[item.id for item in HIDDEN_REQUESTS]
)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_new_application_is_hidden_from_another_user(
    hosted_live_app, hosted_reader, reader_request
):
    # @case hosted-applications-upload-share-view_TC_004
    app, _ = hosted_live_app

    with pytest.raises(HTTPError) as hidden:
        reader_request.call(hosted_reader.service, app.id)

    assert_that(
        error_status(hidden.value),
        equal_to(HIDDEN_FROM_READER),
        "an application nobody shared with the user does not exist for them",
    )
    assert_that(
        error_code(hidden.value),
        equal_to(NOT_FOUND_CODE),
        "the refusal does not tell the application exists",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_owner_opens_own_new_application(hosted_live_app, hosted_owner):
    # @case hosted-applications-upload-share-view_TC_004
    app, artifact = hosted_live_app

    assert_that(
        hosted_owner.service.get_application(app.id).shared,
        is_(False),
        "a new application is private",
    )
    assert_that(
        hosted_owner.service.get_thumbnail(app.id).status_code,
        equal_to(204),
        "the owner reads the thumbnail route; an application without a cover has none",
    )
    HostedContentSession.open(hosted_owner.service, app.id).should_serve(
        artifact.marker
    )


@pytest.fixture
def suspended_app(hosted_user_factory):
    """A live application of an administrator, shared with one recipient and suspended by another administrator."""
    creator = hosted_user_factory(admin=True)
    reviewer = hosted_user_factory(admin=True)
    recipient = hosted_user_factory()
    artifact = html_artifact()
    app = creator.apps.create_app(creator.personal_project)
    creator.apps.go_live(app.id, artifact)
    creator.service.share_with_users(app.id, [recipient.user_id])
    before = creator.apps.get_app(app.id)
    assert_that(
        recipient.service.get_application(app.id).id,
        equal_to(app.id),
        "the recipient opens the application before the suspension",
    )
    reviewer.service.suspend_application(app.id, SUSPENSION_REASON)
    return creator, reviewer, recipient, before, artifact


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_suspended_application_is_denied_to_recipient_and_open_to_its_owner(
    suspended_app,
):
    # @case hosted-applications-upload-share-view_TC_018
    creator, _, recipient, before, artifact = suspended_app

    with pytest.raises(HTTPError) as denied:
        recipient.service.get_application(before.id)
    assert_that(
        error_status(denied.value),
        equal_to(HIDDEN_FROM_READER),
        "a suspended application is gone for its recipient",
    )
    with pytest.raises(HTTPError) as launch_denied:
        recipient.service.launch(before.id)
    assert_that(
        error_status(launch_denied.value),
        equal_to(HIDDEN_FROM_READER),
        "the recipient cannot start a viewing session",
    )

    assert_that(
        creator.service.get_application(before.id).suspended,
        is_(True),
        "the owner sees the suspension",
    )
    HostedContentSession.open(creator.service, before.id).should_serve(artifact.marker)


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_creator_cannot_reinstate_own_suspended_application(suspended_app):
    # @case hosted-applications-upload-share-view_TC_018
    creator, _, _, before, _ = suspended_app

    with pytest.raises(HTTPError) as refused:
        creator.service.reinstate_application(
            before.id, REINSTATE_REASON, creator.apps.get_app(before.id).etag
        )

    assert_that(
        error_status(refused.value),
        equal_to(403),
        "reinstating one's own application is forbidden",
    )
    assert_that(
        error_code(refused.value),
        equal_to(INDEPENDENT_REVIEW_CODE),
        "the refusal asks for an independent administrator",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_independent_administrator_reinstates_and_sharing_is_unchanged(suspended_app):
    # @case hosted-applications-upload-share-view_TC_018
    creator, reviewer, recipient, before, _ = suspended_app

    reinstated = reviewer.service.reinstate_application(
        before.id, REINSTATE_REASON, reviewer.apps.get_app(before.id).etag
    )

    assert_that(reinstated.suspended, is_(False), "the application is back in service")
    assert_that(
        reinstated.shared, equal_to(before.shared), "project sharing is unchanged"
    )
    assert_that(
        reinstated.is_global,
        equal_to(before.is_global),
        "marketplace state is unchanged",
    )
    assert_that(
        reinstated.active_version_id,
        equal_to(before.active_version_id),
        "the live version is unchanged",
    )
    assert_that(
        [item["id"] for item in creator.service.shared_with(before.id).shared_with],
        equal_to([recipient.user_id]),
        "the named recipient keeps the grant",
    )
    assert_that(
        recipient.service.get_application(before.id).id,
        equal_to(before.id),
        "the recipient opens the application again",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_reinstating_an_application_that_is_not_suspended_is_refused(
    hosted_user_factory,
):
    # @case hosted-applications-upload-share-view_TC_018
    creator = hosted_user_factory(admin=True)
    reviewer = hosted_user_factory(admin=True)
    app = creator.apps.create_app(creator.personal_project)

    with pytest.raises(HTTPError) as refused:
        reviewer.service.reinstate_application(
            app.id, REINSTATE_REASON, reviewer.apps.get_app(app.id).etag
        )

    assert_that(error_status(refused.value), equal_to(409), "the request conflicts")
    assert_that(
        error_code(refused.value),
        equal_to(NOT_SUSPENDED_CODE),
        "the refusal says nothing is suspended",
    )
