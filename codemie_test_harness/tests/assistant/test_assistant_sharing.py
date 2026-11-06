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

"""API tests for sharing an assistant with selected internal users.

Covers granting/revoking per-user READ access (POST/DELETE .../share), the
owner-only search for sharable recipients (.../sharable-users), the resulting
visibility of the assistant to the recipient, the ownership boundary on the
share/revoke action itself, the interaction between the per-user grant and the
project-wide "shared" flag, and the data-integrity/audit side effects of
granting, revoking and deleting a shared assistant.
"""

import json

import pytest
from hamcrest import (
    assert_that,
    equal_to,
    greater_than_or_equal_to,
    has_item,
    has_items,
    has_length,
    is_not,
)
from requests import HTTPError

from codemie_sdk.models.assistant import (
    AssistantUpdateRequest,
    ToolDetails,
    ToolKitDetails,
)
from codemie_sdk.models.integration import CredentialTypes, IntegrationType

from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.enums.tools import GitTool, Toolkit
from codemie_test_harness.tests.utils.activity_utils import ActivityUtils
from codemie_test_harness.tests.utils.base_utils import (
    assert_error_details,
    assert_response,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

NOT_A_SHARABLE_INTERNAL_USER = "User {uid} is not a sharable internal user"
OWNER_ONLY_MESSAGE = "Only the assistant owner can share or revoke access"
PERSONAL_INTEGRATION_MESSAGE = (
    "Assistant uses a personal integration and cannot be shared with users. "
    "Replace personal integrations with project integrations before sharing."
)


def _find_active_external_user(user_utils):
    """An existing active user whose user_type is not internal, if any exists.

    user_type is only settable through the admin API in local auth mode
    (UserManagementService.update_user_fields rejects it otherwise); this harness's
    stands authenticate via Keycloak (environments.md), so there is no writable path
    to create one for a test. This reads whatever already exists instead of inventing one.
    """
    response = user_utils.list_admin_users(
        per_page=1,
        filters=json.dumps({"user_type": "external", "is_active": True}),
    )
    if response.pagination.total < 1:
        return None
    return response.data[0]


# ---------------------------------------------------------------------------
# TC_001: grant access to multiple internal users
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.api
def test_owner_can_share_assistant_with_multiple_internal_users(
    assistant_factory, client, regular_client, non_admin_user
):
    """@case share-an-assistant-with-selected_TC_001"""
    assistant = assistant_factory.create()
    grantee_b = regular_client.users.about_me().user_id
    _, grantee_c, _ = non_admin_user

    response = client.assistants.share(assistant.id, [grantee_b, grantee_c])
    assert_that(
        [u.id for u in response.shared_with],
        has_items(grantee_b, grantee_c),
        "the 200 response should list both granted users",
    )

    refreshed = client.assistants.list_shared_with(assistant.id).shared_with
    assert_that(
        [u.id for u in refreshed],
        has_items(grantee_b, grantee_c),
        "re-fetching the shared-with list should still show both granted users",
    )


# ---------------------------------------------------------------------------
# TC_002: a shared assistant is visible only to the granted user
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.api
def test_shared_assistant_visible_only_to_granted_user(
    assistant_factory, client, regular_client, unrelated_client
):
    """@case share-an-assistant-with-selected_TC_002"""
    assistant = assistant_factory.create()
    grantee_id = regular_client.users.about_me().user_id

    client.assistants.share(assistant.id, [grantee_id])

    granted_view = regular_client.assistants.list(
        filters={"search": assistant.name}, per_page=200
    )
    assert_that(
        [a.id for a in granted_view],
        has_item(assistant.id),
        "the granted user should see the shared assistant",
    )

    unrelated_view = unrelated_client.assistants.list(
        filters={"search": assistant.name}, per_page=200
    )
    assert_that(
        [a.id for a in unrelated_view],
        is_not(has_item(assistant.id)),
        "an unrelated user must not see the assistant",
    )


# ---------------------------------------------------------------------------
# TC_004: a shared-only (read-only) recipient's direct update attempt is refused
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.api
def test_shared_only_recipient_cannot_update_assistant(
    assistant_factory, client, non_admin_user, user_utils
):
    """@case share-an-assistant-with-selected_TC_004"""
    assistant = assistant_factory.create()
    _, grantee_id, member_client = non_admin_user
    # A plain project member (not just a named grant) is required so the request clears
    # project_access_check before the WRITE-ability check this case targets is reached.
    user_utils.assign_user_to_project(grantee_id, PROJECT)
    client.assistants.share(assistant.id, [grantee_id])

    full_assistant = client.assistants.get(assistant.id)
    update_request = AssistantUpdateRequest(
        name=full_assistant.name,
        description=full_assistant.description,
        system_prompt=full_assistant.system_prompt,
        project=full_assistant.project,
        llm_model_type=full_assistant.llm_model_type,
    )

    with pytest.raises(HTTPError) as exc_info:
        member_client.assistants.update(assistant.id, update_request)

    assert_error_details(
        exc_info.value.response,
        401,
        "You do not have the necessary permissions to update this entity.",
    )


# ---------------------------------------------------------------------------
# TC_006: revocation removes both visibility and direct access
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.api
def test_revoked_user_loses_assistant_visibility_and_access(
    assistant_factory, client, regular_client
):
    """@case share-an-assistant-with-selected_TC_006"""
    assistant = assistant_factory.create()
    grantee_id = regular_client.users.about_me().user_id

    client.assistants.share(assistant.id, [grantee_id])
    assert_that(
        [
            a.id
            for a in regular_client.assistants.list(
                filters={"search": assistant.name}, per_page=200
            )
        ],
        has_item(assistant.id),
        "the assistant should be visible to B while the grant is active",
    )

    client.assistants.revoke_share(assistant.id, [grantee_id])

    assert_that(
        [
            a.id
            for a in regular_client.assistants.list(
                filters={"search": assistant.name}, per_page=200
            )
        ],
        is_not(has_item(assistant.id)),
        "the assistant must disappear from B's list after revocation",
    )

    with pytest.raises(HTTPError) as exc_info:
        regular_client.assistants.get(assistant.id)
    assert_error_details(
        exc_info.value.response,
        401,
        "You do not have the necessary permissions to view this entity.",
    )


# ---------------------------------------------------------------------------
# TC_007: sharable-users search excludes non-internal users
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.api
def test_sharable_users_search_excludes_external_users(
    assistant_factory, client, regular_client, user_utils
):
    """@case share-an-assistant-with-selected_TC_007"""
    external_user = _find_active_external_user(user_utils)
    if external_user is None:
        pytest.skip(
            "No active external-type user exists on this environment to probe the "
            "exclude_user_type filter against"
        )

    assistant = assistant_factory.create()

    external_results = client.assistants.search_sharable_users(
        assistant.id, external_user.username
    ).users
    assert_that(
        [u.id for u in external_results],
        is_not(has_item(external_user.id)),
        "an external-type user must never appear, even on an exact text match",
    )

    internal_user = regular_client.users.about_me()
    internal_results = client.assistants.search_sharable_users(
        assistant.id, internal_user.username
    ).users
    assert_that(
        [u.id for u in internal_results],
        has_item(internal_user.user_id),
        "an active internal user matching the query must appear in the search",
    )


# ---------------------------------------------------------------------------
# TC_008: direct API share with a non-internal user id is rejected
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.api
def test_direct_share_rejects_non_internal_user_id(
    assistant_factory, client, user_utils
):
    """@case share-an-assistant-with-selected_TC_008"""
    external_user = _find_active_external_user(user_utils)
    if external_user is None:
        pytest.skip(
            "No active external-type user exists on this environment to probe the "
            "server-side rejection against"
        )

    assistant = assistant_factory.create()

    with pytest.raises(HTTPError) as exc_info:
        client.assistants.share(assistant.id, [external_user.id])
    assert_response(
        exc_info.value.response,
        400,
        NOT_A_SHARABLE_INTERNAL_USER.format(uid=external_user.id),
    )

    shared_with = client.assistants.list_shared_with(assistant.id).shared_with
    assert_that(
        shared_with, has_length(0), "no grant should be created for the external id"
    )


# ---------------------------------------------------------------------------
# TC_009: only the owner may share or revoke
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.api
@pytest.mark.parametrize(
    "actor_fixture",
    ["unrelated_client", "regular_client"],
    ids=["no_access_user", "granted_read_only_user"],
)
def test_non_owner_cannot_share_or_revoke(
    request, assistant_factory, client, regular_client, actor_fixture
):
    """@case share-an-assistant-with-selected_TC_009"""
    assistant = assistant_factory.create()
    grantee_id = regular_client.users.about_me().user_id
    client.assistants.share(assistant.id, [grantee_id])

    actor_client = request.getfixturevalue(actor_fixture)

    with pytest.raises(HTTPError) as exc_info:
        actor_client.assistants.share(assistant.id, [grantee_id])
    assert_response(exc_info.value.response, 403, OWNER_ONLY_MESSAGE)

    with pytest.raises(HTTPError) as exc_info:
        actor_client.assistants.revoke_share(assistant.id, [grantee_id])
    assert_response(exc_info.value.response, 403, OWNER_ONLY_MESSAGE)

    shared_with = client.assistants.list_shared_with(assistant.id).shared_with
    assert_that(
        [u.id for u in shared_with],
        has_item(grantee_id),
        "the shared-with list must be unchanged after both denied attempts",
    )


# ---------------------------------------------------------------------------
# TC_011: a per-user grant is findable under the recipient's personal project
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.api
def test_shared_assistant_findable_under_recipient_personal_project(
    assistant_factory, client, regular_client
):
    """@case share-an-assistant-with-selected_TC_011"""
    assistant = assistant_factory.create()  # lives in PROJECT, not B's personal project
    grantee = regular_client.users.about_me()

    client.assistants.share(assistant.id, [grantee.user_id])

    personal_project_view = regular_client.assistants.list(
        filters={"project": [grantee.email], "search": assistant.name}, per_page=200
    )
    assert_that(
        [a.id for a in personal_project_view],
        has_item(assistant.id),
        "the shared assistant should be findable under B's personal project filter",
    )


# ---------------------------------------------------------------------------
# TC_012: a project-wide share and a per-user grant coexist without conflict
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.api
@pytest.mark.not_for_parallel_run
def test_project_wide_share_and_named_grant_coexist(
    assistant_factory, client, regular_client, user_utils
):
    """@case share-an-assistant-with-selected_TC_012"""
    assistant = assistant_factory.create(shared=True)
    grantee = regular_client.users.about_me()
    # Idempotent: B may already be a member of PROJECT from unrelated environment
    # state, in which case the admin API 409s on a repeat add. Only add/remove what
    # this test itself puts in place.
    was_already_member = PROJECT in user_utils.get_user_project_names(grantee.user_id)
    if not was_already_member:
        user_utils.assign_user_to_project(grantee.user_id, PROJECT)
    try:
        client.assistants.share(assistant.id, [grantee.user_id])

        shared_with = client.assistants.list_shared_with(assistant.id).shared_with
        assert_that(
            [u.id for u in shared_with],
            has_item(grantee.user_id),
            "the named grant should be visible to the owner",
        )

        visible = regular_client.assistants.list(
            filters={"project": [PROJECT], "search": assistant.name}, per_page=200
        )
        assert_that(
            len(visible),
            equal_to(1),
            "the two access mechanisms must not produce duplicate/conflicting entries",
        )

        client.assistants.revoke_share(assistant.id, [grantee.user_id])

        shared_with_after_revoke = client.assistants.list_shared_with(
            assistant.id
        ).shared_with
        assert_that(
            [u.id for u in shared_with_after_revoke],
            is_not(has_item(grantee.user_id)),
            "the named grant should be gone after revoke",
        )

        still_visible = regular_client.assistants.list(
            filters={"project": [PROJECT], "search": assistant.name}, per_page=200
        )
        assert_that(
            [a.id for a in still_visible],
            has_item(assistant.id),
            "B should still see the assistant via the project-wide shared flag alone",
        )
    finally:
        if not was_already_member:
            user_utils.remove_user_from_project(grantee.user_id, PROJECT)


# ---------------------------------------------------------------------------
# TC_014: sharing is rejected when the assistant uses a personal integration
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.api
def test_sharing_rejected_when_assistant_uses_personal_integration(
    integration_utils, assistant_utils, client, regular_client
):
    """@case share-an-assistant-with-selected_TC_014"""
    personal_integration = integration_utils.create_integration(
        setting_type=IntegrationType.USER,
        credential_type=CredentialTypes.GIT,
        credential_values=CredentialsManager.gitlab_credentials(),
    )
    grantee_id = regular_client.users.about_me().user_id

    assistant = None
    try:
        assistant = assistant_utils.create_assistant(
            toolkits=[
                ToolKitDetails(
                    toolkit=Toolkit.GIT,
                    tools=[
                        ToolDetails(
                            name=GitTool.LIST_BRANCHES_IN_REPO,
                            settings=personal_integration,
                        )
                    ],
                )
            ],
        )

        with pytest.raises(HTTPError) as exc_info:
            client.assistants.share(assistant.id, [grantee_id])
        assert_response(exc_info.value.response, 400, PERSONAL_INTEGRATION_MESSAGE)

        shared_with = client.assistants.list_shared_with(assistant.id).shared_with
        assert_that(shared_with, has_length(0), "no grant should be created")
    finally:
        if assistant:
            assistant_utils.delete_assistant(assistant)
        integration_utils.delete_integration(personal_integration)


# ---------------------------------------------------------------------------
# TC_015: deleting a shared assistant leaves no dangling grant
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.api
def test_deleting_shared_assistant_leaves_no_dangling_grant(
    assistant_utils, client, regular_client
):
    """@case share-an-assistant-with-selected_TC_015"""
    assistant = assistant_utils.create_assistant()
    grantee_id = regular_client.users.about_me().user_id
    client.assistants.share(assistant.id, [grantee_id])

    assistant_utils.delete_assistant(assistant)

    remaining = regular_client.assistants.list(
        filters={"search": assistant.name}, per_page=200
    )
    assert_that(
        [a.id for a in remaining],
        is_not(has_item(assistant.id)),
        "the deleted assistant must not remain visible to the former recipient",
    )

    with pytest.raises(HTTPError) as exc_info:
        regular_client.assistants.get(assistant.id)
    assert_response(
        exc_info.value.response,
        404,
        f"No assistant found with the id '{assistant.id}'.",
    )


# ---------------------------------------------------------------------------
# TC_016: grant and revoke are written to the activity log
# ---------------------------------------------------------------------------


@pytest.mark.assistant
@pytest.mark.api
def test_grant_and_revoke_write_activity_log_events(
    assistant_factory, client, regular_client, maintainer_client
):
    """@case share-an-assistant-with-selected_TC_016"""
    assistant = assistant_factory.create()
    owner_id = client.users.about_me().user_id
    grantee_id = regular_client.users.about_me().user_id
    activity_utils = ActivityUtils(maintainer_client)

    client.assistants.share(assistant.id, [grantee_id])
    client.assistants.revoke_share(assistant.id, [grantee_id])

    granted_events = activity_utils.list_activity_events(
        entity_id=assistant.id,
        event_type=["assistant.grant.added"],
        domain=["assistant"],
    )
    assert_that(
        len(granted_events.data),
        greater_than_or_equal_to(1),
        "a GRANT_ADDED activity event should be recorded for the grant",
    )
    grant_record = granted_events.data[0]
    assert_that(grant_record.actor_id, equal_to(owner_id), "actor should be the owner")
    assert_that(
        grant_record.attributes.get("principal_id"),
        equal_to(grantee_id),
        "principal should be the granted user",
    )

    revoked_events = activity_utils.list_activity_events(
        entity_id=assistant.id,
        event_type=["assistant.grant.removed"],
        domain=["assistant"],
    )
    assert_that(
        len(revoked_events.data),
        greater_than_or_equal_to(1),
        "a GRANT_REMOVED activity event should be recorded for the revoke",
    )
    revoke_record = revoked_events.data[0]
    assert_that(revoke_record.actor_id, equal_to(owner_id), "actor should be the owner")
    assert_that(
        revoke_record.attributes.get("principal_id"),
        equal_to(grantee_id),
        "principal should be the revoked user",
    )
