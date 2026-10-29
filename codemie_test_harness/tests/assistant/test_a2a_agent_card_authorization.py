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

"""API tests for A2A agent-card endpoint authorization.

Verifies GET /v1/a2a/assistants/{assistant_id}/.well-known/agent-card.json enforces
Ability(user).can(Action.READ, assistant) for private/project assistants, while
intentionally public (global/marketplace) assistants remain discoverable by any
authenticated caller regardless of READ grant.
"""

import uuid

import pytest
from hamcrest import assert_that, ends_with, equal_to, greater_than, has_length
from requests import HTTPError

from codemie_test_harness.tests.utils.base_utils import (
    assert_error_details,
    assert_response,
)

PERMISSION_DENIED_DETAILS = "You don't have permission to access this assistant."


@pytest.mark.assistant
@pytest.mark.api
def test_owner_can_retrieve_agent_card_for_private_assistant(assistant_factory, client):
    """TC-01: The owner of a private (non-shared, non-global) assistant can
    retrieve its agent card and the card content matches the assistant."""
    created = assistant_factory.create()

    card = client.a2a.get_agent_card(created.id)

    assert_that(
        card.name,
        equal_to(created.name),
        "Agent card name doesn't match the assistant.",
    )
    assert_that(
        card.description,
        equal_to(created.description),
        "Agent card description doesn't match the assistant.",
    )
    assert_that(
        card.skills,
        has_length(greater_than(0)),
        "Agent card must expose at least one skill.",
    )
    assert_that(
        card.protocol_version,
        equal_to("1.0"),
        "Agent card must advertise A2A protocol version 1.0.",
    )
    assert_that(
        card.supportedInterfaces[0].url,
        ends_with(f"/v1/a2a/assistants/{created.id}"),
        "Agent card interface URL doesn't point to the assistant.",
    )
    assert_that(
        card.capabilities.streaming,
        equal_to(True),
        "Agent card must advertise streaming support.",
    )


@pytest.mark.assistant
@pytest.mark.api
def test_user_without_read_access_denied_for_private_assistant(
    assistant_factory, regular_client
):
    """TC-02: A caller with no READ grant on a private assistant gets 403 and
    no assistant metadata is returned — the regression this ticket fixes."""
    created = assistant_factory.create()  # shared=False by default, owned by `client`

    with pytest.raises(HTTPError) as exc_info:
        regular_client.a2a.get_agent_card(created.id)

    assert_error_details(exc_info.value.response, 403, PERMISSION_DENIED_DETAILS)


@pytest.mark.assistant
@pytest.mark.api
def test_missing_assistant_returns_404(client):
    """TC-03: Requesting the agent card for a non-existent assistant id
    returns 404 regardless of the caller's authentication."""
    missing_id = str(uuid.uuid4())

    with pytest.raises(HTTPError) as exc_info:
        client.a2a.get_agent_card(missing_id)

    assert_response(
        exc_info.value.response,
        404,
        f"Assistant with id {missing_id} wasn't found",
    )


@pytest.mark.assistant
@pytest.mark.marketplace
@pytest.mark.api
def test_global_marketplace_assistant_accessible_without_read_grant(
    assistant_utils, regular_client
):
    """TC-04: A caller with no READ grant can still retrieve the agent card
    for an intentionally public (global/marketplace) assistant — the explicit
    exemption the fix carves out so A2A discovery keeps working."""
    marketplace_assistant = assistant_utils.get_assistant_by_name(
        "AI/Run FAQ", scope="marketplace"
    )

    card = regular_client.a2a.get_agent_card(marketplace_assistant.id)

    assert_that(
        card.name,
        equal_to(marketplace_assistant.name),
        "Agent card name doesn't match the global assistant.",
    )
