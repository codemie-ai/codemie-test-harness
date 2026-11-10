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

"""LLM models — budget routing smoke test.

Parametrized variant of
``test_admin_creates_platform_project_budget_routes_spending_from_personal``
(see test_project_budget_assignment.py) that runs the same personal ->
project-budget spending flow for every model in ``MODEL_RESPONSES``. Goal:
confirm each model responds, its spend shows up in LiteLLM, and the project
budget feature routes that spend correctly.

Premium status (``LLMModel.is_premium``) is read from the backend at runtime,
not from static test data, since it is a billing-tier attribute the platform
controls rather than something derivable from ``ModelTypes``:
  - ``test_model_platform_budget_routes_spending_from_personal`` covers every
    non-premium model and routes through the ``platform`` budget category.
  - ``test_premium_model_budget_routes_spending_from_personal`` covers premium
    models and routes through the ``premium_models`` budget category.
"""

import functools
import logging
from time import sleep
from typing import Optional

import pytest
from hamcrest import (
    assert_that,
    close_to,
    equal_to,
    greater_than,
    has_item,
    none,
    not_none,
)

from codemie_test_harness.tests.test_data.budget_test_data import (
    budget_chat_prompt,
    BUDGET_CACHE_DELAY,
    DEFAULT_PREMIUM_BUDGET_ID,
    PLATFORM_BUDGET_CATEGORIES,
    PREMIUM_BUDGET_CATEGORIES,
    project_key_alias,
)
from codemie_test_harness.tests.test_data.llm_test_data import MODEL_RESPONSES
from codemie_test_harness.tests.utils.client_factory import get_client
from codemie_test_harness.tests.utils.env_resolver import get_environment

logger = logging.getLogger(__name__)


_PREMIUM_TEST = "test_premium_model_budget_routes_spending_from_personal"


@functools.cache
def _premium_flags() -> Optional[dict]:
    """Premium flag of every model the backend lists, read once per process while pytest collects.

    None when the backend cannot be reached, so collecting (``--collect-only``, no credentials)
    still works; the models are then collected for both tests.
    """
    try:
        return {row.base_name: row.is_premium for row in get_client().llms.list()}
    except Exception as error:
        logger.warning(
            "Premium flags unavailable while collecting, models are not split: %s",
            error,
        )
        return None


def pytest_generate_tests(metafunc):
    """Give each test only the models it covers, so no case is skipped for being the other kind.

    Premium status is a billing-tier attribute the backend owns, so it is read from the backend.
    A model the backend does not list goes to the platform test, which reports it as missing.
    """
    if "model_type" not in metafunc.fixturenames:
        return
    env = get_environment()
    models = list(MODEL_RESPONSES)
    if any(env in model_data.environments for model_data in models):
        premium = _premium_flags()
        wants_premium = metafunc.function.__name__ == _PREMIUM_TEST
        if premium is not None:
            models = [
                model_data
                for model_data in models
                if bool(premium.get(model_data.model_type, False)) == wants_premium
            ]
    test_data = [
        pytest.param(
            model_data.model_type,
            marks=pytest.mark.skipif(
                env not in model_data.environments,
                reason=f"Skip on non {'/'.join(str(e) for e in model_data.environments)} envs",
            ),
        )
        for model_data in models
    ]
    metafunc.parametrize("model_type", test_data)


def _is_premium(llm_utils, model_type) -> bool:
    models = llm_utils.list_llm_models()
    assert_that(
        [row.base_name for row in models],
        has_item(model_type),
        f"{model_type} is missing in backend response",
    )
    return next(row.is_premium for row in models if row.base_name == model_type)


def _assert_model_routes_spending_to_project_budget(
    *,
    model_type,
    budget_category,
    categories,
    personal_customer_id,
    project_name,
    user_assistant_utils,
    project_budget_groups,
    lite_llm_budget_utils,
    admin_project_utils,
):
    alias = project_key_alias(project_name, budget_category)

    assistant = user_assistant_utils.create_assistant(
        llm_model_type=model_type, project_name=project_name
    )
    try:
        # Phase 1 — no project budget: model responds, spending goes to personal
        logger.info(
            "Phase 1 (%s): no project %s budget — expecting personal spending for %s",
            model_type,
            budget_category,
            personal_customer_id,
        )
        response = user_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
        assert_that(response, not_none())
        logger.info("Waiting for personal spending (customer=%s)", personal_customer_id)
        customer = lite_llm_budget_utils.wait_for_spending(personal_customer_id)
        assert_that(customer, not_none())
        assert_that(float(customer["spend"]), greater_than(0))
        assert_that(lite_llm_budget_utils.get_key_info_by_alias(alias), none())

        # Phase 2 — project budget created: spending goes to project key
        logger.info(
            "Phase 2 (%s): creating project %s budget — expecting spending on project key (alias=%s)",
            model_type,
            budget_category,
            alias,
        )
        project_budget_groups.create(
            project_name, categories, name_prefix=f"autotest-{budget_category}"
        )
        sleep(BUDGET_CACHE_DELAY)
        logger.info(
            "Sending assistant request (project %s budget active, model=%s)",
            budget_category,
            model_type,
        )
        user_assistant_utils.ask_assistant(assistant, budget_chat_prompt())
        logger.info("Waiting for project key alias spending (alias=%s)", alias)
        project_key_info = lite_llm_budget_utils.wait_for_key_alias_spending(alias)
        assert_that(project_key_info, not_none())
        assert_that(float(project_key_info["spend"]), greater_than(0))

        logger.info(
            "Waiting for %s budget spend in ledger (project=%s)",
            budget_category,
            project_name,
        )
        budget = admin_project_utils.wait_for_project_budget_spending_above(
            project_name, budget_category, float(project_key_info["spend"]) - 0.0001
        )
        assert_that(
            budget,
            not_none(),
            f"Project {budget_category} budget not found in spend ledger",
        )
        assert_that(
            budget.current_spending,
            close_to(float(project_key_info["spend"]), 0.0001),
            f"Project {budget_category} budget current_spending should match project {budget_category} key spend.",
        )
    finally:
        user_assistant_utils.delete_assistant(assistant)


@pytest.mark.budget
@pytest.mark.llm
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_model_platform_budget_routes_spending_from_personal(
    keycloak_user,
    llm_utils,
    user_assistant_utils,
    lite_llm_budget_utils,
    project_setup,
    project_budget_groups,
    admin_project_utils,
    model_type,
):
    assert_that(
        _is_premium(llm_utils, model_type),
        equal_to(False),
        f"{model_type} is a premium model — it belongs to the premium budget test",
    )

    email, _ = keycloak_user
    _assert_model_routes_spending_to_project_budget(
        model_type=model_type,
        budget_category="platform",
        categories=PLATFORM_BUDGET_CATEGORIES,
        personal_customer_id=email,
        project_name=project_setup,
        user_assistant_utils=user_assistant_utils,
        project_budget_groups=project_budget_groups,
        lite_llm_budget_utils=lite_llm_budget_utils,
        admin_project_utils=admin_project_utils,
    )


@pytest.mark.budget
@pytest.mark.llm
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.timeout(1000)
def test_premium_model_budget_routes_spending_from_personal(
    keycloak_user,
    llm_utils,
    user_assistant_utils,
    lite_llm_budget_utils,
    project_setup,
    project_budget_groups,
    admin_project_utils,
    model_type,
):
    assert_that(
        _is_premium(llm_utils, model_type),
        equal_to(True),
        f"{model_type} is not a premium model — it belongs to the platform budget test",
    )

    email, _ = keycloak_user
    premium_customer_id = f"{email}_{DEFAULT_PREMIUM_BUDGET_ID}"
    _assert_model_routes_spending_to_project_budget(
        model_type=model_type,
        budget_category="premium_models",
        categories=PREMIUM_BUDGET_CATEGORIES,
        personal_customer_id=premium_customer_id,
        project_name=project_setup,
        user_assistant_utils=user_assistant_utils,
        project_budget_groups=project_budget_groups,
        lite_llm_budget_utils=lite_llm_budget_utils,
        admin_project_utils=admin_project_utils,
    )
