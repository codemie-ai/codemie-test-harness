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

conversation_ids = []


TRIGGER_ACTIONS = [
    pytest.param(
        "cancel_button",
        lambda page: page.click_cancel(),
        id="cancel_button",
    ),
    pytest.param(
        "menu_navigation",
        lambda page: page.menu.navigate_to_integrations(),
        id="menu_navigation",
    ),
    pytest.param("back_button", lambda page: page.click_back(), id="back_button"),
]
