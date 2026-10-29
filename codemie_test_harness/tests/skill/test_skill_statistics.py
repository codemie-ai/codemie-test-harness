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

"""Tests for Skills Statistics API (event log and aggregated stats)."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from hamcrest import (
    assert_that,
    equal_to,
    greater_than_or_equal_to,
    instance_of,
    not_none,
)
from requests.exceptions import HTTPError

from codemie_sdk.models.skill import SkillEventRequest
from codemie_test_harness.tests.test_data.skill_test_data import unique_slug


@pytest.fixture
def seed_event(skill_utils):
    def _seed(command: str, slug: str, agent: str = "test-agent") -> str:
        skill_utils.record_event(
            SkillEventRequest(
                session_id=str(uuid4()),
                command=command,
                status="completed",
                skill_slug=slug,
                target_agents=[agent],
            )
        )
        return slug

    return _seed


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.skill
@pytest.mark.api
def test_events_log_returns_list_response(skill_utils):
    response = skill_utils.get_events()

    assert_that(response, instance_of(list))


@pytest.mark.skill
@pytest.mark.api
def test_events_log_new_event_appears(skill_utils, seed_event):
    slug = unique_slug()
    t0 = datetime.now(timezone.utc).isoformat()
    seed_event("add", slug)

    events = skill_utils.get_events(from_=t0)
    event = skill_utils.find_event(events, slug, command="add")

    assert_that(event, not_none())


@pytest.mark.skill
@pytest.mark.api
def test_events_log_date_filter(skill_utils, seed_event):
    slug = unique_slug()
    t0 = datetime.now(timezone.utc).isoformat()
    seed_event("add", slug)
    t1 = datetime.now(timezone.utc).isoformat()

    t1_with_buffer = (datetime.fromisoformat(t1) + timedelta(seconds=5)).isoformat()
    events_in_range = skill_utils.get_events(from_=t0, to=t1_with_buffer)
    event_found = skill_utils.find_event(events_in_range, slug)
    assert_that(event_found, not_none())

    events_before = skill_utils.get_events(to=t0)
    event_not_found = skill_utils.find_event(events_before, slug)
    assert_that(event_not_found, equal_to(None))


@pytest.mark.skill
@pytest.mark.api
def test_events_log_excludes_non_add_remove_commands(skill_utils, seed_event):
    slug = unique_slug()
    t0 = datetime.now(timezone.utc).isoformat()
    seed_event("list", slug)

    events = skill_utils.get_events(from_=t0)
    event = skill_utils.find_event(events, slug)

    assert_that(event, equal_to(None))


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.skill
@pytest.mark.api
def test_events_stats_returns_list_response(skill_utils):
    response = skill_utils.get_events_stats()

    assert_that(response, instance_of(list))


@pytest.mark.skill
@pytest.mark.api
def test_events_stats_increments_on_add(skill_utils, seed_event):
    slug = unique_slug()
    t0 = datetime.now(timezone.utc).isoformat()

    seed_event("add", slug)

    stats = skill_utils.get_events_stats(from_=t0)
    item = skill_utils.find_in_events_stats(stats, slug)

    assert_that(item, not_none())
    assert_that(item.installs, greater_than_or_equal_to(1))


@pytest.mark.skill
@pytest.mark.api
def test_events_stats_increments_on_remove(skill_utils, seed_event):
    slug = unique_slug()
    t0 = datetime.now(timezone.utc).isoformat()

    seed_event("remove", slug)

    stats = skill_utils.get_events_stats(from_=t0)
    item = skill_utils.find_in_events_stats(stats, slug)

    assert_that(item, not_none())
    assert_that(item.removals, greater_than_or_equal_to(1))


@pytest.mark.skill
@pytest.mark.api
def test_single_skill_stats_increments_on_add(skill_utils, seed_event):
    slug = unique_slug()

    seed_event("add", slug)
    stats = skill_utils.get_skill_stats(slug)

    assert_that(stats.installs, greater_than_or_equal_to(1))


@pytest.mark.skill
@pytest.mark.api
def test_single_skill_stats_returns_404_for_unknown(skill_utils):
    slug = "nonexistent-skill-" + str(uuid4())[:8]

    with pytest.raises(HTTPError) as exc_info:
        skill_utils.get_skill_stats(slug)
    assert_that(exc_info.value.response.status_code, equal_to(404))
