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

import os
import random
import string
from pathlib import Path

from codemie_test_harness.cli.runner import resolve_tests_path_and_root
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.env_utils import load_env_file

_, root_dir = resolve_tests_path_and_root()
env_file_path = Path(root_dir) / ".env"

# Load initial .env file (or the local-stack template) before the constants below
load_env_file(env_file_path)

LANGFUSE_TRACES_ENABLED = (
    os.getenv("LANGFUSE_TRACES_ENABLED", "false").lower() == "true"
)

PROJECT = os.getenv("PROJECT_NAME", "codemie")
TEST_USER = os.getenv("TEST_USER_FULL_NAME", "AiRun Account")
GITHUB_URL = CredentialsManager.get_parameter("GITHUB_URL", "https://github.com")
VERIFY_SSL = os.getenv("VERIFY_SSL", "True").lower() == "true"
API_DOMAIN = os.getenv("CODEMIE_API_DOMAIN")

autotest_entity_prefix = (
    f"{''.join(random.choice(string.ascii_lowercase) for _ in range(3))}_"
)
