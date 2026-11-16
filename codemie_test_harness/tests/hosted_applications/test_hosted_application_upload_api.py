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

"""Hosted applications API: uploads and their validation, single-page bundles, personal limits
and deleting an application."""

import json

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    greater_than,
    has_items,
    is_,
    is_not,
    none,
)
from requests import HTTPError

from codemie_test_harness.tests.test_data.hosted_application_test_data import (
    CONFIGURATION_CONFLICT_CODE,
    CONTENT_UNAVAILABLE_BODY,
    HIDDEN_FROM_READER,
    INVALID_UPLOADS,
    PERSONAL_LIMITS,
    SPA_BUNDLES,
    SPA_CLIENT_ROUTE,
    SPA_MISSING_ASSET,
    html_artifact,
    secret_value,
    spa_artifact,
    two_root_zip,
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

CAPABILITY = "features:hostedApplications"


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.requires_setting("FRONTEND_URL")
@pytest.mark.parametrize("bundle", SPA_BUNDLES, ids=[item.id for item in SPA_BUNDLES])
@pytest.mark.hosted_applications
@pytest.mark.api
def test_spa_bundle_falls_back_to_entry_page_and_missing_asset_is_not_found(
    hosted_owner, bundle
):
    # @case hosted-applications-upload-share-view_TC_005
    artifact = spa_artifact(bundle)
    app = hosted_owner.apps.create_app(hosted_owner.personal_project)
    hosted_owner.apps.go_live(app.id, artifact, routing_mode="spa_history")
    session = HostedContentSession.open(hosted_owner.service, app.id)

    entry = session.page("/")
    client_route = session.page(SPA_CLIENT_ROUTE)
    missing = session.asset(SPA_MISSING_ASSET)

    assert_that(
        entry.text, contains_string(artifact.marker), "the entry page is served"
    )
    assert_that(client_route.status_code, equal_to(200), "a client route is answered")
    assert_that(
        client_route.text,
        equal_to(entry.text),
        "a client route gets the entry page",
    )
    assert_that(
        missing.status_code,
        equal_to(404),
        "a missing asset is not answered with the entry page",
    )
    assert_that(
        missing.content,
        equal_to(CONTENT_UNAVAILABLE_BODY),
        "the missing asset carries the unavailable answer only",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize(
    "upload", INVALID_UPLOADS, ids=[item.id for item in INVALID_UPLOADS]
)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_invalid_upload_is_rejected_with_its_code_and_nothing_goes_live(
    hosted_owner, upload
):
    # @case hosted-applications-upload-share-view_TC_006
    app = hosted_owner.apps.create_app(hosted_owner.personal_project)

    version = hosted_owner.apps.upload_version(app.id, upload.build())

    assert_that(
        version.validation_state, equal_to("rejected"), "the version is rejected"
    )
    assert_that(
        version.can_activate, is_(False), "a rejected version cannot be released"
    )
    report = hosted_owner.service.get_version_validation(app.id, version.id)
    assert_that(report.error_code, equal_to(upload.code), "the rejection code")
    assert_that(
        [item["code"] for item in report.errors],
        equal_to([upload.code]),
        "the report lists that one error",
    )
    assert_that(
        [item["message"] for item in report.errors][0],
        is_not(equal_to("")),
        "with guidance for the owner",
    )
    assert_that(
        json.dumps(report.model_dump()),
        is_not(contains_string(secret_value())),
        "the report never repeats a credential found in the upload",
    )
    after = hosted_owner.apps.get_app(app.id)
    assert_that(after.active_version_id, none(), "no live version was set")
    assert_that(after.has_active_version, is_(False), "the application is still draft")


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_stale_configuration_choice_is_refused(hosted_owner):
    # @case hosted-applications-upload-share-view_TC_008
    app = hosted_owner.apps.create_app(hosted_owner.personal_project)

    version = hosted_owner.apps.upload_version(app.id, two_root_zip())

    assert_that(
        version.validation_state,
        equal_to("awaiting_configuration"),
        "the version waits for the owner's choice",
    )
    assert_that(version.can_activate, is_(False), "it is not live")
    report = hosted_owner.service.get_version_validation(app.id, version.id)
    assert_that(report.roots, has_items("site-a", "site-b"), "both roots are offered")

    with pytest.raises(HTTPError) as stale:
        hosted_owner.service.configure_version(
            app.id,
            version.id,
            "site-elsewhere",
            "site-elsewhere/index.html",
            "static",
            report.candidate_manifest_digest,
            report.configuration_revision,
            version.etag,
        )

    assert_that(error_status(stale.value), equal_to(409), "the choice conflicts")
    assert_that(
        error_code(stale.value),
        equal_to(CONFIGURATION_CONFLICT_CODE),
        "the choice is not among the detected options",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_valid_configuration_choice_makes_the_version_ready(hosted_owner):
    # @case hosted-applications-upload-share-view_TC_008
    app = hosted_owner.apps.create_app(hosted_owner.personal_project)
    version = hosted_owner.apps.upload_version(app.id, two_root_zip())
    report = hosted_owner.service.get_version_validation(app.id, version.id)
    root = "site-a"
    entry = [path for path in report.entries if path.startswith(f"{root}/")][0]

    queued = hosted_owner.service.configure_version(
        app.id,
        version.id,
        root,
        entry,
        "static",
        report.candidate_manifest_digest,
        report.configuration_revision,
        hosted_owner.service.get_version(app.id, version.id).etag,
    )

    assert_that(queued.state, equal_to("queued"), "the choice is accepted for checking")
    settled = hosted_owner.apps.wait_for_version(app.id, version.id)
    assert_that(settled.validation_state, equal_to("accepted"), "the version is ready")
    assert_that(settled.can_activate, is_(True), "and can be released")


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.parametrize(
    "limit", PERSONAL_LIMITS, ids=[item.id for item in PERSONAL_LIMITS]
)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_personal_limit_refuses_the_next_one_and_stores_nothing(hosted_owner, limit):
    # @case hosted-applications-upload-share-view_TC_014
    ask_for_one_more = getattr(hosted_owner.apps, limit.reach)(
        hosted_owner.personal_project
    )
    ids_before = hosted_owner.apps.all_app_ids()
    usage_before = hosted_owner.service.usage()

    with pytest.raises(HTTPError) as refused:
        ask_for_one_more()

    assert_that(error_status(refused.value), equal_to(409), "the limit conflicts")
    assert_that(error_code(refused.value), equal_to(limit.code), "the limit's code")
    assert_that(
        error_message(refused.value),
        contains_string(limit.message_part),
        "the message names the limit",
    )
    usage_after = hosted_owner.service.usage()
    assert_that(
        hosted_owner.apps.all_app_ids(),
        equal_to(ids_before),
        "the list of applications is unchanged",
    )
    assert_that(
        usage_after.reserved_bytes,
        equal_to(usage_before.reserved_bytes),
        "no storage was reserved for the refused request",
    )
    assert_that(
        usage_after.stored_bytes,
        equal_to(usage_before.stored_bytes),
        "and none was stored",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_deleting_an_application_purges_its_files_and_refunds_the_bytes(hosted_owner):
    # @case hosted-applications-upload-share-view_TC_019
    baseline = hosted_owner.service.usage()
    app = hosted_owner.apps.create_app(hosted_owner.personal_project)
    hosted_owner.apps.go_live(app.id, html_artifact())
    assert_that(
        hosted_owner.service.usage().stored_bytes,
        greater_than(baseline.stored_bytes),
        "the upload is stored against the quota",
    )

    deletion = hosted_owner.apps.delete_app(app.id)

    assert_that(deletion.state, equal_to("purging"), "the purge is queued")
    status = hosted_owner.apps.wait_until_purged(app.id)
    assert_that(status.state, equal_to("purged"), "the purge ends")
    assert_that(status.remaining_prefixes, equal_to(0), "no stored files remain")
    refunded = poll_until(
        hosted_owner.service.usage,
        lambda usage: usage.stored_bytes == baseline.stored_bytes,
        timeout=60,
        interval=2.0,
    )
    assert_that(
        refunded.stored_bytes,
        equal_to(baseline.stored_bytes),
        "the stored bytes are back to the starting value",
    )
    with pytest.raises(HTTPError) as gone:
        hosted_owner.service.get_application(app.id)
    assert_that(
        error_status(gone.value),
        equal_to(HIDDEN_FROM_READER),
        "the application is gone",
    )
