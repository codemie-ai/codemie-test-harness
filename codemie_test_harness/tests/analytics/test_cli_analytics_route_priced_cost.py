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

"""CLI Analytics cost of requests Claude Code made through the LiteLLM proxy: a session
is priced by the LiteLLM deployment its requests ran on (the route the proxy reports in
``x-litellm-model-name``), the price LiteLLM charges for them, not by the price of the
model name the request asked for."""

import pytest
from codemie_sdk.models.llm import CostConfig
from hamcrest import assert_that, close_to, equal_to, greater_than, has_item

from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    COST_TOLERANCE,
    ROUTE_PRICED_CASES,
    get_route_priced_seeds,
    get_unpriced_route_seed,
    session_catalog_cost,
)


@pytest.fixture(scope="module")
def litellm_route_prices(lite_llm_budget_utils):
    """Price per token of every route the stand's LiteLLM serves at a single price."""
    prices = lite_llm_budget_utils.get_route_prices()
    if not prices:
        pytest.skip("LiteLLM serves no chat route at a single price")
    return prices


@pytest.fixture(scope="module")
def route_priced_sessions(seed_cli_sessions, litellm_route_prices):
    """Hooks-only sessions, keyed by case id, of the cases whose route LiteLLM serves at
    a single price, each with that price."""
    cases = [case for case in ROUTE_PRICED_CASES if case.route in litellm_route_prices]
    if not cases:
        pytest.skip("LiteLLM serves none of the routes of the cases")
    seeds = seed_cli_sessions(get_route_priced_seeds(cases))
    return {
        case.id: (
            seeds[case.id],
            CostConfig(
                input=litellm_route_prices[case.route][0],
                output=litellm_route_prices[case.route][1],
            ),
        )
        for case in cases
    }


@pytest.fixture
def route_priced_session(request, route_priced_sessions):
    """The seed and the LiteLLM price of the route of the (indirect) case."""
    case = request.param
    if case.id not in route_priced_sessions:
        pytest.skip(f"LiteLLM does not serve {case.route} at a single price")
    return route_priced_sessions[case.id]


@pytest.fixture(scope="module")
def unpriced_route_session(seed_cli_sessions):
    """A hooks-only session whose request ran on a route nothing prices."""
    seed = get_unpriced_route_seed()
    return seed_cli_sessions([seed])[seed.key]


@pytest.mark.cli_analytics
@pytest.mark.api
@pytest.mark.parametrize(
    "route_priced_session",
    [pytest.param(case, id=case.id) for case in ROUTE_PRICED_CASES],
    indirect=True,
)
def test_session_cost_is_its_tokens_priced_by_the_litellm_route_it_ran_on(
    analytics_utils, route_priced_session
):
    """The cost of a session whose requests ran on a LiteLLM route is its tokens at that
    route's deployment price, as LiteLLM charges it, whether the model name the request
    asked for is dated, has a Vertex or DIAL alias, or is priced at no single plain-name
    price (then the session must not show $0.00 or a price of another deployment)."""
    seed, route_price = route_priced_session
    session = analytics_utils.wait_for_cli_session(seed.session_id)
    assert_that(  # repro:precondition
        session.input_tokens,
        equal_to(seed.input_tokens),
        f"setup: session {seed.session_id} was not rolled up with its seeded tokens",
    )
    assert_that(  # repro:symptom
        session.cost_usd,
        close_to(session_catalog_cost(seed, route_price), COST_TOLERANCE),
        f"cost of session {seed.session_id} of {seed.model_raw} that ran on {seed.model}",
    )


@pytest.mark.cli_analytics
@pytest.mark.api
def test_session_on_route_without_price_is_reported_unpriced_by_its_model_name(
    analytics_utils, unpriced_route_session
):
    """A session whose request ran on a route nothing prices lists its model, by the
    plain name and not the route, among the session's unpriced models, instead of
    silently showing $0.00."""
    seed = unpriced_route_session
    session = analytics_utils.wait_for_cli_session(seed.session_id)
    assert_that(  # repro:precondition
        session.input_tokens,
        greater_than(0),
        f"setup: session {seed.session_id} was rolled up without tokens",
    )

    unpriced_models = analytics_utils.get_cli_session_unpriced_models(seed.session_id)
    assert_that(  # repro:symptom
        unpriced_models or [],
        has_item(seed.model_raw),
        f"unpriced models of the session that ran on {seed.model}: {unpriced_models!r}",
    )
