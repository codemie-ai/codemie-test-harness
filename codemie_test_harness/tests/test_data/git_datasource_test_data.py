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

"""Test data constants for GitHub Datasource tests"""

from codemie_test_harness.tests.utils.github_seed import SEED_FILE_NAME

GITHUB_DATASOURCE_REQUEST = "Get repository file tree"

# A plain string, not Seeded(...): test_code_datasource.py reads it directly at module
# scope. Tied to the GitHub seed file rather than the exact root listing.
GITHUB_DATASOURCE_RESPONSE = f"""
        'Repository file tree:

        - `{SEED_FILE_NAME}` (among possibly other files)'
    """
