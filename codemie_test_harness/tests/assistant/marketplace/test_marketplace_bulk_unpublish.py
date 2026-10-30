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

"""API tests for marketplace bulk unpublish.

``POST /v1/marketplace-management/entities/assistants/bulk-unpublish`` attempts
every id independently and answers 200 ``{unpublished, failed:[{entity_id,
reason}]}``; an empty id list is rejected with 422.
"""

import pytest
from hamcrest import all_of, assert_that, contains_string, equal_to, has_length

from codemie_test_harness.tests.test_data.marketplace_test_data import (
    COMPLETE_VALID_CONFIG,
    get_publishable_assistant_config,
    get_unknown_assistant_id,
)


@pytest.fixture(scope="function")
def published_assistants(assistant_factory, assistant_utils):
    """Two publishable assistants (content that clears the CRITICAL publish
    gates) published to the marketplace; cleaned up after the test."""
    assistants = [
        assistant_factory.create(**get_publishable_assistant_config()) for _ in range(2)
    ]
    for created in assistants:
        assistant_utils.publish_assistant_to_marketplace(
            created.id,
            categories=COMPLETE_VALID_CONFIG["categories"],
            ignore_recommendations=True,
        )
    yield assistants
    for created in assistants:
        try:
            assistant_utils.unpublish_assistant_from_marketplace(created.id)
        except Exception:
            pass


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_bulk_unpublish_withdraws_valid_assistants_and_reports_unknown_id(
    published_assistants, assistant_utils, marketplace_management_utils
):
    """Two published ids plus one unknown id: 2 unpublished, the unknown id is
    listed in failed with a reason, and the two leave the marketplace."""
    published_ids = [a.id for a in published_assistants]
    unknown_id = get_unknown_assistant_id()

    listed_before = {
        a.id for a in assistant_utils.get_all_assistants(scope="marketplace")
    }
    assert_that(
        set(published_ids) & listed_before,
        equal_to(set(published_ids)),
        "both assistants must be listed in the marketplace before the bulk call",
    )

    response = marketplace_management_utils.bulk_unpublish([*published_ids, unknown_id])

    assert_that(response.status_code, equal_to(200), response.text)
    body = response.json()
    assert_that(
        body["unpublished"],
        equal_to(2),
        "both published assistants must be reported as unpublished",
    )
    assert_that(body["failed"], has_length(1), "only the unknown id must fail")
    assert_that(
        body["failed"][0]["entity_id"],
        equal_to(unknown_id),
        "the failure must name the unknown id",
    )
    # Reason text comes from queue_service.decide: ValueError(f"Assistant
    # {assistant_id!r} not found"), passed through str(exc) by the endpoint.
    assert_that(
        body["failed"][0]["reason"],
        all_of(contains_string("not found"), contains_string(unknown_id)),
        "the failure must carry the not-found reason for the unknown id",
    )

    marketplace_ids = [
        a.id for a in assistant_utils.get_all_assistants(scope="marketplace")
    ]
    assert_that(
        set(published_ids) & set(marketplace_ids),
        equal_to(set()),
        "unpublished assistants must no longer be in the marketplace",
    )


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_bulk_unpublish_rejects_empty_entity_ids(marketplace_management_utils):
    """An empty entity_ids list violates min_length=1 and is rejected with 422."""
    response = marketplace_management_utils.bulk_unpublish([])

    assert_that(
        response.status_code,
        equal_to(422),
        "empty entity_ids must be rejected with 422",
    )
