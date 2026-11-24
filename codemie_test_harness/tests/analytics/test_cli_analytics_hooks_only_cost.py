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

"""CLI Analytics cost of sessions whose requests come from hooks only (no OTel cost
record): priced from tokens and the model's catalog price, or reported as unpriced."""

import pytest
from hamcrest import assert_that, close_to, equal_to, greater_than, has_item

from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    COST_TOLERANCE,
    CatalogRates,
    cache_priced_model,
    get_hooks_only_cost_seeds,
    get_unpriced_model_seed,
    session_catalog_cost,
)
from codemie_test_harness.tests.utils.cli_analytics_api_utils import CliAnalyticsApi


@pytest.fixture(scope="module")
def cache_cost_model(client) -> tuple[str, CatalogRates]:
    """A model the stand's catalog prices for every token kind, cache writes of both
    durations included, with its rates. The SDK's model list drops the cache rates,
    so the catalog is read raw."""
    response = CliAnalyticsApi(client).request("GET", "/v1/llm_models")
    assert_that(response.status_code, equal_to(200), response.text[:300])
    model = cache_priced_model(response.json())
    if model is None:
        pytest.skip("no LLM in the catalog prices input, output and every cache kind")
    return model


@pytest.fixture(scope="module")
def hooks_only_priced_sessions(seed_cli_sessions, cache_cost_model):
    """Two users' hooks-only sessions of a model priced for every token kind."""
    model_name, _ = cache_cost_model
    return list(seed_cli_sessions(get_hooks_only_cost_seeds(model_name)).values())


@pytest.fixture(scope="module")
def hooks_only_unpriced_session(seed_cli_sessions):
    """A hooks-only session of a model the catalog has no price for."""
    seed = get_unpriced_model_seed()
    return seed_cli_sessions([seed])[seed.key]


@pytest.mark.cli_analytics
@pytest.mark.api
def test_hooks_only_session_cost_is_its_tokens_priced_at_catalog(
    analytics_utils, cache_cost_model, hooks_only_priced_sessions
):
    """A session whose requests came from hooks only is priced from its tokens at the
    model's catalog price, not shown as $0.00: input and output, cache reads, and
    five-minute and one-hour cache writes each at their own rate."""
    model_name, rates = cache_cost_model
    for seed in hooks_only_priced_sessions:
        session = analytics_utils.wait_for_cli_session(seed.session_id)
        assert_that(  # repro:precondition
            session.input_tokens,
            greater_than(0),
            f"setup: hooks-only session {seed.session_id} was rolled up without tokens",
        )
        assert_that(  # repro:symptom
            session.cost_usd,
            close_to(session_catalog_cost(seed, rates), COST_TOLERANCE),
            f"cost of hooks-only session {seed.session_id} of {model_name}",
        )


@pytest.mark.cli_analytics
@pytest.mark.api
def test_hooks_only_session_of_model_without_price_is_reported_unpriced(
    analytics_utils, hooks_only_unpriced_session
):
    """A hooks-only session of a model the catalog has no price for lists that model
    among the session's unpriced models, instead of silently showing $0.00."""
    seed = hooks_only_unpriced_session
    session = analytics_utils.wait_for_cli_session(seed.session_id)
    assert_that(  # repro:precondition
        session.input_tokens,
        greater_than(0),
        f"setup: hooks-only session {seed.session_id} was rolled up without tokens",
    )

    unpriced_models = analytics_utils.get_cli_session_unpriced_models(seed.session_id)
    assert_that(  # repro:symptom
        unpriced_models or [],
        has_item(seed.model),
        f"unpriced models of the session of {seed.model}: {unpriced_models!r}",
    )
