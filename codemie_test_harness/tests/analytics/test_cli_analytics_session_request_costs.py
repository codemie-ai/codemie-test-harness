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

"""CLI Analytics Session Detail request costs: each listed request is priced with all
of its tokens at its model's catalog rates, so the requests add up to the session cost
(the figure the "Token & cost growth" line ends on)."""

import pytest
from hamcrest import (
    assert_that,
    close_to,
    empty,
    equal_to,
    has_entries,
    has_length,
    instance_of,
    is_,
    not_,
)

from codemie_test_harness.tests.test_data.cli_analytics_request_costs_test_data import (
    BEDROCK_ID_FORMS,
    DATED_CLAUDE_MODEL,
    get_bedrock_id_seed,
    get_hooks_only_requests_seed,
    get_one_hour_cache_write_seed,
)
from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    COST_TOLERANCE,
    CatalogRates,
    CliSessionSeed,
    cache_priced_model,
    session_catalog_cost,
)


@pytest.fixture(scope="module")
def dated_cache_cost_model(llm_catalog) -> tuple[str, CatalogRates]:
    """A Claude model with a dated catalog name, priced for every token kind: the
    model a Bedrock-style id names."""
    model = cache_priced_model(llm_catalog, DATED_CLAUDE_MODEL)
    if model is None:
        pytest.skip("no dated Claude model in the catalog prices every token kind")
    return model


def _requests(data: dict) -> list[dict]:
    """The API requests Session Detail lists for the session."""
    return [event for event in data["events"] if event["event_type"] == "api_request"]


def _session_detail(analytics_utils, seed: CliSessionSeed) -> dict:
    """The session detail body once its listed requests hold all of the seed's input
    tokens: the rollup has the session's requests."""
    detail = analytics_utils.wait_for_cli_session_detail(
        seed.session_id,
        lambda d: sum(e["input_tokens"] or 0 for e in _requests(d["data"]))
        >= seed.input_tokens,
    )
    assert_that(  # repro:precondition
        detail,
        instance_of(dict),
        f"setup: session {seed.session_id} was never rolled up",
    )
    return detail


def _assert_requests_add_up(data: dict, money: float, what: str) -> None:
    """The session costs ``money`` and its listed requests add up to it."""
    assert_that(  # repro:symptom
        data["cost_usd"],
        close_to(money, COST_TOLERANCE),
        f"{what}: session cost, its tokens at the catalog rates",
    )
    assert_that(  # repro:symptom
        sum(event["cost_usd"] or 0 for event in _requests(data)),
        close_to(data["cost_usd"], COST_TOLERANCE),
        f"{what}: the listed requests' costs add up to the session cost",
    )


@pytest.mark.cli_analytics
@pytest.mark.api
def test_hooks_only_requests_are_priced_with_their_cache_writes(
    analytics_utils, seed_cli_sessions, cache_cost_model
):
    """Requests reported by hooks only (no OTel record) are each listed with their
    cache writes and priced with them, so they add up to the session cost."""
    model, rates = cache_cost_model
    seed = get_hooks_only_requests_seed(model)
    seed_cli_sessions([seed])

    data = _session_detail(analytics_utils, seed)["data"]
    requests = _requests(data)
    assert_that(  # repro:precondition
        requests,
        has_length(seed.requests),
        f"setup: requests listed for the {seed.requests} hooks-only requests",
    )
    assert_that(  # repro:symptom
        [event["cache_creation_tokens"] for event in requests],
        equal_to([seed.cache_creation_tokens // seed.requests] * seed.requests),
        "cache-write tokens of each hooks-only request",
    )
    _assert_requests_add_up(
        data, session_catalog_cost(seed, rates), "hooks-only session"
    )


@pytest.mark.cli_analytics
@pytest.mark.api
def test_one_hour_cache_writes_of_a_request_are_priced_at_the_one_hour_rate(
    analytics_utils, seed_cli_sessions, cache_cost_model
):
    """A request whose OTel record gives its cache writes as one total, while the CLI's
    usage row of the same request says they are one-hour writes, is priced at the
    one-hour rate, the rate of the session cost, not at the five-minute rate."""
    model, rates = cache_cost_model
    assert_that(  # repro:precondition
        rates.cache_write_1h,
        not_(equal_to(rates.cache_write)),
        f"setup: {model} prices five-minute and one-hour cache writes alike",
    )
    seed = get_one_hour_cache_write_seed(model)
    seed_cli_sessions([seed])

    data = _session_detail(analytics_utils, seed)["data"]
    requests = _requests(data)
    assert_that(  # repro:symptom
        [(event["input_tokens"], event["cache_creation_tokens"]) for event in requests],
        equal_to([(seed.input_tokens, seed.cache_creation_1h_tokens)]),
        "the request reported by OTel and the CLI is listed once, with its cache writes",
    )
    _assert_requests_add_up(
        data, session_catalog_cost(seed, rates), "session with one-hour cache writes"
    )


@pytest.mark.cli_analytics
@pytest.mark.api
@pytest.mark.parametrize("form", list(BEDROCK_ID_FORMS))
def test_bedrock_model_id_is_priced_as_its_catalog_model(
    analytics_utils, seed_cli_sessions, dated_cache_cost_model, form
):
    """A request reported under a Bedrock-style model id is shown and priced as the
    catalog model the id names: its cache reads cost money and the model is not
    reported as unpriced."""
    model, rates = dated_cache_cost_model
    seed = get_bedrock_id_seed(model, form)
    seed_cli_sessions([seed])

    detail = _session_detail(analytics_utils, seed)
    data = detail["data"]
    assert_that(  # repro:symptom
        data,
        has_entries(
            model_name=model,
            cost_available=True,
            unpriced_models=is_(empty()),
        ),
        f"session of {seed.model}: shown as {model}, priced",
    )
    assert_that(  # repro:symptom
        data["cache_read_cost_usd"],
        close_to(seed.cache_read_tokens * rates.cache_read, COST_TOLERANCE),
        f"cache-read cost of the session of {seed.model}",
    )
    assert_that(  # repro:symptom
        detail["metadata"]["unpriced_models"],
        is_(empty()),
        "unpriced models of the session detail",
    )
    _assert_requests_add_up(
        data, session_catalog_cost(seed, rates), f"session of {seed.model}"
    )
