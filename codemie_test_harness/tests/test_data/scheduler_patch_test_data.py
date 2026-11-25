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

"""Test data for the scheduler enable/disable (PATCH) tests."""

from codemie_sdk.models.integration import CredentialValues

from codemie_test_harness.tests.test_data.scheduler_list_test_data import (
    DAILY_SCHEDULE,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager


def enabled_scheduler_credential_values(
    assistant_id: str, prompt: str
) -> list[CredentialValues]:
    """Credentials of an enabled scheduler that targets the given assistant.

    The row starts enabled so a PATCH to ``isEnabled: false`` is a real change. The
    daily-midnight schedule does not fire during the few seconds a test holds it.
    """
    return [
        CredentialValues(key="url", value=CredentialsManager.AUTO_GENERATED),
        CredentialValues(key="is_enabled", value=True),
        CredentialValues(key="schedule", value=DAILY_SCHEDULE),
        CredentialValues(key="resource_type", value="assistant"),
        CredentialValues(key="resource_id", value=assistant_id),
        CredentialValues(key="prompt", value=prompt),
    ]
