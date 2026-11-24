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

"""CLI Analytics Sessions list: the page, its order, search and filters stay correct.

The list pages, sorts, searches and filters in the database. These tests pin what the
caller sees: the response structure, the sessions on every page and the total, the order
of the three sorts (start, cost, context per call), search, the filters and their
combinations, and that a row agrees with the session detail and with the totals.
"""

import pytest
from hamcrest import (
    all_of,
    assert_that,
    close_to,
    contains_exactly,
    empty,
    equal_to,
    greater_than_or_equal_to,
    has_item,
    is_,
    less_than,
)

from codemie_test_harness.tests.test_data.cli_analytics_test_data import (
    COST_TOLERANCE,
    EFFICIENCY_PATH,
    PURE_CHAT_LABEL,
    SEED_MODEL,
    SESSION_DETAIL_FIELDS,
    SESSION_LIST_FILTER_CASES,
    SESSION_LIST_INVALID_PARAMS,
    SESSION_LIST_KEYS,
    SESSION_LIST_PAGE_CASES,
    SESSION_LIST_SEARCH_CASES,
    SESSION_METADATA_TYPES,
    SESSION_ROW_TYPES,
    SESSIONS_DEFAULT_PER_PAGE,
    SESSIONS_MAX_PER_PAGE,
    SESSIONS_PATH,
    SORT_BY_COST,
    SORT_BY_CTX_PER_CALL,
    SORT_BY_START_TIME,
    SUPERPOWERS_LABEL,
    context_per_call,
    day_window,
    get_context_session_seeds,
    get_early_session_seeds,
    get_new_session_seed,
    get_paging_boundary_seeds,
    get_session_list_seeds,
    sorted_session_ids,
)
from codemie_test_harness.tests.utils.cli_analytics_api_utils import CliAnalyticsApi

SORT_PAGE_SIZE = 3


@pytest.fixture(scope="module")
def sessions_api(analytics_utils):
    """Raw reads of the Sessions list: the SDK model has no sort, search, framework or
    branch parameter, and its row drops the context per call."""
    return CliAnalyticsApi(analytics_utils.client)


@pytest.fixture(scope="module")
def priced_model_name(catalog_priced_model):
    return catalog_priced_model.base_name if catalog_priced_model else SEED_MODEL


@pytest.fixture(scope="module")
def list_seeds(seed_cli_sessions, priced_model_name):
    """Seven sessions of the module's project, one of an unpriced model, rolled up."""
    return list(seed_cli_sessions(get_session_list_seeds(priced_model_name)).values())


@pytest.fixture(scope="module")
def context_project(create_cli_analytics_project):
    return create_cli_analytics_project()


@pytest.fixture(scope="module")
def context_seeds(seed_cli_sessions, context_project, priced_model_name):
    """Sessions of a project of their own that read different amounts from the prompt
    cache, rolled up."""
    seeds = get_context_session_seeds(priced_model_name)
    return list(seed_cli_sessions(seeds, context_project).values())


def _get(api: CliAnalyticsApi, path: str, **params) -> dict:
    response = api.read(path, **day_window().params(), **params)
    assert_that(response.status_code, equal_to(200), response.text)
    return response.json()


def _list(api: CliAnalyticsApi, project: str, **params) -> dict:
    """One page of the Sessions list of a project over the seed day."""
    return _get(api, SESSIONS_PATH, projects=project, **params)


def _ids(body: dict) -> list[str]:
    return [session["trace_id"] for session in body["data"]["sessions"]]


def _read_pages(
    api: CliAnalyticsApi, project: str, per_page: int, **params
) -> tuple[list[dict], list[str]]:
    """Every page of the list, in order: the session rows and their ids."""
    first = _list(api, project, page=0, per_page=per_page, **params)
    page_count = -(-first["data"]["total"] // per_page)
    pages = [first] + [
        _list(api, project, page=page, per_page=per_page, **params)
        for page in range(1, page_count)
    ]
    rows = [row for body in pages for row in body["data"]["sessions"]]
    return rows, [row["trace_id"] for row in rows]


def _structure_problems(body: dict) -> list[str]:
    """What differs from the response contract of the list: missing keys and values of
    another type. Keys beyond the contract are not a problem."""
    problems = [
        f"missing top-level key {key!r}"
        for key in ("data", "metadata")
        if key not in body
    ]
    data = body.get("data", {})
    problems += [
        f"missing data key {key!r}" for key in SESSION_LIST_KEYS if key not in data
    ]
    problems += [
        f"metadata {key!r} is not {expected}"
        for key, expected in SESSION_METADATA_TYPES.items()
        if not isinstance(body.get("metadata", {}).get(key), expected)
    ]
    for row in data.get("sessions", []):
        problems += [
            f"session {row.get('trace_id')} field {key!r} is {row.get(key, 'missing')!r}"
            for key, expected in SESSION_ROW_TYPES.items()
            if key not in row or not isinstance(row[key], expected)
        ]
    return problems


def _comparable(row: dict) -> dict:
    """The fields the list and the detail of a session must agree on, with the cost
    rounded to the precision money is reported at."""
    values = {field: row[field] for field in SESSION_DETAIL_FIELDS}
    values["cost_usd"] = round(row["cost_usd"], 6)
    return values


@pytest.mark.cli_analytics
@pytest.mark.oss_standalone
@pytest.mark.api
def test_sessions_list_keeps_its_response_structure(
    sessions_api, cli_analytics_project, list_seeds
):
    """The list answers with the same keys and value types as before: the page, the
    page size and the total, a row of every session field, and the metadata."""
    body = _list(sessions_api, cli_analytics_project)

    assert_that(body["data"]["total"], equal_to(len(list_seeds)))  # repro:precondition
    assert_that(  # repro:symptom
        _structure_problems(body), empty(), "response differs from its contract"
    )


@pytest.mark.cli_analytics
@pytest.mark.oss_standalone
@pytest.mark.api
def test_sessions_list_without_paging_returns_first_twenty_newest_first(
    sessions_api, cli_analytics_project, list_seeds
):
    """With no page, page size or sort given, the list starts at page 0, holds up to
    twenty sessions per page and puts the newest session first."""
    expected_ids = sorted_session_ids(list_seeds, SORT_BY_START_TIME)[
        :SESSIONS_DEFAULT_PER_PAGE
    ]

    body = _list(sessions_api, cli_analytics_project)

    assert_that(body["data"]["total"], equal_to(len(list_seeds)))  # repro:precondition
    assert_that(  # repro:symptom
        (body["data"]["page"], body["data"]["per_page"], _ids(body)),
        equal_to((0, SESSIONS_DEFAULT_PER_PAGE, expected_ids)),
    )


@pytest.mark.cli_analytics
@pytest.mark.oss_standalone
@pytest.mark.api
def test_default_page_holds_twenty_of_twenty_one_sessions(
    sessions_api, create_cli_analytics_project, seed_cli_sessions, priced_model_name
):
    """With one session more than a page holds, the list without paging returns the
    twenty newest sessions and still reports all twenty-one in its total."""
    project = create_cli_analytics_project()
    seeds = list(
        seed_cli_sessions(
            get_paging_boundary_seeds(priced_model_name), project
        ).values()
    )
    expected_ids = sorted_session_ids(seeds, SORT_BY_START_TIME)[
        :SESSIONS_DEFAULT_PER_PAGE
    ]

    body = _list(sessions_api, project)

    assert_that(  # repro:precondition
        len(seeds), equal_to(SESSIONS_DEFAULT_PER_PAGE + 1)
    )
    assert_that(  # repro:symptom
        (body["data"]["total"], body["data"]["per_page"], _ids(body)),
        equal_to((len(seeds), SESSIONS_DEFAULT_PER_PAGE, expected_ids)),
    )


@pytest.mark.parametrize("sort_by", [SORT_BY_START_TIME, SORT_BY_COST])
@pytest.mark.cli_analytics
@pytest.mark.oss_standalone
@pytest.mark.api
def test_sort_orders_every_session_across_pages(
    sessions_api, cli_analytics_project, list_seeds, cost_model, sort_by
):
    """Read page by page, the sessions come in the order of the sort key, highest first
    (ties by session id), each session on one page, with the full total on every page.
    An unpriced session costs nothing, so it is last by cost."""
    expected_ids = sorted_session_ids(
        list_seeds, sort_by, {cost_model.base_name: cost_model.cost}
    )

    rows, listed_ids = _read_pages(
        sessions_api, cli_analytics_project, SORT_PAGE_SIZE, sort_by=sort_by
    )

    assert_that(
        sorted(listed_ids), equal_to(sorted(expected_ids))
    )  # repro:precondition
    assert_that(
        listed_ids, equal_to(expected_ids), f"sessions by {sort_by}"
    )  # repro:symptom


@pytest.mark.cli_analytics
@pytest.mark.oss_standalone
@pytest.mark.api
def test_context_per_call_sort_orders_sessions_by_cache_read_per_call(
    sessions_api, context_project, context_seeds
):
    """Sessions with more cache-read tokens per model call come first, whatever their
    total cache reads; a session that read nothing from the cache is last."""
    expected_ids = sorted_session_ids(context_seeds, SORT_BY_CTX_PER_CALL)

    rows, listed_ids = _read_pages(
        sessions_api,
        context_project,
        SORT_PAGE_SIZE,
        sort_by=SORT_BY_CTX_PER_CALL,
    )

    assert_that(  # repro:precondition
        {row["trace_id"]: row["ctx_per_call"] for row in rows},
        equal_to({seed.session_id: context_per_call(seed) for seed in context_seeds}),
    )
    assert_that(
        listed_ids, equal_to(expected_ids), "sessions by ctx_per_call"
    )  # repro:symptom


@pytest.mark.cli_analytics
@pytest.mark.oss_standalone
@pytest.mark.api
def test_efficiency_worst_session_is_first_by_context_per_call(
    sessions_api, context_project, context_seeds
):
    """The Efficiency view names as its worst session the one the Sessions list puts
    first when sorted by context per call, with the same ratio."""
    first_row = _list(sessions_api, context_project, sort_by=SORT_BY_CTX_PER_CALL)[
        "data"
    ]["sessions"][0]

    kpis = _get(sessions_api, EFFICIENCY_PATH, projects=context_project)["data"]["kpis"]

    assert_that(  # repro:precondition
        first_row["trace_id"],
        equal_to(sorted_session_ids(context_seeds, SORT_BY_CTX_PER_CALL)[0]),
    )
    assert_that(  # repro:symptom
        (kpis["worst_session_trace_id"], kpis["worst_session_ctx_per_call"]),
        equal_to((first_row["trace_id"], first_row["ctx_per_call"])),
    )


@pytest.mark.parametrize("term, keeps", SESSION_LIST_SEARCH_CASES)
@pytest.mark.cli_analytics
@pytest.mark.oss_standalone
@pytest.mark.api
def test_search_keeps_sessions_whose_repository_or_branch_contains_the_text(
    sessions_api, cli_analytics_project, list_seeds, term, keeps
):
    """Search ignores case and matches a part of the repository or branch; `%` and `_`
    in the text stand for themselves. The total counts every match."""
    expected_ids = sorted_session_ids(
        [seed for seed in list_seeds if keeps(seed)], SORT_BY_START_TIME
    )

    everything = _list(sessions_api, cli_analytics_project, per_page=1)
    searched = _list(sessions_api, cli_analytics_project, search=term)

    assert_that(
        everything["data"]["total"], equal_to(len(list_seeds))
    )  # repro:precondition
    assert_that(  # repro:symptom
        (searched["data"]["total"], _ids(searched)),
        equal_to((len(expected_ids), expected_ids)),
        f"sessions matching {term!r}",
    )


@pytest.mark.parametrize("case", SESSION_LIST_FILTER_CASES)
@pytest.mark.cli_analytics
@pytest.mark.oss_standalone
@pytest.mark.api
def test_filters_and_their_combinations_keep_only_matching_sessions(
    sessions_api,
    cli_analytics_project,
    cli_analytics_users,
    list_seeds,
    cost_model,
    case,
):
    """Each filter (user, repository, branch, framework) narrows the list to the
    sessions that match, together with the others and with search and sort. The total
    counts the matching sessions and the sort order holds within them."""
    params = dict(case.params)
    if case.users:
        params["users"] = cli_analytics_users[case.users].email
    sort_by = params.get("sort_by", SORT_BY_START_TIME)
    expected_ids = sorted_session_ids(
        [seed for seed in list_seeds if case.keeps(seed)],
        sort_by,
        {cost_model.base_name: cost_model.cost},
    )

    everything = _list(sessions_api, cli_analytics_project, per_page=1)
    filtered = _list(sessions_api, cli_analytics_project, **params)

    assert_that(
        everything["data"]["total"], equal_to(len(list_seeds))
    )  # repro:precondition
    assert_that(  # repro:symptom
        (filtered["data"]["total"], _ids(filtered)),
        equal_to((len(expected_ids), expected_ids)),
        f"sessions for {params}",
    )


@pytest.mark.parametrize("page, per_page, expected_count", SESSION_LIST_PAGE_CASES)
@pytest.mark.cli_analytics
@pytest.mark.oss_standalone
@pytest.mark.api
def test_page_holds_its_slice_of_sessions_and_reports_the_full_total(
    sessions_api, cli_analytics_project, list_seeds, page, per_page, expected_count
):
    """A page holds its slice of the sessions: a full page, a partial last one, and an
    empty one after the last. The page, page size and total are reported as asked and
    counted."""
    expected_ids = sorted_session_ids(list_seeds, SORT_BY_START_TIME)[
        page * per_page : (page + 1) * per_page
    ]

    body = _list(sessions_api, cli_analytics_project, page=page, per_page=per_page)

    assert_that(body["data"]["total"], equal_to(len(list_seeds)))  # repro:precondition
    assert_that(  # repro:symptom
        (len(_ids(body)), _ids(body), body["data"]["page"], body["data"]["per_page"]),
        equal_to((expected_count, expected_ids, page, per_page)),
    )


@pytest.mark.parametrize("params", SESSION_LIST_INVALID_PARAMS)
@pytest.mark.cli_analytics
@pytest.mark.oss_standalone
@pytest.mark.api
def test_list_refuses_paging_and_sort_values_out_of_range(
    sessions_api, cli_analytics_project, list_seeds, params
):
    """A negative page, a page size of zero or above the limit, and an unknown sort
    key are refused as a client error, not answered with a page."""
    valid = _list(sessions_api, cli_analytics_project, per_page=SESSIONS_MAX_PER_PAGE)

    refused = sessions_api.read(
        SESSIONS_PATH,
        projects=cli_analytics_project,
        **day_window().params(),
        **params,
    )

    assert_that(valid["data"]["total"], equal_to(len(list_seeds)))  # repro:precondition
    assert_that(  # repro:symptom
        refused.status_code,
        all_of(greater_than_or_equal_to(400), less_than(500)),
        f"status of the list asked for {params}",
    )


@pytest.mark.parametrize(
    "key", [f"list_{n}" for n in range(1, 7)] + ["list_7_unpriced"]
)
@pytest.mark.cli_analytics
@pytest.mark.oss_standalone
@pytest.mark.api
def test_listed_session_agrees_with_its_detail(
    sessions_api, cli_analytics_project, list_seeds, key
):
    """The tokens, cost, duration, framework and the other identity fields of a listed
    session are those of its detail."""
    seed = next(seed for seed in list_seeds if seed.key == key)
    rows, _ = _read_pages(
        sessions_api, cli_analytics_project, SESSIONS_MAX_PER_PAGE, sort_by=SORT_BY_COST
    )
    row = next((row for row in rows if row["trace_id"] == seed.session_id), None)

    response = sessions_api.read(f"{SESSIONS_PATH}/{seed.session_id}")
    assert_that(response.status_code, equal_to(200), response.text)
    detail = response.json()["data"]

    assert_that(
        row is not None, is_(True), "the session is listed"
    )  # repro:precondition
    assert_that(  # repro:symptom
        _comparable(detail), equal_to(_comparable(row)), f"detail of {key}"
    )


@pytest.mark.cli_analytics
@pytest.mark.oss_standalone
@pytest.mark.api
def test_listed_sessions_add_up_to_the_cost_totals(
    analytics_utils, sessions_api, cli_analytics_project, list_seeds
):
    """Over the whole window, the sessions' cost and tokens add up to the cost view's
    totals, so a page of the list and a total never disagree."""
    kpis = analytics_utils.get_cli_analytics_cost(
        projects=cli_analytics_project, **day_window().params()
    ).data.kpis

    rows, _ = _read_pages(sessions_api, cli_analytics_project, SESSIONS_MAX_PER_PAGE)

    assert_that(len(rows), equal_to(len(list_seeds)))  # repro:precondition
    assert_that(  # repro:symptom
        sum(row["cost_usd"] for row in rows),
        close_to(kpis.total_cost_usd, COST_TOLERANCE),
        "cost of the listed sessions against the cost view total",
    )
    assert_that(
        sum(row["input_tokens"] + row["output_tokens"] for row in rows),
        equal_to(kpis.total_tokens),
        "tokens of the listed sessions against the cost view total",
    )


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"sort_by": SORT_BY_COST}, id="cost-sort"),
        pytest.param({"framework": PURE_CHAT_LABEL}, id="framework-filter"),
    ],
)
@pytest.mark.cli_analytics
@pytest.mark.oss_standalone
@pytest.mark.api
def test_unpriced_model_of_the_window_is_reported_whatever_the_page(
    sessions_api, cli_analytics_project, list_seeds, cost_model, params
):
    """A model with no catalog price is named in the metadata and the cost is marked
    incomplete, also when the page holds none of its sessions."""
    unpriced_seed = next(seed for seed in list_seeds if seed.key == "list_7_unpriced")

    body = _list(sessions_api, cli_analytics_project, per_page=1, **params)

    assert_that(  # repro:precondition
        [row["cost_available"] for row in body["data"]["sessions"]],
        contains_exactly(True),
        "the page holds a priced session only",
    )
    assert_that(  # repro:symptom
        body["metadata"]["unpriced_models"],
        has_item(unpriced_seed.model),
        "models without a price",
    )
    assert_that(body["metadata"]["cost_incomplete"], is_(True))


@pytest.mark.cli_analytics
@pytest.mark.oss_standalone
@pytest.mark.api
def test_session_that_arrives_later_is_placed_by_every_sort_and_filter(
    sessions_api,
    create_cli_analytics_project,
    seed_cli_sessions,
    priced_model_name,
    cost_model,
):
    """A session rolled up after the others were listed is in the sorted and filtered
    pages at once, with the right place: first by context, in the middle by cost, and
    the only one the framework filter keeps."""
    project = create_cli_analytics_project()
    early = list(
        seed_cli_sessions(get_early_session_seeds(priced_model_name), project).values()
    )
    early_listed = _list(sessions_api, project)["data"]["total"]
    new = seed_cli_sessions([get_new_session_seed(priced_model_name)], project)
    seeds = early + list(new.values())
    prices = {cost_model.base_name: cost_model.cost}

    listed = {
        "ctx": _ids(_list(sessions_api, project, sort_by=SORT_BY_CTX_PER_CALL)),
        "cost": _ids(_list(sessions_api, project, sort_by=SORT_BY_COST)),
        "framework": _ids(_list(sessions_api, project, framework=SUPERPOWERS_LABEL)),
    }

    assert_that(early_listed, equal_to(len(early)))  # repro:precondition
    assert_that(  # repro:symptom
        listed,
        equal_to(
            {
                "ctx": sorted_session_ids(seeds, SORT_BY_CTX_PER_CALL),
                "cost": sorted_session_ids(seeds, SORT_BY_COST, prices),
                "framework": [list(new.values())[0].session_id],
            }
        ),
    )
