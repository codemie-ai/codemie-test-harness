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

from codemie_test_harness.tests.test_data.provider_toolkit_test_data import (
    default_repositories_json,
    provider_payload_with_default_value,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


@pytest.fixture(scope="module")
def code_exploration_toolkit(providers_utils):
    """Create an isolated clone of the AICE provider with a `repositories`
    default pointing at the real GitLab project the suite already indexes
    — the backend rejects datasource creation without one ("Toolkit config
    must include repositories"), and the shared "AICE" provider itself has
    no such default configured.

    Cloned rather than used directly, like `isolated_provider`
    (tests/ui/datasource/conftest.py), so this module's datasource doesn't
    collide with any other test's use of the shared provider.
    """
    payload = providers_utils.provider_request_json()  # defaults to AICE
    payload["name"] = get_random_name()
    payload = provider_payload_with_default_value(
        payload, "repositories", default_repositories_json()
    )
    provider = providers_utils.send_post_request_to_providers_endpoint(payload).json()
    toolkit = next(
        t
        for t in provider["provided_toolkits"]
        if t["name"] == "CodeExplorationToolkit"
    )

    yield {"toolkit": toolkit, "provider_name": provider["name"]}

    # Best-effort: never let teardown mask a real assertion failure from the
    # module's own tests (mirrors `isolated_provider`, tests/ui/datasource/conftest.py).
    providers_utils.safe_delete_provider(provider["id"])


@pytest.fixture(scope="module")
def code_exploration_datasource(code_exploration_toolkit, datasource_utils):
    """Create and index a CodeExplorationToolkit datasource directly against the
    cloned AICE provider. The combined provider needs no separate datasource
    to reference — repository config lives on the provider's own
    `repositories` parameter.
    """
    toolkit_id = code_exploration_toolkit["toolkit"]["toolkit_id"]
    provider_name = code_exploration_toolkit["provider_name"]

    datasource = datasource_utils.create_code_exploration_datasource(
        toolkit_id=toolkit_id,
        provider_name=provider_name,
    )

    yield datasource

    # Best-effort: never let teardown mask a real assertion failure from the
    # module's own tests (mirrors `isolated_provider_datasource`, tests/ui/datasource/conftest.py).
    datasource_utils.safe_delete_datasource(datasource)
