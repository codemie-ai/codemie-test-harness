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

"""Test data for feedback authorization tests."""

from dataclasses import dataclass

from codemie_test_harness.tests.utils.base_utils import get_random_name


@dataclass
class FeedbackSeed:
    """The texts of one question, its answer and the comment left on the answer."""

    request: str
    response: str
    comments: str


def feedback_seed() -> FeedbackSeed:
    suffix = get_random_name()
    return FeedbackSeed(
        request=f"question {suffix}",
        response=f"answer {suffix}",
        comments=f"comment {suffix}",
    )


FEEDBACK_NOT_FOUND_MESSAGE = "Feedback not found"
ACCESS_DENIED_MESSAGE = "Access denied"
FEEDBACK_REMOVED_MESSAGE = "Specified feedback entry removed"
