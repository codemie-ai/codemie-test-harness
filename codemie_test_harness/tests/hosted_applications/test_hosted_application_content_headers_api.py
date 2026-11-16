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

"""Hosted applications API: the security headers every content response carries, and what the
content host does with a top-level document request."""

from urllib.parse import urlparse

import pytest
from hamcrest import all_of, assert_that, contains_string, equal_to, is_not

from codemie_test_harness.tests.test_data.hosted_application_test_data import (
    CONTENT_REQUESTS,
    CSP_DIRECTIVES,
    DENIED_FEATURES,
    FIXED_CONTENT_HEADERS,
    FULLSCREEN_DELEGATION,
)
from codemie_test_harness.tests.utils.hosted_content_utils import (
    HostedContentSession,
    ui_origin,
)

CAPABILITY = "features:hostedApplications"


@pytest.fixture
def content_session(hosted_live_app, hosted_owner):
    """A viewing session of the owner on the live version, with the application and its artifact."""
    app, artifact = hosted_live_app
    return HostedContentSession.open(hosted_owner.service, app.id), artifact


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.requires_setting("FRONTEND_URL")
@pytest.mark.parametrize(
    "content_request", CONTENT_REQUESTS, ids=[item.id for item in CONTENT_REQUESTS]
)
@pytest.mark.hosted_applications
@pytest.mark.api
def test_content_responses_carry_the_server_owned_security_headers(
    content_session, content_request
):
    # @case hosted-applications-upload-share-view_TC_017
    session, _ = content_session

    response = session.request(
        content_request.path, content_request.method, page=content_request.page
    )

    assert_that(
        response.status_code,
        equal_to(content_request.status),
        f"the {content_request.id} gets its status",
    )
    csp = response.headers["Content-Security-Policy"]
    assert_that(
        csp,
        all_of(*[contains_string(item) for item in CSP_DIRECTIVES]),
        "the policy denies everything by default and bounds the page",
    )
    assert_that(csp, is_not(contains_string("unsafe-eval")), "no dynamic evaluation")
    assert_that(
        csp,
        contains_string(ui_origin()),
        "only the CodeMie web application may frame the content",
    )
    assert_that(
        csp,
        is_not(contains_string("frame-ancestors 'none'")),
        "the web application is allowed to frame it",
    )
    features = response.headers["Permissions-Policy"]
    assert_that(
        features,
        all_of(*[contains_string(item) for item in DENIED_FEATURES]),
        "powerful features are denied",
    )
    assert_that(
        features,
        contains_string(FULLSCREEN_DELEGATION),
        "full screen is allowed on the content's own origin",
    )
    assert_that(
        {name: response.headers.get(name) for name in FIXED_CONTENT_HEADERS},
        equal_to(FIXED_CONTENT_HEADERS),
        "the isolation headers are fixed",
    )


@pytest.mark.requires_capability(CAPABILITY)
@pytest.mark.requires_setting("FRONTEND_URL")
@pytest.mark.hosted_applications
@pytest.mark.api
def test_top_level_document_request_is_handed_to_the_viewer_origin(content_session):
    # @case hosted-applications-upload-share-view_TC_017
    session, artifact = content_session

    response = session.document_navigation("/")

    assert_that(
        response.status_code, equal_to(303), "the document request is redirected"
    )
    target = urlparse(response.headers["Location"])
    assert_that(
        target.netloc,
        is_not(equal_to(urlparse(session.origin).netloc)),
        "to a different origin than the content's own",
    )
    assert_that(target.path, equal_to("/"), "for the page that was asked for")
    assert_that(
        response.text,
        is_not(contains_string(artifact.marker)),
        "the redirect carries no bytes of the application",
    )
