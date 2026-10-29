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

from dataclasses import dataclass

from codemie_test_harness.tests.utils.base_utils import get_random_name


@dataclass
class AssistantPartialUpdateData:
    name: str
    temperature: float
    top_p: float


def build_assistant_with_optional_fields() -> AssistantPartialUpdateData:
    """Build test data for an assistant with truly-optional fields (temperature, top_p) set.

    description is a required field in AssistantRequestBase (SDK), so it cannot be omitted
    from an SDK update call. temperature and top_p are genuinely optional (None defaults in
    both SDK and backend), making them the correct fields for partial-update
    regression coverage.
    """
    return AssistantPartialUpdateData(
        name=get_random_name(),
        temperature=0.7,
        top_p=0.9,
    )
