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

"""Test data for the 'Your personal spending' panel UI tests."""

# The panel draws a table only for two or more rows, so the project budget group spans two
# categories: percentages of the group total, as the budget group distribution endpoint takes them.
TWO_CATEGORY_DISTRIBUTION = {"platform": 50.0, "cli": 50.0}

# Column that the table hides by design; the API still returns it.
HIDDEN_COLUMN_ID = "budget_limit"

# Real chat spend is a few cents, which the table rounds to 0.0% of a 50 dollar budget. The
# category that receives the spend gets a one dollar budget instead. The
# requests carry the CLI client header, which routes them to the cli key once the project has one.
SPENT_CATEGORY = "cli"
