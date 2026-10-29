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

"""Test data constants for workflow evaluation endpoint tests."""

import uuid

from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

# Real Langfuse dataset ID available in the test environment.
# Override via LANGFUSE_DATASET_ID in Parameter Store / .env.
# The hardcoded fallback is the ID from the feature MR; it may not exist in every
# environment — tests that depend on a valid dataset use LANGFUSE_DATASET_CONFIGURED
# to skip gracefully when the ID is absent.
_langfuse_dataset_id: str | None = CredentialsManager.get_parameter(
    "LANGFUSE_DATASET_ID", None
)
VALID_DATASET_ID: str = _langfuse_dataset_id or "autotests_dataset"
LANGFUSE_DATASET_CONFIGURED: bool = _langfuse_dataset_id is not None

# Dataset ID that cannot be resolved in Langfuse
INVALID_DATASET_ID: str = "nonexistent-dataset-abc123xyz"

# Unique experiment name for this test session
VALID_EXPERIMENT_NAME: str = get_random_name()

# Random UUID that will not match any workflow in the system
NONEXISTENT_WORKFLOW_ID: str = str(uuid.uuid4())

# max_concurrency boundary values (valid range: [1, 5])
MAX_CONCURRENCY_MIN: int = 1
MAX_CONCURRENCY_MAX: int = 5
MAX_CONCURRENCY_ABOVE_MAX: int = 6
MAX_CONCURRENCY_BELOW_MIN: int = 0
