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

"""UI tests: the platform status of a model on the Project Details Models tab.

A Disabled model or router has no row on the tab and is left out of both numbers of
the "N of M models available" counter; a Deprecated one stays listed and can be
ticked. Saving keeps a hidden Disabled name the project already stores, never adds
one, and never widens an explicit list to "all models" unless the admin resets it.
A Disabled project default blocks the save until an available default is chosen.

Statuses are set through the API on the dedicated "(Autotest)" models only and put
back on teardown (status_test_model(s)). The status is platform-wide, so the tests
carry xdist_group(name="model_status") and run one after another on one worker.
Stored project settings are read back with GET /v1/projects/{name}: ``allowed_models``
None means "all models", a list is an explicit list.
"""

import pytest
from hamcrest import (
    all_of,
    assert_that,
    equal_to,
    has_item,
    has_items,
    instance_of,
    is_not,
    none,
)

from codemie_sdk.models.llm import ModelStatus

from codemie_test_harness.tests.ui.pageobject.administration.project_details_page import (
    ProjectDetailsPage,
)
from codemie_test_harness.tests.ui.test_data.project_models_status_test_data import (
    DEFAULT_SELECT_LABEL,
    MODEL_SETTINGS_SAVED_TOAST,
)
from codemie_test_harness.tests.utils.llm_utils import (
    global_default_model_label,
    selectable_chat_models,
)


def _open_models_tab(page, project_name):
    """Load the project's Models tab afresh, so it reads the current catalog."""
    details_page = ProjectDetailsPage(page)
    details_page.navigate_to(project_name)
    models = details_page.open_models_tab()
    models.should_be_visible()
    return models


# @case models-tab-hides-disabled-models_TC_001
# Rows = checklistModels, a 'disabled' entry has no row (ProjectModelsSection.tsx:330);
# counter '{checked} of {checklistModels.length}' excludes it (ProjectModelsSection.tsx:298).
@pytest.mark.xdist_group(name="model_status")
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_models_tab_hides_a_disabled_model_and_drops_it_from_the_counter(
    page,
    project_admin_setup,
    project_admin_setup_client,
    llm_model_status_utils,
    status_test_model,
):
    project_name = project_admin_setup[0]
    label = status_test_model.label

    models = _open_models_tab(page, project_name)
    models.should_list_model(label, checked=True)
    selected, total = models.selected_and_total_count()

    llm_model_status_utils.apply_status(
        status_test_model.base_name, ModelStatus.DISABLED, project_admin_setup_client
    )

    models = _open_models_tab(page, project_name)
    models.should_not_list_model(label)
    models.should_show_counter(selected - 1, total - 1)
    models.should_show_model_count(total - 1)


# @case models-tab-hides-disabled-models_TC_001
# 'deprecated' entries stay checklist-listed (projectModelConfiguration.ts:31) and are
# toggled through onSelectionChange=setModelEnabled (ProjectModelsSection.tsx:337).
@pytest.mark.xdist_group(name="model_status")
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_models_tab_keeps_a_deprecated_model_listed_and_tickable(
    page,
    project_admin_setup,
    project_admin_setup_client,
    llm_model_status_utils,
    status_test_model,
):
    project_name = project_admin_setup[0]
    label = status_test_model.label

    models = _open_models_tab(page, project_name)
    selected, total = models.selected_and_total_count()

    llm_model_status_utils.apply_status(
        status_test_model.base_name, ModelStatus.DEPRECATED, project_admin_setup_client
    )

    models = _open_models_tab(page, project_name)
    models.should_list_model(label, checked=True)
    models.should_show_counter(selected, total)
    models.set_model_checked(label, False)
    models.should_show_counter(selected - 1, total)
    models.set_model_checked(label, True)
    models.should_show_counter(selected, total)


# @case models-tab-hides-disabled-models_TC_003
# A stored allow_list holding a hidden name saves with policy 'disable' and keeps the
# name (ProjectModelsSection.tsx:204, projectModelConfiguration.ts:93); toast
# 'Model settings updated' (ProjectModelsSection.tsx:225).
@pytest.mark.xdist_group(name="model_status")
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_saving_one_more_ticked_model_keeps_a_hidden_disabled_model_in_the_stored_list(
    page,
    client,
    project_admin_setup,
    project_admin_setup_client,
    admin_project_utils,
    llm_model_status_utils,
    status_test_models,
):
    project_name = project_admin_setup[0]
    hidden, kept = status_test_models
    extra = selectable_chat_models(client, exclude=(hidden.base_name, kept.base_name))[
        0
    ]
    admin_project_utils.restrict_models(
        project_name, [hidden.base_name, kept.base_name], kept.base_name
    )
    llm_model_status_utils.apply_status(
        hidden.base_name, ModelStatus.DISABLED, project_admin_setup_client
    )

    models = _open_models_tab(page, project_name)
    models.should_not_list_model(hidden.label)
    models.set_model_checked(extra.label, True)
    models.apply_changes()
    models.toast.should_show_success(MODEL_SETTINGS_SAVED_TOAST)

    stored = admin_project_utils.get_project_detail(project_name).allowed_models
    assert_that(
        stored,
        all_of(
            instance_of(list),
            has_items(hidden.base_name, kept.base_name, extra.base_name),
        ),
        "the saved explicit list must keep the hidden Disabled model and add the ticked one",
    )


# @case models-tab-hides-disabled-models_TC_003
# Ticking every visible row still saves an allow_list while the stored list holds a
# hidden name (storesHiddenModels, ProjectModelsSection.tsx:204-210).
@pytest.mark.xdist_group(name="model_status")
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_ticking_every_visible_row_keeps_a_hidden_disabled_model_in_the_stored_list(
    page,
    client,
    project_admin_setup,
    project_admin_setup_client,
    admin_project_utils,
    llm_model_status_utils,
    status_test_models,
):
    project_name = project_admin_setup[0]
    hidden, kept = status_test_models
    extra = selectable_chat_models(client, exclude=(hidden.base_name, kept.base_name))[
        0
    ]
    admin_project_utils.restrict_models(
        project_name, [hidden.base_name, kept.base_name], kept.base_name
    )
    llm_model_status_utils.apply_status(
        hidden.base_name, ModelStatus.DISABLED, project_admin_setup_client
    )

    models = _open_models_tab(page, project_name)
    models.should_not_list_model(hidden.label)
    models.tick_every_visible_row()
    models.apply_changes()
    models.toast.should_show_success(MODEL_SETTINGS_SAVED_TOAST)

    stored = admin_project_utils.get_project_detail(project_name).allowed_models
    assert_that(
        stored,
        all_of(
            instance_of(list),
            has_items(hidden.base_name, kept.base_name, extra.base_name),
        ),
        "ticking every visible row must save an explicit list that keeps the hidden Disabled model",
    )


# @case models-tab-hides-disabled-models_TC_004
# From 'all', the new allow_list holds only ticked visible entries and never adds a
# hidden name (projectModelConfiguration.ts:95); after re-enable, an allow_list row is
# ticked only when stored (projectModelConfiguration.ts:69, ProjectModelsSection.tsx:334).
@pytest.mark.xdist_group(name="model_status")
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_narrowing_with_a_disabled_model_stores_only_ticked_models_and_it_returns_unticked(
    page,
    client,
    project_admin_setup,
    project_admin_setup_client,
    admin_project_utils,
    llm_model_status_utils,
    status_test_models,
):
    project_name = project_admin_setup[0]
    hidden, unticked = status_test_models
    ticked = selectable_chat_models(
        client, exclude=(hidden.base_name, unticked.base_name)
    )[0]
    llm_model_status_utils.apply_status(
        hidden.base_name, ModelStatus.DISABLED, project_admin_setup_client
    )

    models = _open_models_tab(page, project_name)
    models.should_not_list_model(hidden.label)
    models.set_model_checked(unticked.label, False)
    models.apply_changes()
    models.toast.should_show_success(MODEL_SETTINGS_SAVED_TOAST)

    stored = admin_project_utils.get_project_detail(project_name).allowed_models
    assert_that(
        stored,
        all_of(
            instance_of(list),
            has_item(ticked.base_name),
            is_not(has_item(hidden.base_name)),
            is_not(has_item(unticked.base_name)),
        ),
        "the narrowed list must hold the ticked visible models only",
    )

    llm_model_status_utils.apply_status(
        hidden.base_name, ModelStatus.ENABLED, project_admin_setup_client
    )
    models = _open_models_tab(page, project_name)
    models.should_list_model(hidden.label, checked=False)
    models.set_model_checked(hidden.label, True)
    models.apply_changes()
    models.toast.should_show_success(MODEL_SETTINGS_SAVED_TOAST)

    stored = admin_project_utils.get_project_detail(project_name).allowed_models
    assert_that(
        stored,
        all_of(instance_of(list), has_item(hidden.base_name)),
        "the re-enabled model must be stored once it is ticked and saved",
    )


# @case models-tab-hides-disabled-models_TC_005
# restrictsHiddenModels keeps the save an allow_list when every visible row is ticked
# (projectModelConfiguration.ts:58, ProjectModelsSection.tsx:209); Reset stays enabled
# (ProjectModelsSection.tsx:124) and its save calls resetSettings (ProjectModelsSection.tsx:235).
@pytest.mark.xdist_group(name="model_status")
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_explicit_list_lacking_a_disabled_model_stays_explicit_until_reset(
    page,
    project_admin_setup,
    project_admin_setup_client,
    admin_project_utils,
    llm_model_status_utils,
    status_test_models,
):
    project_name = project_admin_setup[0]
    hidden, toggled = status_test_models
    llm_model_status_utils.apply_status(
        hidden.base_name, ModelStatus.DISABLED, project_admin_setup_client
    )

    models = _open_models_tab(page, project_name)
    models.set_model_checked(toggled.label, False)
    models.apply_changes()
    models.toast.should_show_success(MODEL_SETTINGS_SAVED_TOAST)

    models.set_model_checked(toggled.label, True)
    models.apply_changes()
    stored = admin_project_utils.get_project_detail(project_name).allowed_models
    assert_that(
        stored,
        all_of(
            instance_of(list),
            has_item(toggled.base_name),
            is_not(has_item(hidden.base_name)),
        ),
        "re-ticking every visible row must keep an explicit list without the Disabled model",
    )

    models.should_have_reset_enabled()
    models.reset_to_global_settings()
    models.apply_changes()
    models.toast.should_show_success(MODEL_SETTINGS_SAVED_TOAST)
    stored = admin_project_utils.get_project_detail(project_name).allowed_models
    assert_that(stored, none(), "Reset must return the project to all models")


# @case models-tab-hides-disabled-models_TC_006
# A default missing from the available models is invalid: 'Selected model is not
# available' (projectModelConfiguration.ts:156, DefaultModelsSelector.tsx:125); Apply is
# disabled while !defaultIsValid (ModelSettingsActions.tsx:57, ProjectModelsSection.tsx:246).
@pytest.mark.xdist_group(name="model_status")
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_disabled_project_default_blocks_saving_until_an_available_default_is_chosen(
    page,
    client,
    project_admin_setup,
    project_admin_setup_client,
    admin_project_utils,
    llm_model_status_utils,
    status_test_models,
):
    project_name = project_admin_setup[0]
    stale_default, new_default = status_test_models
    pending_change = selectable_chat_models(
        client, exclude=(stale_default.base_name, new_default.base_name)
    )[0]
    admin_project_utils.set_default_model(project_name, stale_default.base_name)
    llm_model_status_utils.apply_status(
        stale_default.base_name, ModelStatus.DISABLED, project_admin_setup_client
    )

    models = _open_models_tab(page, project_name)
    models.should_show_default_model_error()
    models.should_not_offer_model_in_default_dropdown(
        DEFAULT_SELECT_LABEL, stale_default.label
    )
    models.set_model_checked(pending_change.label, False)
    models.should_have_apply_disabled()
    assert_that(
        admin_project_utils.get_project_detail(project_name).default_model,
        equal_to(stale_default.base_name),
        "nothing may be saved while the project default is Disabled",
    )

    models.select_default_model(DEFAULT_SELECT_LABEL, new_default.label)
    models.apply_changes()
    models.toast.should_show_success(MODEL_SETTINGS_SAVED_TOAST)
    assert_that(
        admin_project_utils.get_project_detail(project_name).default_model,
        equal_to(new_default.base_name),
        "the chosen available default must be saved",
    )


# @case models-tab-hides-disabled-models_TC_007
# The draft default is the first platform-enabled isDefault candidate
# (ProjectModelsSection.tsx:77); the backend moves 'default' off a disabled global default
# to the next selectable model (llm_service.py:1037-1047, :469-474).
@pytest.mark.xdist_group(name="model_status")
@pytest.mark.project
@pytest.mark.budget
@pytest.mark.ui
def test_reset_to_global_settings_proposes_the_next_enabled_model_for_a_disabled_global_default(
    page,
    client,
    project_admin_setup,
    project_admin_setup_client,
    admin_project_utils,
    llm_model_status_utils,
    saved_global_default,
    status_test_model,
):
    project_name = project_admin_setup[0]
    disabled_default = status_test_model
    llm_model_status_utils.set_default(disabled_default.base_name)
    llm_model_status_utils.wait_until_catalog_default(
        lambda default: default == disabled_default.base_name,
        disabled_default.base_name,
        project_admin_setup_client,
    )
    llm_model_status_utils.apply_status(
        disabled_default.base_name, ModelStatus.DISABLED, project_admin_setup_client
    )
    next_default = llm_model_status_utils.wait_until_catalog_default(
        lambda default: default not in (None, disabled_default.base_name),
        f"an Enabled model other than {disabled_default.base_name}",
        project_admin_setup_client,
    )
    next_default_label = global_default_model_label(client)
    assert_that(
        next_default_label,
        is_not(equal_to(disabled_default.label)),
        "the catalog must flag another model as the global default",
    )
    project_default = selectable_chat_models(
        client, exclude=(disabled_default.base_name, next_default)
    )[0]
    admin_project_utils.set_default_model(project_name, project_default.base_name)

    models = _open_models_tab(page, project_name)
    models.should_have_default_model_selected(
        DEFAULT_SELECT_LABEL, project_default.label
    )
    models.reset_to_global_settings()
    models.should_have_default_model_selected(DEFAULT_SELECT_LABEL, next_default_label)
    models.should_not_have_default_model_selected(
        DEFAULT_SELECT_LABEL, disabled_default.label
    )
