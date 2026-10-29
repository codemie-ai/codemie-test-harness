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

"""Test data for project budget chargeback UI tests."""

from dataclasses import dataclass

from codemie_test_harness.tests.utils.base_utils import get_random_name


@dataclass
class ProjectBudgetChargebackData:
    """Holds random names used across chargeback budget test scenarios."""

    project_name: str
    cost_center_name: str


def make_project_budget_chargeback_data() -> ProjectBudgetChargebackData:
    """Return a fresh set of random, unique names for one test scenario."""
    return ProjectBudgetChargebackData(
        project_name=get_random_name(),
        cost_center_name=get_random_name(),
    )
