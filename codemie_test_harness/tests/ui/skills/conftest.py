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


"""Shared fixtures for skills UI tests."""

import logging

import pytest
from codemie_sdk.models.skill import SkillVisibility

from codemie_test_harness.tests.ui.pageobject.login_page import LoginPage
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.skill_utils import SkillsUtils

logger = logging.getLogger(__name__)


@pytest.fixture
def favorites_user(platform_user):
    """A fresh user of its own, so the favorites in its preferences are private to the test.

    Requesting this fixture makes ``login`` below sign in as this user instead of the
    default one. The user is created by ``platform_user`` and deleted after the test.
    """
    return platform_user


@pytest.fixture(autouse=True)
def login(request, page):
    """Override tests/ui/conftest.py login.

    A test that requests ``favorites_user`` signs in as that user; every other test of
    this package signs in as the default AUTH_USERNAME user, exactly as before.
    """
    if "favorites_user" in request.fixturenames:
        user = request.getfixturevalue("favorites_user")
        username, password, user_id = user.email, user.password, user.user_id
    else:
        username = CredentialsManager.get_parameter("AUTH_USERNAME")
        password = CredentialsManager.get_parameter("AUTH_PASSWORD")
        user_id = get_client().users.about_me().user_id
    LoginPage(page).login_suppressing_popups(
        username,
        password,
        user_id,
        CredentialsManager.get_parameter("FRONTEND_URL", ""),
    )


@pytest.fixture
def skill_to_favorite(favorites_user):
    """A private skill created and owned by ``favorites_user``, in that user's personal project.

    A private skill is visible only to its owner, so it belongs unambiguously to the
    user's own Skills list (it shows under both the 'All' and the 'Private' visibility
    filters) whatever scope the default view applies. Teardown deletes it through the
    user's client; the favorite lives in the user's preferences and goes with the user.
    """
    skill_utils = SkillsUtils(favorites_user.client)
    created_skill = skill_utils.create_skill(
        project_name=favorites_user.email, visibility=SkillVisibility.PRIVATE
    )
    yield created_skill
    try:
        skill_utils.delete_skill(created_skill)
    except Exception as e:
        logger.warning(f"Failed to delete skill {created_skill.id}: {e}")
