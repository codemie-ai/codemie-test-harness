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

import random

import pytest
import yaml
from hamcrest import assert_that, equal_to

from codemie_test_harness.tests import TEST_USER
from codemie_test_harness.tests.ui.pageobject.workflows.create_workflow_page import (
    CreateWorkflowPage,
)
from codemie_test_harness.tests.ui.pageobject.workflows.workflow_template_details import (
    WorkflowTemplateDetailsPage,
)
from codemie_test_harness.tests.ui.pageobject.workflows.workflow_templates_page import (
    WorkflowTemplatesPage,
)
from codemie_test_harness.tests.ui.pageobject.workflows.workflows_page import (
    WorkflowsPage,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name

_SEARCH_QUERY_1 = "Iteration"
_SEARCH_QUERY_2 = "Example"


@pytest.fixture(scope="function")
def predefined_templates(workflow_utils):
    """Fixture returns predefined templates data."""
    return workflow_utils.get_prebuilt_workflows()


@pytest.mark.workflow
@pytest.mark.workflow_templates
@pytest.mark.ui
def test_templates_visible(page, predefined_templates):
    """Verify that workflow templates are presented and tooltips visible for the user."""
    templates = predefined_templates

    workflow_templates_page = WorkflowTemplatesPage(page)
    workflow_templates_page.navigate_to()

    page_size = 12
    visible_count = min(page_size, len(templates))
    workflow_templates_page.should_have_templates(visible_count)

    for i in range(visible_count):
        expected_name = templates[i]["name"]
        expected_description = templates[i]["description"]
        trimmed_description = templates[i]["description"][:70]

        workflow_templates_page.should_have_title_description(
            i, expected_name, trimmed_description, expected_description
        )


@pytest.mark.workflow
@pytest.mark.workflow_templates
@pytest.mark.ui
def test_templates_details(page, predefined_templates):
    """Verify that workflow template leads to specific template page."""
    templates = predefined_templates

    workflow_templates_page = WorkflowTemplatesPage(page)
    workflow_templates_details_page = WorkflowTemplateDetailsPage(page)
    workflow_templates_page.navigate_to()

    page_size = 12
    random_index = random.randint(0, min(page_size, len(templates)) - 1)
    random_template = templates[random_index]

    template_title = random_template["name"]
    description = random_template["description"]
    yaml_config = random_template["yaml_config"]

    workflow_templates_page.template_details_click(random_index)
    workflow_templates_details_page.should_have_template_header()
    workflow_templates_details_page.should_have_template_sidebar()
    workflow_templates_details_page.should_have_template_details(
        template_title, description, yaml_config
    )


_MCP_SERVER_ENV_FIELDS = frozenset(
    {"auth_token", "mcp_connect_url", "config", "description", "enabled"}
)


def _normalize_value(value):
    """Recursively normalize a parsed YAML value for structural comparison.

    Applies the following normalizations:
    - Strings: strip trailing whitespace/newlines from each line and from the whole value.
      This eliminates cosmetic differences in multi-line strings (e.g. trailing ``\\n``
      that the API yaml_config stores but the ACE editor omits).
    - Lists: normalize each element recursively.
    - Dicts: normalize each value recursively.
    - Other types: returned as-is.
    """
    if isinstance(value, str):
        # Normalize each line (strip trailing spaces) and strip trailing newlines
        lines = [line.rstrip() for line in value.splitlines()]
        return "\n".join(lines).rstrip()
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    if isinstance(value, dict):
        return {k: _normalize_value(v) for k, v in value.items()}
    return value


def _strip_env_specific_fields(yaml_data: dict) -> dict:
    """Return a normalized copy of parsed YAML with environment-specific fields removed.

    Performs three transformations:
    1. Removes env-specific keys from ``mcp_server`` mappings in ``states`` entries
       (``auth_token``, ``mcp_connect_url``, ``config``, ``description``, ``enabled``).
       These are injected by the backend at runtime and differ between environments.
    2. Removes ``meta_*`` prefixed keys from ``next:`` mappings in ``states`` entries
       (e.g. ``meta_iter_state_id``). These are visual-editor metadata fields that
       track iterator node connections and are not part of the canonical template YAML.
    3. Normalizes all string values by stripping trailing whitespace and newlines so
       that cosmetic differences (e.g. a trailing ``\\n`` present in the API template
       but absent in the ACE editor rendering) do not cause false failures.
    """
    # First normalize all values recursively
    normalized = _normalize_value(yaml_data)

    # Top-level retry_policy (the workflow-wide default retry policy).
    if "retry_policy" in normalized and isinstance(normalized["retry_policy"], dict):
        normalized = {
            **normalized,
            "retry_policy": _coerce_retry_policy_floats(normalized["retry_policy"]),
        }

    # Then strip env-specific and editor-specific fields from states
    states = normalized.get("states", [])
    cleaned_states = []
    for state in states:
        state_copy = dict(state)
        # Strip env-specific keys from mcp_server
        if "mcp_server" in state_copy and isinstance(state_copy["mcp_server"], dict):
            state_copy["mcp_server"] = {
                k: v
                for k, v in state_copy["mcp_server"].items()
                if k not in _MCP_SERVER_ENV_FIELDS
            }
        # Strip meta_* keys from next: mapping (visual editor metadata)
        if "next" in state_copy and isinstance(state_copy["next"], dict):
            state_copy["next"] = {
                k: v for k, v in state_copy["next"].items() if not k.startswith("meta_")
            }
        # Per-state retry_policy override (a state can override the workflow-wide
        # default above with its own retry_policy).
        if "retry_policy" in state_copy and isinstance(
            state_copy["retry_policy"], dict
        ):
            state_copy["retry_policy"] = _coerce_retry_policy_floats(
                state_copy["retry_policy"]
            )
        cleaned_states.append(state_copy)
    # Sort by id so list order is irrelevant to the comparison: the visual
    # editor relocates unreachable states into orphaned_states and the page
    # object merges them back at the end of the list (see get_yaml_content),
    # which does not match their original position in the raw template.
    # Order was never semantically significant here — each state's `next`
    # field, not its list position, defines the actual graph.
    cleaned_states.sort(key=lambda s: s.get("id", ""))
    return {**normalized, "states": cleaned_states}


def _coerce_retry_policy_floats(retry_policy: dict) -> dict:
    """Coerce retry_policy's float-typed fields to float.

    The API may return an int (5) for any of these fields while the stored
    template has a float (5.0); coerce both sides so yaml.dump matches.
    max_attempts is excluded — it's a count, always int.
    """
    rp = dict(retry_policy)
    for field in ("backoff_factor", "initial_interval_seconds", "max_interval_seconds"):
        if field in rp and isinstance(rp[field], (int, float)):
            rp[field] = float(rp[field])
    return rp


_TEMPLATE_VARIABLE_FILL_VALUE = "test-value"


def _substitute_required_variables(
    text: str, required_variables: list[str], value: str = _TEMPLATE_VARIABLE_FILL_VALUE
) -> str:
    """Mirror the app's own ``${input:name}`` substitution.

    When a template declares required variables, the "Configure Template
    Variables" dialog substitutes every ``${input:name}`` occurrence with the
    value the user enters — in both the rendered YAML and the description
    text. To compare the raw template's ``yaml_config``/``description``
    against what the UI actually shows post-substitution, the same
    replacement must be applied to the expected side before comparing.
    """
    for name in required_variables:
        text = text.replace(f"${{input:{name}}}", value)
    return text


@pytest.mark.workflow
@pytest.mark.workflow_templates
@pytest.mark.ui
def test_templates_creation(page, predefined_templates):
    """Verify that workflow template create button leads to Create Workflow Page.

    The YAML comparison strips environment-specific MCP server fields
    (auth_token, mcp_connect_url, config, description, enabled) from both the
    actual and expected YAML before comparing, so the test is stable across
    environments while still verifying the structurally significant parts
    (states, tool, tool_args).
    """
    templates = predefined_templates

    workflow_templates_page = WorkflowTemplatesPage(page)
    create_workflow_page = CreateWorkflowPage(page)

    workflow_templates_page.navigate_to()

    page_size = 12
    random_index = random.randint(0, min(page_size, len(templates)) - 1)
    random_template = templates[random_index]

    description = random_template["description"]
    yaml_config = random_template["yaml_config"]
    required_variables = random_template["required_variables"]

    workflow_templates_page.click_create_workflow_from_template(random_index)
    # Templates with ${input:name} placeholders show a
    # "Configure Template Variables" dialog that must be filled before the
    # canvas becomes usable; templates without any placeholder don't show it.
    create_workflow_page.fill_template_variables_if_present(
        _TEMPLATE_VARIABLE_FILL_VALUE
    )
    create_workflow_page.should_be_on_create_workflow_page(
        "Create Workflow from Template"
    )
    create_workflow_page.should_have_all_form_sections_visible()

    config_panel = create_workflow_page.open_yaml_panel()
    actual_yaml = config_panel.get_yaml_content()

    # Mirror the dialog's own substitution on the expected side so templates
    # with required variables compare correctly against the now-substituted
    # actual YAML/description.
    description = _substitute_required_variables(description, required_variables)
    yaml_config = _substitute_required_variables(yaml_config, required_variables)

    actual_parsed = _strip_env_specific_fields(yaml.safe_load(actual_yaml))
    expected_parsed = _strip_env_specific_fields(yaml.safe_load(yaml_config))

    normalized_actual = yaml.dump(
        actual_parsed, sort_keys=True, default_flow_style=False
    )
    normalized_expected = yaml.dump(
        expected_parsed, sort_keys=True, default_flow_style=False
    )

    assert_that(
        normalized_actual,
        equal_to(normalized_expected),
        f"Workflow YAML structure mismatch after stripping environment-specific fields.\n"
        f"Actual (stripped):\n{normalized_actual}\n"
        f"Expected (stripped):\n{normalized_expected}",
    )

    config_panel.switch_to_basic_tab()
    config_panel.should_have_description_field_value(description)


_PAGINATION_PAGE_SIZE = 12


@pytest.mark.workflow
@pytest.mark.workflow_templates
@pytest.mark.pagination
@pytest.mark.ui
def test_workflow_templates_pagination_full_flow(page, predefined_templates):
    """TC-001: Workflow Templates pagination full flow.

    Covers AC-1, AC-3, AC-4, AC-5.

    Steps executed in sequence within a single test (mirrors a manual walkthrough):
      1. Navigate to /workflows/templates.
      2. Template cards visible on page 1 — AC-5.
      3. Pagination controls visible — AC-1.
      5. Previous-page button disabled on page 1 — boundary.
      6. Click next page; verify different card set — AC-3.
      7. Click previous page; verify return to page-1 card set — AC-3.
      8. Conditional: click page 2 directly — AC-3.
      9. Change items-per-page (if control present) — AC-4.
     10. Navigate to last page; next-page button disabled — boundary.
     11. Reload page; page-1 cards still visible — AC-3.

    Precondition: environment has more than _PAGINATION_PAGE_SIZE templates.
    The test is skipped gracefully when this precondition is not met.
    """
    templates = predefined_templates
    total = len(templates)

    wt_page = WorkflowTemplatesPage(page)
    wt_page.navigate_to()

    # Step 2: template cards visible on page 1 — AC-5
    wt_page.should_have_templates_visible()

    if total <= _PAGINATION_PAGE_SIZE:
        pytest.skip(
            f"Only {total} workflow templates in the environment; "
            f"need > {_PAGINATION_PAGE_SIZE} to trigger pagination. "
            "Skipping TC-001 pagination flow."
        )

    # Step 3: pagination controls visible — AC-1
    wt_page.should_see_pagination()

    # Step 5: previous-page button disabled / absent on page 1
    wt_page.should_have_previous_page_disabled()

    # Step 6: click next page, verify a different card set loads — AC-3
    page1_first_title = wt_page.get_first_template_title()
    wt_page.click_next_page()
    wt_page.should_have_templates_visible()
    wt_page.should_not_contain_template_text(page1_first_title)

    # Step 7: click previous page, verify return to original card set — AC-3
    wt_page.click_previous_page()
    wt_page.should_have_templates_visible()
    wt_page.should_contain_template_text(page1_first_title)

    # Step 8: direct page-number button navigation (conditional) — AC-3
    page2_btn = wt_page.pagination_page_button(2)
    if page2_btn.is_visible():
        wt_page.select_page(2)
        wt_page.should_see_pagination()
        wt_page.should_not_contain_template_text(page1_first_title)

    # Step 9: change items-per-page — AC-4
    if wt_page.show_per_page_dropdown.is_visible():
        initial_card_count = wt_page.templates_list.count()
        wt_page.change_items_per_page(24)
        wt_page.should_have_card_count_other_than(initial_card_count)
    # else: per-page dropdown absent — AC-4 skipped gracefully

    # Step 10: navigate to last page, verify next-page button disabled — boundary
    wt_page.navigate_to()
    wt_page.navigate_to_last_page()
    wt_page.should_have_next_page_disabled()

    # Step 11: reload from last page; verify cards still visible after state reset — AC-3
    wt_page.refresh_page()
    wt_page.should_have_templates_visible()


@pytest.mark.workflow
@pytest.mark.workflow_templates
@pytest.mark.ui
def test_template_create(page, predefined_templates):
    """Verify that workflow template can be created."""
    templates = predefined_templates
    workflow_name = get_random_name()
    template_name = "Iteration Workflow Example"
    template_description = next(
        (
            template["description"]
            for template in templates
            if template["name"] == template_name
        )
    )

    workflow_template_page = WorkflowTemplatesPage(page)
    create_workflow_page = CreateWorkflowPage(page)
    workflows_page = WorkflowsPage(page)

    workflow_template_page.navigate_to()
    workflow_template_page.type_search(template_name)
    workflow_template_page.click_create_workflow_from_specific_template(template_name)
    create_workflow_page.create_workflow(workflow_name)
    workflows_page.should_see_workflow_card(workflow_name)
    workflows_page.should_see_workflow_author(workflow_name, TEST_USER)
    workflows_page.should_see_workflow_description(workflow_name, template_description)


# ---------------------------------------------------------------------------
# Search query constants — partial names expected to match a subset of
# predefined workflow templates without matching ALL of them.
# ---------------------------------------------------------------------------


@pytest.mark.workflow
@pytest.mark.workflow_templates
@pytest.mark.ui
def test_workflow_template_search_journey(page, predefined_templates):
    """TC-01: Full search journey on the Workflow Templates page.

    Steps:
    1. Navigate to /workflows/templates
    2. Verify the search/filter input is visible
    3. Enter a partial name query matching a subset of templates
    4. Verify filtered results are shown (fewer cards than full list)
    5. Clear the search input
    6. Verify all templates are restored
    7. Enter a different search query and verify filtered results update
    8. Navigate away to /workflows
    9. Navigate back to /workflows/templates
    10. Verify previous search filter state persists (value + filtered results)
    """
    page_size = 12
    visible_count = min(page_size, len(predefined_templates))

    workflow_templates_page = WorkflowTemplatesPage(page)

    # Step 1 — Navigate to workflow templates
    workflow_templates_page.navigate_to()

    # Step 2 — Search input must be visible
    workflow_templates_page.should_show_search_input_visible()

    # Step 3 — Enter first search query
    workflow_templates_page.type_search(_SEARCH_QUERY_1)

    # Step 4 — Filtered results shown: every visible card contains the search term
    workflow_templates_page.should_show_template(_SEARCH_QUERY_1)

    # Step 5 — Clear search
    workflow_templates_page.clear_search()

    # Step 6 — All templates restored
    workflow_templates_page.should_have_templates(visible_count)

    # Step 7 — Enter a different search query
    workflow_templates_page.type_search(_SEARCH_QUERY_2)
    workflow_templates_page.should_show_template(_SEARCH_QUERY_2)

    # Step 8 — Navigate away to /workflows
    workflows_page = WorkflowsPage(page)
    workflows_page.navigate_to()

    # Step 9 — Navigate back to /workflows/templates
    workflow_templates_page.navigate_to()

    # Step 10 — Verify previous search filter persists (client-side store survives
    # in-session navigation via workflowsFilters Zustand store)
    workflow_templates_page.should_show_template(_SEARCH_QUERY_2)
