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

"""Fixtures for the hosted application UI tests.

Every application is created through the SDK as the primary test account (the account
tests/ui/conftest.py logs the browser in as) and deleted on teardown.
"""

import pytest

from codemie_test_harness.tests.utils.hosted_application_utils import (
    HostedApplicationUtils,
    HostedVersionState,
)
from codemie_test_harness.tests.utils.logger_util import setup_logger

logger = setup_logger(__name__)


@pytest.fixture
def hosted_application_utils(client):
    """Hosted application helper bound to the primary test account."""
    return HostedApplicationUtils(client)


@pytest.fixture
def hosted_app(hosted_application_utils):
    """Factory: create an application owned by the test account in a given version state.

    Usage:
        app = hosted_app(HostedVersionState.ACTIVE)

    Every application the factory created is deleted on teardown.
    """
    created_ids = []

    def _create(state: HostedVersionState):
        application = hosted_application_utils.create_application()
        created_ids.append(application.id)
        return hosted_application_utils.bring_to_state(application.id, state)

    yield _create

    for app_id in created_ids:
        try:
            hosted_application_utils.delete_application(app_id)
        except Exception as e:
            logger.warning(f"Failed to delete hosted application {app_id}: {e}")
