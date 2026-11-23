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

from playwright.sync_api import Locator


def uploaded_icon_avatar(scope: Locator, icon_url: str) -> Locator:
    """Avatar image of an uploaded icon file inside ``scope``.

    The avatar resolves a stored icon token to ``/v1/files/<token>`` (Avatar, iconUrl.ts).
    The locator keys on that source only, not on the avatar's styling classes.
    """
    return scope.locator(f'img[src$="/v1/files/{icon_url}"]')
