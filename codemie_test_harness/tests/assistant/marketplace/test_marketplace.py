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

import json

import pytest
from codemie_sdk.models.assistant import ReactionType
from hamcrest import (
    assert_that,
    equal_to,
    is_in,
    has_key,
    contains_string,
    has_item,
    greater_than,
    any_of,
)

from codemie_test_harness.tests.test_data.marketplace_test_data import (
    VALIDATION_TEST_CONFIGS,
    COMPLETE_VALID_CONFIG,
    COMPLETE_CATEGORIES,
)


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_marketplace_publish_with_valid_data(assistant, assistant_utils):
    """Test validating and publishing an assistant with all valid data without ignore_recommendations."""
    # Create assistant with complete valid configuration
    created_assistant = assistant(**COMPLETE_VALID_CONFIG)

    # Validate assistant for marketplace
    validation_response = assistant_utils.validate_assistant_for_marketplace(
        created_assistant.id
    )

    # Assert validation response structure
    assert_that(validation_response, has_key("message"))
    assert_that(
        validation_response.get("message"),
        contains_string(
            f"Assistant {created_assistant.id} is ready to be published to marketplace"
        ),
    )

    # After successful validation, publish to marketplace WITHOUT ignore_recommendations
    publish_response = assistant_utils.publish_assistant_to_marketplace(
        created_assistant.id,
        categories=COMPLETE_VALID_CONFIG["categories"],
    )

    # Assert publish response
    assert_that(publish_response, has_key("message"))
    assert_that(
        publish_response.get("message"),
        contains_string(
            f"Assistant {created_assistant.id} published to marketplace successfully"
        ),
    )

    # Verify assistant appears in marketplace
    marketplace_assistants = assistant_utils.get_all_assistants(scope="marketplace")
    marketplace_assistant_ids = [asst.id for asst in marketplace_assistants]

    assert_that(
        created_assistant.id,
        is_in(marketplace_assistant_ids),
        "Published assistant should appear in marketplace",
    )


@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_marketplace_publish_with_invalid_data(assistant, assistant_utils):
    """Test that publishing a basic assistant without validation fails."""
    # Create basic assistant without proper marketplace requirements
    created_assistant = assistant()

    # Attempt to publish without validation should fail
    with pytest.raises(Exception) as exec_info:
        assistant_utils.publish_assistant_to_marketplace(
            created_assistant.id,
            categories=[COMPLETE_CATEGORIES],
        )

    # Verify response contains quality validation rejection
    response_data = json.loads(exec_info.value.response.content)
    assert_that(exec_info.value.response.status_code, equal_to(422))
    assert_that(
        response_data["error"]["message"],
        equal_to(
            "Assistant quality validation failed. Please improve the assistant before publishing."
        ),
    )


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_marketplace_publish_ignore_recommendations(assistant, assistant_utils):
    """Test publishing assistant to marketplace by ignoring validation recommendations."""
    # Create basic assistant without proper marketplace requirements
    created_assistant = assistant()

    # Publish directly with ignore_recommendations=True and categories
    publish_response = assistant_utils.publish_assistant_to_marketplace(
        created_assistant.id,
        categories=["quality-assurance"],
        ignore_recommendations=True,
    )

    # Assert publish response
    assert_that(publish_response, has_key("message"))
    assert_that(
        publish_response.get("message"),
        contains_string(
            f"Assistant {created_assistant.id} published to marketplace successfully"
        ),
    )

    # Verify assistant appears in marketplace
    marketplace_assistants = assistant_utils.get_all_assistants(scope="marketplace")
    marketplace_assistant_ids = [asst.id for asst in marketplace_assistants]

    assert_that(
        created_assistant.id,
        is_in(marketplace_assistant_ids),
        "Published assistant should appear in marketplace",
    )


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_marketplace_unpublish(assistant, assistant_utils):
    """Test unpublishing an assistant from marketplace."""
    # Create and publish assistant first
    created_assistant = assistant()

    # Publish with ignore_recommendations to bypass validation
    assistant_utils.publish_assistant_to_marketplace(
        created_assistant.id,
        categories=["quality-assurance"],
        ignore_recommendations=True,
    )

    # Verify it's in marketplace
    marketplace_assistants = assistant_utils.get_all_assistants(scope="marketplace")
    marketplace_assistant_ids = [asst.id for asst in marketplace_assistants]
    assert_that(
        created_assistant.id,
        is_in(marketplace_assistant_ids),
        "Assistant should be in marketplace before unpublishing",
    )

    # Unpublish from marketplace
    unpublish_response = assistant_utils.unpublish_assistant_from_marketplace(
        created_assistant.id
    )

    # Assert unpublish response
    assert_that(unpublish_response, has_key("message"))
    assert_that(
        unpublish_response.get("message"),
        contains_string(
            f"Assistant {created_assistant.id} unpublished from marketplace successfully"
        ),
    )

    # Verify assistant no longer appears in marketplace
    marketplace_assistants_after = assistant_utils.get_all_assistants(
        scope="marketplace"
    )
    marketplace_assistant_ids_after = [asst.id for asst in marketplace_assistants_after]

    assert_that(
        created_assistant.id not in marketplace_assistant_ids_after,
        "Unpublished assistant should not appear in marketplace",
    )


def _make_test_params():
    """Generate pytest.param objects from VALIDATION_TEST_CONFIGS, applying skip marks if needed."""
    params = []
    for tc in VALIDATION_TEST_CONFIGS:
        marks = []
        if "skip" in tc:
            marks.append(pytest.mark.skip(reason=tc["skip"]))
        params.append(pytest.param(tc, id=tc["id"], marks=marks))
    return params


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
@pytest.mark.parametrize(
    "test_case",
    [pytest.param(tc, id=tc["id"]) for tc in VALIDATION_TEST_CONFIGS],
)
def test_marketplace_validation_fields_recommendation(
    assistant, assistant_utils, test_case
):
    """Test validation recommendations for different field configurations."""
    config = test_case["config"]
    expected_issues = test_case["expected_issues"]

    # Create assistant with specific configuration
    created_assistant = assistant(**config)

    # Attempt to publish without ignore_recommendations should fail with validation errors
    publish_categories = test_case["config"].get("categories") or [COMPLETE_CATEGORIES]
    with pytest.raises(Exception) as exec_info:
        assistant_utils.publish_assistant_to_marketplace(
            created_assistant.id,
            categories=publish_categories,
        )

    # Extract validation response from error
    response_data = json.loads(exec_info.value.response.content)
    assert_that(exec_info.value.response.status_code, equal_to(422))

    # Check if response has quality_validation in error.details
    assert_that(response_data, has_key("error"))
    error = response_data["error"]
    assert_that(error, has_key("details"))
    details = error["details"]
    assert_that(details, has_key("quality_validation"))

    quality_validation = details["quality_validation"]

    # Validation returned recommendations (rejected)
    assert_that(
        quality_validation["decision"],
        equal_to("reject"),
        f"Expected validation to reject assistant with issues in {expected_issues}",
    )

    # Check that recommendations structure exists
    assert_that(quality_validation, has_key("recommendations"))
    recommendations = quality_validation["recommendations"]
    assert_that(recommendations, has_key("fields"))

    # Get all field recommendations
    field_recommendations = recommendations["fields"]

    # Verify there are recommendations provided
    assert_that(
        len(field_recommendations),
        greater_than(0),
        "Validation should provide field recommendations",
    )

    # Extract field names from recommendations
    recommended_field_names = [field["name"] for field in field_recommendations]

    # Assert that all expected fields are in the recommendations
    for expected_field in expected_issues:
        assert_that(
            recommended_field_names,
            has_item(expected_field),
            f"Expected field '{expected_field}' to be flagged in validation recommendations",
        )

        # Find the specific field recommendation
        field_rec = next(
            (f for f in field_recommendations if f["name"] == expected_field), None
        )

        if field_rec:
            # Assert field recommendation has required keys
            assert_that(field_rec, has_key("action"))
            assert_that(field_rec, has_key("severity"))
            assert_that(field_rec, has_key("reason"))
            assert_that(field_rec, has_key("recommended"))

            # Assert action is valid
            assert_that(
                field_rec["action"],
                any_of(equal_to("change"), equal_to("add"), equal_to("remove")),
                f"Action should be 'change', 'add', or 'remove' for field {expected_field}",
            )

            # Assert severity is valid
            assert_that(
                field_rec["severity"],
                any_of(equal_to("critical"), equal_to("optional"), equal_to("warning")),
                f"Severity should be 'critical', 'optional', or 'warning' for field {expected_field}",
            )

            # Assert reason is not empty
            assert_that(
                len(field_rec["reason"]),
                greater_than(10),
                f"Reason should be descriptive for field {expected_field}",
            )

            # Assert recommended value is not empty for change actions
            if field_rec["action"] == "change":
                assert_that(
                    len(str(field_rec["recommended"])),
                    greater_than(0),
                    f"Recommended value should be provided for field {expected_field}",
                )


@pytest.mark.smoke
@pytest.mark.sanity
@pytest.mark.marketplace
@pytest.mark.assistant
@pytest.mark.api
def test_reaction_marketplace_assistant(assistant, assistant_utils):
    """Test reaction for like/dislike assistant on marketplace."""
    # Create basic assistant without proper marketplace requirements
    created_assistant = assistant()

    # Publish directly with ignore_recommendations=True and categories
    publish_response = assistant_utils.publish_assistant_to_marketplace(
        created_assistant.id,
        categories=["quality-assurance"],
        ignore_recommendations=True,
    )

    # Assert publish response
    assert_that(publish_response, has_key("message"))
    assert_that(
        publish_response.get("message"),
        contains_string(
            f"Assistant {created_assistant.id} published to marketplace successfully"
        ),
    )

    # Verify assistant appears in marketplace and get initial counts
    marketplace_assistant = assistant_utils.get_assistant_by_name(
        created_assistant.name, scope="marketplace"
    )

    assert_that(
        marketplace_assistant.id,
        equal_to(created_assistant.id),
        "Published assistant should appear in marketplace",
    )

    # Initial counts should be 0 or None
    initial_likes = marketplace_assistant.unique_likes_count or 0
    initial_dislikes = marketplace_assistant.unique_dislikes_count or 0

    # React with "like"
    assistant_utils.react_to_assistant(created_assistant.id, ReactionType.LIKE)

    # Get assistant after like reaction
    assistant_after_like = assistant_utils.get_assistant_by_name(
        created_assistant.name, scope="marketplace"
    )

    # Verify like count increased
    assert_that(
        assistant_after_like.unique_likes_count,
        equal_to(initial_likes + 1),
        "Like count should increase by 1 after liking",
    )
    assert_that(
        assistant_after_like.unique_dislikes_count or 0,
        equal_to(initial_dislikes),
        "Dislike count should remain unchanged after liking",
    )

    # React with "dislike" (should remove like and add dislike for same user)
    assistant_utils.react_to_assistant(created_assistant.id, ReactionType.DISLIKE)

    # Get assistant after dislike reaction
    assistant_after_dislike = assistant_utils.get_assistant_by_name(
        created_assistant.name, scope="marketplace"
    )

    # Verify dislike count increased and like count decreased (same user changed reaction)
    assert_that(
        assistant_after_dislike.unique_dislikes_count,
        equal_to(initial_dislikes + 1),
        "Dislike count should increase by 1 after disliking",
    )
    assert_that(
        assistant_after_dislike.unique_likes_count or 0,
        equal_to(initial_likes),
        "Like count should decrease back to initial after same user changes to dislike",
    )
    assert_that(
        assistant_after_dislike.unique_users_count,
        equal_to(assistant_after_like.unique_users_count),
        "Unique users count should remain same when same user changes reaction",
    )
