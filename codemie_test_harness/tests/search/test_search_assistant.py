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
from hamcrest import assert_that

from codemie_test_harness.tests import TEST_USER
from codemie_test_harness.tests.utils.base_utils import get_random_name


@pytest.fixture(scope="session")
def test_assistant_name():
    base_name = get_random_name()
    return f"{base_name}_assistant_for_search_test"


@pytest.fixture(scope="session")
def test_assistant_partial_name(test_assistant_name):
    return test_assistant_name[:8]


@pytest.fixture(scope="session", autouse=True)
def search_assistant(assistant_utils, default_llm, test_assistant_name):
    assistant = assistant_utils.create_assistant(
        assistant_name=test_assistant_name,
        shared=True,
        llm_model_type=default_llm.base_name,
    )
    yield assistant
    if assistant:
        assistant_utils.delete_assistant(assistant)


@pytest.fixture(scope="session")
def test_data(test_assistant_name, test_assistant_partial_name):
    return [
        {"search": test_assistant_name},
        {"created_by": TEST_USER, "search": test_assistant_name},
        {"created_by": TEST_USER},
        {"shared": True, "search": test_assistant_name},
        {"is_global": False, "search": test_assistant_name},
        {"search": test_assistant_partial_name},
        {"created_by": TEST_USER, "search": test_assistant_partial_name},
        {"shared": True, "search": test_assistant_partial_name},
        {"is_global": False, "search": test_assistant_partial_name},
    ]


@pytest.fixture
def filters(request, test_data):
    return test_data[request.param]


def pytest_generate_tests(metafunc):
    if "filters" in metafunc.fixturenames:
        # Parametrize with all 9 test cases
        # Test cases with indices 1, 2, 6 are excluded from smoke suite
        ids = [
            "search_full_name",
            "created_by_and_search_full",
            "created_by_only",
            "shared_and_search_full",
            "not_global_and_search_full",
            "search_partial_name",
            "created_by_and_search_partial",
            "shared_and_search_partial",
            "not_global_and_search_partial",
        ]

        # Check if we're running with smoke or sanity marker
        mark_expr = metafunc.config.getoption("-m", "")
        is_smoke = "smoke" in mark_expr if mark_expr else False
        is_sanity = "sanity" in mark_expr if mark_expr else False

        # Mark specific test cases to skip when smoke or sanity marker is present
        params = []
        excluded_from_smoke = [
            "created_by_and_search_full",
            "created_by_only",
            "created_by_and_search_partial",
        ]

        for i, test_id in enumerate(ids):
            if (is_smoke or is_sanity) and test_id in excluded_from_smoke:
                # Skip these test cases in smoke suite
                params.append(
                    pytest.param(
                        i,
                        marks=pytest.mark.skip(
                            reason="Excluded from smoke/sanity suite"
                        ),
                    )
                )
            else:
                params.append(i)

        metafunc.parametrize(
            "filters",
            params,
            ids=ids,
            indirect=True,
        )


@pytest.mark.sanity
@pytest.mark.smoke
@pytest.mark.assistant
@pytest.mark.search
@pytest.mark.api
def test_search_assistant_by_filters(search_utils, filters, test_assistant_name):
    response = search_utils.list_assistants(filters)
    names = list(map(lambda item: item["name"], response))

    assert_that(
        test_assistant_name in names, "Assistant is not found in search results."
    )
