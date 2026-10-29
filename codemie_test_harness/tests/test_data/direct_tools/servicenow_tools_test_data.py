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

"""Test data for ServiceNow direct tools tests."""

from codemie_test_harness.tests.utils.servicenow_seed import SEED_SHORT_DESCRIPTION

PROMPT = {
    "method": "GET",
    "table": "incident",
    "params": f'{{"sysparm_query":"short_description={SEED_SHORT_DESCRIPTION}^ORDERBYsys_created_on","sysparm_limit":"1"}}',
}
