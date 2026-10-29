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

import logging

import pytest

from codemie_test_harness.tests.test_data.provider_toolkit_test_data import (
    DEFAULT_GRAPHDB_PASSWORD_VALUE,
    DEFAULT_GRAPHDB_USERNAME_VALUE,
    default_repositories_json,
    provider_payload_with_default_value,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.constants import FILES_PATH
from codemie_test_harness.tests.utils.datasource_utils import DataSourceUtils

logger = logging.getLogger(__name__)

_MIN_DATASOURCES = 10
_TARGET_DATASOURCES = 11
_TXT_FILE = str(FILES_PATH / "test.txt")


@pytest.fixture
def enough_datasources():
    """Ensure at least _TARGET_DATASOURCES datasources exist before the test.

    If the current count is <= _MIN_DATASOURCES, creates file datasources using test.txt
    to reach _TARGET_DATASOURCES. All created datasources are deleted in teardown.
    """
    client = get_client()
    utils = DataSourceUtils(client)
    existing = client.datasources.list(per_page=200)
    created = []

    if len(existing) <= _MIN_DATASOURCES:
        needed = _TARGET_DATASOURCES - len(existing)
        for _ in range(needed):
            ds = utils.create_file_datasource(files=[_TXT_FILE])
            created.append(ds)

    yield

    for ds in created:
        try:
            utils.delete_datasource(ds)
        except Exception as e:
            logger.warning(f"Failed to delete datasource {ds}: {e}")


@pytest.fixture
def cleanup_file_datasources():
    """Track datasource names created during a test and delete them in teardown.

    UI-created datasources return only their name, so the entity is looked up to
    resolve its id. Best-effort — teardown never raises, so it cannot mask the
    test outcome. Append created names to the yielded list inside the test.
    """
    names = []

    yield names

    client = get_client()
    utils = DataSourceUtils(client)
    existing = {d.name: d for d in client.datasources.list(per_page=200)}
    for name in names:
        ds = existing.get(name)
        if ds is not None:
            try:
                utils.delete_datasource(ds)
            except Exception:
                pass


@pytest.fixture
def provider_with_default_values(providers_utils):
    """Create an isolated AICE-based provider with `default_value` configured on
    every one of its base parameters — repositories, graphdb_username,
    graphdb_password — so a Create Data Source form
    driven by this provider pre-populates all of them without typing.
    `create_datasource`'s own name/description arguments are required with no
    default_value concept, so they are never defaulted and are always filled
    separately via `fill_name`/`fill_description`.

    `repositories` points at the real GitLab project the suite already
    indexes (via CredentialsManager, never os.getenv), so the resulting Data
    Source can actually complete indexing.

    Yields the created provider's unique `name` (used to locate it in the
    dynamically-populated Datasource Type dropdown) and deletes the
    provider via the API in teardown.
    """
    payload = providers_utils.provider_request_json()
    payload["name"] = get_random_name()
    payload = provider_payload_with_default_value(
        payload, "repositories", default_repositories_json()
    )
    payload = provider_payload_with_default_value(
        payload, "graphdb_username", DEFAULT_GRAPHDB_USERNAME_VALUE
    )
    payload = provider_payload_with_default_value(
        payload, "graphdb_password", DEFAULT_GRAPHDB_PASSWORD_VALUE
    )

    create_response = providers_utils.send_post_request_to_providers_endpoint(payload)
    provider_id = create_response.json()["id"]
    provider_name = payload["name"]

    yield provider_name

    providers_utils.send_delete_provider_request(provider_id)


@pytest.fixture
def provider_datasource_without_default_password(providers_utils, datasource_utils):
    """Provider-based data source on its own isolated AICE provider whose
    `graphdb_password` (a credential field, masked in the UI) has no
    `default_value`, while `repositories` and `graphdb_username` do, so a
    cloned form can only show a password if the clone copied the source's
    secret. `repositories` points at the real GitLab project the suite
    already indexes, so the data source can actually complete indexing.
    Teardown deletes the data source first, then the provider.
    """
    payload = providers_utils.provider_request_json()
    payload = provider_payload_with_default_value(
        payload, "repositories", default_repositories_json()
    )
    payload = provider_payload_with_default_value(
        payload, "graphdb_username", DEFAULT_GRAPHDB_USERNAME_VALUE
    )
    payload = provider_payload_with_default_value(payload, "graphdb_password", None)

    provider = providers_utils.send_post_request_to_providers_endpoint(payload).json()
    provider_id = provider["id"]
    toolkit = next(
        t
        for t in provider["provided_toolkits"]
        if t["name"] == "CodeExplorationToolkit"
    )

    datasource = datasource_utils.create_code_exploration_datasource(
        toolkit_id=toolkit["toolkit_id"],
        provider_name=provider["name"],
    )

    yield datasource

    datasource_utils.safe_delete_datasource(datasource)
    providers_utils.safe_delete_provider(provider_id)


@pytest.fixture
def isolated_provider(providers_utils):
    """Create an isolated copy of the AICE provider so a test
    can change its parameter definition without touching the shared provider
    other tests use. The `repositories` parameter defaults to the GitLab
    project the suite already indexes, since the backend rejects a datasource
    without it ("Toolkit config must include repositories"). Yields the created
    provider's JSON (`id`, `name`, `provided_toolkits`) and deletes the provider
    via the API in teardown.
    """
    payload = providers_utils.provider_request_json()
    payload["name"] = get_random_name()
    payload = provider_payload_with_default_value(
        payload, "repositories", default_repositories_json()
    )

    create_response = providers_utils.send_post_request_to_providers_endpoint(payload)
    provider = create_response.json()

    yield provider

    providers_utils.safe_delete_provider(provider["id"])


@pytest.fixture
def isolated_provider_datasource(isolated_provider, datasource_utils):
    """Create and index a CodeExplorationToolkit datasource through
    `isolated_provider` via the API. The AICE provider needs no
    other datasources, so the datasource is created from name and description
    alone. Yields the indexed datasource and deletes it in
    teardown, before the provider is deleted.

    Indexing a fresh, previously-unindexed provider can take longer than the
    default poll window; `create_code_exploration_datasource` already waits up
    to 1200s for exactly this reason.
    """
    toolkit = next(
        t
        for t in isolated_provider["provided_toolkits"]
        if t["name"] == "CodeExplorationToolkit"
    )
    datasource = datasource_utils.create_code_exploration_datasource(
        toolkit_id=toolkit["toolkit_id"],
        provider_name=isolated_provider["name"],
    )

    yield datasource

    datasource_utils.safe_delete_datasource(datasource)


@pytest.fixture
def managed_integration(integration_utils):
    """Factory fixture for creating global integrations with safe teardown.

    Tracks every integration created via the returned factory callable and
    deletes them in teardown with try/except to tolerate double-deletes (the
    integration may be explicitly deleted inside the test body before teardown
    runs, which is part of some test scenarios).

    Usage::

        def test_something(page, managed_integration, integration_utils):
            integration = managed_integration(
                credential_type=CredentialTypes.CONFLUENCE,
                credentials=CredentialsManager.confluence_credentials(),
            )
            # ... test body ...
            integration_utils.delete_integration(integration)  # explicit mid-test delete
            # teardown safely ignores the double-delete
    """
    created = []

    def _factory(credential_type, credentials):
        integration = integration_utils.create_global_integration(
            credential_type=credential_type,
            credentials=credentials,
        )
        created.append(integration)
        return integration

    yield _factory

    for integration in created:
        try:
            integration_utils.delete_integration(integration)
        except Exception:
            pass
