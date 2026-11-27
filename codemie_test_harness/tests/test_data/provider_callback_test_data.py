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

import pytest

PROVIDER_CALLBACK_COMPLETED_PAYLOAD = {"status": "Completed"}

# Header values the provider callback must reject. `None` omits the
# X-Callback-OTP header altogether, "" sends it empty.
provider_callback_rejected_otp_test_data = [
    pytest.param(None, id="header_missing"),
    pytest.param("", id="header_empty"),
    pytest.param("not-the-one-time-password", id="header_wrong"),
]
