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

"""UI fixtures for the marketplace management tests.

`login` is overridden so a test can choose who the browser logs in as through the
`acting_credentials` fixture (indirect parametrization): the default harness user
(an admin) or the `submitter`, the plain user who owns the assistants under review.
"""

import os

import pytest

from codemie_test_harness.tests.ui.pageobject.login_page import LoginPage
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


@pytest.fixture
def acting_credentials(request, marketplace_core_gates):
    """(username, password[, user id]) the browser logs in with; admin unless parametrized.

    Depends on `marketplace_core_gates`, so the gate thresholds are set before any UI
    test creates or edits an assistant.
    """
    role = getattr(request, "param", "admin")
    if role == "submitter":
        submitter = request.getfixturevalue("marketplace_submitter")
        return submitter.email, submitter.password, submitter.user_id
    return (
        CredentialsManager.get_parameter("AUTH_USERNAME"),
        CredentialsManager.get_parameter("AUTH_PASSWORD"),
    )


@pytest.fixture(autouse=True)
def login(page, acting_credentials):
    """Override tests/ui/conftest.py login: authenticate as the requested role."""
    username, password, *known_user_id = acting_credentials
    user_id = (
        known_user_id[0]
        if known_user_id
        else get_client(username=username, password=password).users.about_me().user_id
    )
    LoginPage(page).login_suppressing_popups(
        username, password, user_id, os.getenv("FRONTEND_URL", "")
    )
