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

"""Test data for the Cost center filter of the Projects Management UI tests."""

# A term no cost center name can contain: it has to match nothing for the empty-search state.
NO_MATCH_SEARCH_TERM = "zzq-no-such-cost-center"


def distinctive_fragment(cost_center_name: str) -> str:
    """Part of a generated cost center name ('<letters>-<letters>') that no other
    generated name shares: the random part after the separator."""
    return cost_center_name.split("-", 1)[1]
