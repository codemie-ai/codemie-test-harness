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

"""UI-only fixtures for the auditor role test package.

Overrides the `login` fixture from tests/ui/conftest.py so that every UI test
under tests/ui/auditor/ authenticates as the auditor user instead of the
regular user.
"""

import pytest

from codemie_test_harness.tests.ui.pageobject.login_page import LoginPage
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


@pytest.fixture(autouse=True)
def login(page):
    """Override tests/ui/conftest.py login — authenticate as the auditor user."""
    login_page = LoginPage(page)
    username = CredentialsManager.get_parameter("AUDITOR_USERNAME")
    password = CredentialsManager.get_parameter("AUDITOR_PASSWORD")
    user = get_client(username=username, password=password).users.about_me()
    frontend_url = CredentialsManager.get_parameter("FRONTEND_URL", "")
    login_page.login_suppressing_popups(username, password, user.user_id, frontend_url)
