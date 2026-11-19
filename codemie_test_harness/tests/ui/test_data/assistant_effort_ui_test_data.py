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

"""Models and values for the assistant effort UI tests."""

# Display labels in the model catalog of the stand.
EFFORT_MODEL_LABEL = "Bedrock Claude Sonnet 4.6"
NON_EFFORT_MODEL_LABEL = "GPT-4.1 2025-04-14"

# Temperature saved on an assistant before it is opened in the edit form.
SAVED_TEMPERATURE = 0.7
SAVED_TEMPERATURE_TEXT = "0.7"

# An effort level every effort model declares, chosen to clear the saved temperature.
CLEARING_EFFORT = "low"
# Effort levels below and at the one that shows the token-usage warning.
EFFORT_WITHOUT_WARNING = "high"
EFFORT_WITH_WARNING = "max"

# Above the 0-1 cap of Claude models.
OVER_CAP_TEMPERATURE = "1.5"
