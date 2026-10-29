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

"""
API tests: timezone parameter in Scheduler integration cron expression.

AC covered:
  AC-1  User can specify a timezone when creating a Scheduler integration (verified via credential_values)
  AC-2  Selected timezone is saved together with the cron configuration
  AC-3  Scheduled execution uses the selected timezone (slow / live-execution test, S-08)
  AC-6  Timezone support does not break existing scheduler creation flows
  AC-7  Validation prevents saving invalid or unsupported timezone values

Scenarios: S-01, S-04, S-05, S-06, S-07, S-08
"""

import pytest
from datetime import datetime, timedelta

from hamcrest import assert_that, equal_to
from requests import HTTPError
from tzlocal import get_localzone

from codemie_sdk.models.integration import IntegrationType
from codemie_test_harness.tests.utils.base_utils import get_random_name, wait_for_entity
from codemie_test_harness.tests.utils.env_resolver import EnvironmentResolver

pytestmark = pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Scheduler is disabled on sandbox environments",
)

VALID_TIMEZONES = ["Europe/Warsaw", "Asia/Tokyo", "UTC", "America/New_York"]
INVALID_TIMEZONES = ["UTC+2", "UTC-5", "Fake/Zone", ""]


@pytest.mark.scheduler
@pytest.mark.api
@pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Scheduler is disabled on sandbox environments",
)
class TestSchedulerTimezoneCreate:
    """S-01, S-04, S-07: timezone is persisted when provided and backward compat holds."""

    def test_create_scheduler_integration_with_valid_iana_timezone(
        self, assistant, scheduler_integration
    ):
        """S-01: Create with timezone='Europe/Warsaw'; assert credential_values contain the timezone.

        AC: AC-1, AC-2
        """
        # Arrange
        resource_assistant = assistant()
        alias = get_random_name()
        timezone = "Europe/Warsaw"

        # Act
        integration = scheduler_integration(
            alias=alias,
            resource_type="assistant",
            resource_id=resource_assistant.id,
            timezone=timezone,
        )

        # Assert
        tz_value = next(
            (cv.value for cv in integration.credential_values if cv.key == "timezone"),
            None,
        )
        assert_that(str(tz_value), equal_to(timezone))

    def test_create_scheduler_integration_without_timezone_backward_compat(
        self, assistant, scheduler_integration
    ):
        """S-04: Create without timezone; assert integration created and no timezone credential stored.

        AC: AC-6
        """
        # Arrange
        resource_assistant = assistant()
        alias = get_random_name()
        cron_schedule = "0 12 * * *"

        # Act
        integration = scheduler_integration(
            alias=alias,
            resource_type="assistant",
            resource_id=resource_assistant.id,
            schedule=cron_schedule,
        )

        # Assert — integration was created
        assert integration is not None

        # Assert — schedule credential was saved
        schedule_value = next(
            (cv.value for cv in integration.credential_values if cv.key == "schedule"),
            None,
        )
        assert_that(str(schedule_value), equal_to(cron_schedule))

        # Assert — no timezone key added (backward compat)
        tz_entry = next(
            (cv for cv in integration.credential_values if cv.key == "timezone"),
            None,
        )
        assert tz_entry is None

    @pytest.mark.parametrize("timezone", VALID_TIMEZONES)
    def test_create_scheduler_integration_with_multiple_valid_timezones(
        self, assistant, scheduler_integration, timezone
    ):
        """S-07: Parametrized — POST with each valid IANA zone; assert saved correctly.

        AC: AC-1, AC-2
        """
        # Arrange
        resource_assistant = assistant()
        alias = get_random_name()

        # Act
        integration = scheduler_integration(
            alias=alias,
            resource_type="assistant",
            resource_id=resource_assistant.id,
            timezone=timezone,
        )

        # Assert
        tz_value = next(
            (cv.value for cv in integration.credential_values if cv.key == "timezone"),
            None,
        )
        assert_that(str(tz_value), equal_to(timezone))


@pytest.mark.scheduler
@pytest.mark.api
@pytest.mark.not_for_parallel_run
@pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Scheduler is disabled on sandbox environments",
)
class TestSchedulerTimezoneUpdate:
    """S-05: Update timezone on an existing integration and verify it persists.

    Marked not_for_parallel_run because it modifies shared integration state.
    AC: AC-2
    """

    def test_update_scheduler_integration_timezone(
        self, assistant, scheduler_integration, integration_utils
    ):
        """S-05: Create with timezone='UTC'; update to 'Europe/London'; re-fetch and verify.

        AC: AC-2
        """
        # Arrange
        resource_assistant = assistant()
        alias = get_random_name()

        integration = scheduler_integration(
            alias=alias,
            resource_type="assistant",
            resource_id=resource_assistant.id,
            timezone="UTC",
        )

        # Verify initial timezone
        initial_tz = next(
            (cv.value for cv in integration.credential_values if cv.key == "timezone"),
            None,
        )
        assert_that(str(initial_tz), equal_to("UTC"))

        # Act — update timezone to Europe/London
        updated_credential_values = [
            cv.model_copy(update={"value": "Europe/London"})
            if cv.key == "timezone"
            else cv
            for cv in integration.credential_values
        ]
        update_request = integration.model_copy(
            update={"credential_values": updated_credential_values}
        )
        integration_utils.update_integration(update_request)

        # Assert — re-fetch and verify persisted timezone
        updated_integration = integration_utils.get_integration_by_alias(
            alias, IntegrationType.PROJECT
        )
        updated_tz = next(
            (
                cv.value
                for cv in updated_integration.credential_values
                if cv.key == "timezone"
            ),
            None,
        )
        assert_that(str(updated_tz), equal_to("Europe/London"))


@pytest.mark.scheduler
@pytest.mark.api
@pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Scheduler is disabled on sandbox environments",
)
class TestSchedulerTimezoneValidation:
    """S-06: Invalid timezone formats are rejected with HTTP 422.

    AC: AC-7
    """

    @pytest.mark.parametrize("invalid_tz", INVALID_TIMEZONES)
    def test_create_scheduler_with_invalid_timezone_rejected(
        self, assistant, scheduler_integration, invalid_tz
    ):
        """S-06: POST with invalid timezone; assert HTTP 422 with 'Invalid timezone' message.

        AC: AC-7
        """
        # Arrange
        resource_assistant = assistant()
        alias = get_random_name()

        # Act & Assert
        with pytest.raises(HTTPError) as exc_info:
            scheduler_integration(
                alias=alias,
                resource_type="assistant",
                resource_id=resource_assistant.id,
                timezone=invalid_tz,
            )

        assert_that(exc_info.value.response.status_code, equal_to(422))
        assert_that(
            exc_info.value.response.json()["error"]["message"],
            equal_to("Invalid timezone"),
        )


@pytest.mark.scheduler
@pytest.mark.api
@pytest.mark.slow
@pytest.mark.skipif(
    EnvironmentResolver.is_sandbox(),
    reason="Scheduler is disabled on sandbox environments",
)
class TestSchedulerTimezoneExecution:
    """S-08: Scheduler fires at timezone-adjusted time.

    Creates a cron for now+2min in the local machine timezone and polls for
    a resulting conversation within 120 s.

    AC: AC-3
    """

    def test_scheduler_fires_at_timezone_adjusted_time(
        self, assistant, scheduler_integration, conversation_utils
    ):
        """S-08: Scheduler with local machine timezone fires and produces a conversation.

        AC: AC-3
        """
        # Arrange — use machine timezone so the cron fires within the test window
        resource_assistant = assistant()
        alias = get_random_name()
        local_tz = str(get_localzone())
        next_minute = (datetime.now() + timedelta(minutes=2)).minute
        schedule = f"{next_minute} * * * *"

        # Act
        scheduler_integration(
            alias=alias,
            resource_type="assistant",
            resource_id=resource_assistant.id,
            schedule=schedule,
            timezone=local_tz,
            is_enabled=True,
        )

        # Assert — conversation appears within 120 s (scheduler fired)
        conversation = wait_for_entity(
            lambda: conversation_utils.list_conversations(),
            entity_name=f"Scheduler: {resource_assistant.id}",
            timeout=120,
        )

        assert_that(conversation.name, equal_to(f"Scheduler: {resource_assistant.id}"))
        assert_that(conversation.initial_assistant_id, equal_to(resource_assistant.id))
