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

import re

from playwright.sync_api import Locator


def metric_label(root: Locator, label: str) -> Locator:
    """Label paragraph of a metric card inside ``root``, matched by exact text."""
    return root.locator("p").filter(has_text=re.compile(rf"^{re.escape(label)}$")).first


def metric_value(root: Locator, label: str) -> Locator:
    """Value paragraph of a metric card inside ``root``."""
    return metric_label(root, label).locator("xpath=../following-sibling::p[1]")


def metric_description(root: Locator, label: str) -> Locator:
    """Optional description paragraph of a metric card inside ``root``."""
    return metric_label(root, label).locator("xpath=../following-sibling::p[2]")
