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

"""Test data for spend bucket distribution tests."""

from dataclasses import dataclass


@dataclass
class SpendBucketDistributionTestData:
    """Test data for project budget group distribution scenarios."""

    valid_categories: dict
    """Valid distribution that sums to 100%: platform required, sum within 0.5."""
    invalid_sum_categories: dict
    """Distribution whose pct values sum to more than 100.5%."""
    missing_platform_categories: dict
    """Distribution that lacks the mandatory 'platform' category."""
    negative_pct_categories: dict
    """Distribution containing a negative percentage value."""


def spend_bucket_distribution_test_data() -> SpendBucketDistributionTestData:
    """Return a populated SpendBucketDistributionTestData instance."""
    return SpendBucketDistributionTestData(
        valid_categories={"platform": 60.0, "cli": 40.0},
        invalid_sum_categories={"platform": 60.0, "cli": 50.0},  # total 110%
        missing_platform_categories={"cli": 100.0},
        negative_pct_categories={"platform": -10.0, "cli": 110.0},
    )
