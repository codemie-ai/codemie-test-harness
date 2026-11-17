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

"""Test data for the hosted application UI tests."""

# What the probe page of the sandbox test writes when nothing escapes: one line per attempt, in
# the order the page makes them. The report is compared with whitespace normalised.
PROBE_REPORT_LINES = (
    "parent=blocked",
    "top=blocked",
    "cookie=none",
    "foreign_storage=none",
    "management_api=blocked",
)
PROBE_REPORT = " ".join(PROBE_REPORT_LINES)
# What the page that keeps a value in its own storage says once it has done so.
HOLDER_WRITTEN_TEXT = "storage written"
# The probe page reaches the management API of the stand by this route.
MANAGEMENT_ROUTE = "/v1/hosted-applications/capabilities"
