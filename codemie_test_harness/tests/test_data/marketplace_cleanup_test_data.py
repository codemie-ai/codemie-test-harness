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

"""Test data for the marketplace Cleanup list tests."""

# Creator the Cleanup table used to show for every assistant whose author it could not resolve.
SYSTEM_CREATOR = "System"

# Top-level keys of the Cleanup response.
CLEANUP_RESPONSE_KEYS = frozenset({"total", "page", "page_size", "items"})

# Keys of every Cleanup row; a row with no value carries the key with an explicit null.
CLEANUP_ITEM_KEYS = frozenset(
    {
        "id",
        "name",
        "creator",
        "categories",
        "unique_users_count",
        "unique_likes_count",
        "usage_tier",
        "bucket",
        "bucket_reason",
        "verdict_kind",
        "cleanup_reason",
        "canonical_id",
        "canonical_name",
        "canonical_users",
        "critical_count",
        "optional_count",
        "detail",
        "top_similar",
    }
)
