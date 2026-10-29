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

import re
from typing import Optional

from hamcrest import assert_that, is_not, empty, matches_regexp
from playwright.sync_api import expect
from reportportal_client import step

from codemie_test_harness.tests.test_data.google_datasource_test_data import (
    GOOGLE_DOC_GUIDE_URL,
    get_google_doc_url,
)
from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.pageobject.components.create_user_integration_dialog import (
    CreateUserIntegrationDialog,
)
from codemie_test_harness.tests.ui.pageobject.components.project_selector import (
    ProjectSelector,
)
from codemie_test_harness.tests.ui.pageobject.datasources.datasource_sidebar import (
    DataSourceSidebar,
)
from codemie_test_harness.tests.ui.test_data.datasource_test_data import (
    DataSourceType,
    SUMMARIZATION_METHODS_LIST,
    DATA_SOURCE_TYPES_LIST,
    FILE_INSTRUCTIONS,
    GOOGLE_EXAMPLE,
    EMPTY_NAME_ERROR,
    EMPTY_DESCRIPTION_ERROR,
    EMPTY_REPO_LINK_ERROR,
    EMPTY_BRANCH_ERROR,
    EMPTY_CQL_ERROR,
    EMPTY_JQL_ERROR,
    EMPTY_FILE_ERROR,
    EMPTY_GOOGLE_LINK_ERROR,
    ADO_INSTRUCTIONS,
    GOOGLE_DETAILED_EXAMPLE,
    CLONE_PAGE_TITLE,
    CLONE_SIDEBAR_TITLE,
    CLONE_SIDEBAR_SUBTITLE,
)
from codemie_test_harness.tests.utils.base_utils import get_random_name


class CreateEditDatasourcePage(BasePage):
    """Create Data Source page object with property-based element locators."""

    page_url = "/data-sources/create"

    def __init__(self, page):
        super().__init__(page)
        self.sidebar = DataSourceSidebar(page)
        self.selector = ProjectSelector(page)
        self.create_user_integration_dialog = CreateUserIntegrationDialog(page)

    # -----------------
    # Page Elements
    # -----------------

    @property
    def save_reindex_button(self):
        return self.page.locator("button:has-text('Save & Reindex')")

    @property
    def save_button(self):
        """'Save' button — distinct from 'Save & Reindex' (does not trigger reindexing).

        Scoped to `main` where the header action buttons now live (Cancel / Save /
        Save & Reindex moved out of the aside into the page header area).
        """
        return self.page.get_by_role("main").get_by_role(
            "button", name="Save", exact=True
        )

    # Help button and panel
    @property
    def help_button(self):
        """Help button in bottom right corner."""
        return self.page.get_by_role("button", name="Help").filter(
            has=self.page.locator("svg")
        )

    @property
    def help_panel_title(self):
        """Help panel title 'CodeMie Helper'."""
        return self.page.get_by_role("heading", name="CodeMie Helper", level=3)

    @property
    def help_panel_close_button(self):
        """Close button in help panel.
        Uses exact=True to avoid matching toast notification 'Close notification' button.
        """
        return self.page.get_by_role("button", name="Close", exact=True)

    @property
    def help_work_with_datasources_button(self):
        """'How to work with Data Sources' button in help panel."""
        return self.page.get_by_role("button", name="How to work with Data Sources")

    @property
    def help_create_git_datasource_button(self):
        """'How to create Git data source' button in help panel."""
        return self.page.get_by_role("button", name="How to create Git data source")

    @property
    def shared_with_project_switch(self):
        return self.page.locator("input#projectSpaceVisible + span")

    @property
    def automatic_credentials_lookup_switch(self):
        """Toggle visual element for 'Automatic Credentials Lookup'.
        Default state: ON (checked) — hides the integration dropdown.
        When turned OFF — the integration dropdown becomes visible.
        The toggle input has no id, so it is located via its label text.
        """
        return (
            self.page.locator("label")
            .filter(has_text="Automatic Credentials Lookup")
            .locator("input[role='switch'] + span.switch")
        )

    @property
    def automatic_credentials_lookup_input(self):
        """Checkbox input for 'Automatic Credentials Lookup' toggle (for state checking)."""
        return (
            self.page.locator("label")
            .filter(has_text="Automatic Credentials Lookup")
            .locator("input[role='switch']")
        )

    @property
    def name_input(self):
        return self.page.locator("input#name")

    @property
    def disabled_name_input(self):
        return self.page.locator("input#name[disabled]")

    @property
    def error_name_input(self):
        return self.page.get_by_text("Data source name is required")

    @property
    def description_input(self):
        return self.page.locator("textarea#description")

    @property
    def error_description_input(self):
        return self.page.get_by_text("Description is required")

    @property
    def datasource_type_selector(self):
        return self.page.locator('span#indexType input[type="text"]')

    @property
    def datasource_type_dropdown(self):
        return self.page.locator("span#indexType button")

    @property
    def integration_input(self):
        # The label "Select integration..." and the .p-dropdown are siblings inside
        # a div.flex.flex-col.gap-2 container — use filter(has=...) to scope correctly.
        return (
            self.page.locator("div.flex.flex-col.gap-2")
            .filter(has=self.page.locator('label:has-text("Integration")'))
            .locator(".p-dropdown")
        )

    @property
    def add_integration_button(self):
        return self.page.locator('button:has-text("Add User Integration")')

    @property
    def integration_dropdown(self):
        return self.integration_input.locator(".p-dropdown-label")

    @property
    def refresh_integrations_button(self):
        """Refresh button next to the integrations dropdown.

        Uses aria-label='Refresh integrations' set on the button in IntegrationSection.tsx.
        """
        return self.page.get_by_role("button", name="Refresh integrations")

    def dropdown_values(self, value: str):
        if value == DataSourceType.GIT.value:
            # "Git" is now a text-prefix of the "Git FAQ" option too. Other
            # values (e.g. "X-ray", "SVN") rely on substring matching because
            # their options carry a glued "NEW" badge suffix ("X-rayNEW"), so
            # only disambiguate this specific, newly-introduced collision.
            return self.page.get_by_role("option", name=value, exact=True)
        return self.page.locator("[role='option']").filter(has_text=value)

    # -------------------------------
    # Clone page elements
    # -------------------------------

    @property
    def clone_page_title(self):
        """Page header title of the clone route ('Clone Data Source')."""
        return self.page.get_by_role("heading", name=CLONE_PAGE_TITLE, exact=True)

    def block_message(self, message: str):
        """Message shown instead of the form when a clone is not possible."""
        return self.page.get_by_text(message, exact=True)

    def uploaded_file_name(self, file_name: str):
        """File name text shown in the form's file list."""
        return self.page.get_by_text(file_name, exact=True)

    # -------------------------------
    # Navigation methods
    # -------------------------------
    @step
    def navigate_to(self):
        """
        Navigate to the Create DataSource page.

        Returns:
            self: Returns the page object for method chaining
        """
        self.page.goto(self.page_url)
        self.wait_for_page_load()
        expect(self.name_input).to_be_visible(timeout=30000)

        return self

    # -------------------------------
    # Help panel methods
    # -------------------------------
    @step
    def click_help_button(self):
        """Click the help button in bottom right corner."""
        self.help_button.click()
        expect(self.help_panel_title).to_be_visible()
        return self

    @step
    def close_help_panel(self):
        """Close the help panel."""
        self.help_panel_close_button.click()
        expect(self.help_panel_title).to_be_hidden()
        return self

    @step
    def should_have_help_button_visible(self):
        """Verify that the help button is visible."""
        expect(self.help_button).to_be_visible()
        return self

    @step
    def should_have_help_panel_visible(self):
        """Verify that the help panel is visible."""
        expect(self.help_panel_title).to_be_visible()
        expect(self.help_work_with_datasources_button).to_be_visible()
        expect(self.help_create_git_datasource_button).to_be_visible()
        return self

    # -------------------------------
    # Git DataSource Type Elements
    # -------------------------------

    @property
    def summarization_method_input(self):
        return self.page.locator('span#repoIndexType input[type="text"]')

    @property
    def summarization_method_dropdown(self):
        return self.page.locator("span#repoIndexType button")

    @property
    def repo_link_input(self):
        return self.page.locator("input#repoLink")

    @property
    def error_repo_link_input(self):
        return self.page.get_by_text("Repo Link is required")

    @property
    def branch_input(self):
        return self.page.locator("input#repoBranch")

    @property
    def error_branch_input(self):
        return self.page.get_by_text("Branch is required")

    @property
    def files_filter_input(self):
        return self.page.locator("textarea#filesFilter")

    @property
    def embeddings_model_input(self):
        return self.page.locator('span#embeddingsModel input[type="text"]')

    @property
    def embeddings_model_dropdown(self):
        return self.page.locator("span#embeddingsModel button")

    # -------------------------------
    # Confluence DataSource Type Elements
    # -------------------------------

    @property
    def cql_query_input(self):
        return self.page.locator("input#cql")

    @property
    def error_cql_query_input(self):
        return self.page.get_by_text("CQL is required")

    # -------------------------------
    # Jira And X-ray DataSource Type Elements
    # -------------------------------

    @property
    def jql_input(self):
        return self.page.locator("input#jql")

    @property
    def error_jql_query_input(self):
        return self.page.get_by_text("JQL is required")

    # -------------------------------
    # File DataSource Type Elements
    # -------------------------------

    @property
    def file_drop_zone(self):
        """Drop zone area for file upload (replaced old 'Select file' button)."""
        return self.page.locator("div.bg-surface-base-dropzone.cursor-pointer")

    @property
    def file_drop_zone_label(self):
        """'Upload or drop files' label text inside the drop zone."""
        return self.page.locator("div.bg-surface-base-dropzone span.underline")

    @property
    def input_file(self):
        return self.page.locator('input[type="file"]')

    @property
    def remove_file_icon(self):
        return self.page.locator("svg.cursor-pointer")

    @property
    def files_info_text(self):
        return self.page.locator("label[for='files'] ~ div span.mt-0\\.5")

    @property
    def error_files_info_text(self):
        return self.page.get_by_text("At least one file is required")

    @property
    def file_input_field(self):
        """Filename text shown for a selected/uploaded file in the file list.

        Note: the browser only ever knows the selected File object's own name
        (e.g. "test.zip"); server-side extraction of an archive's contents
        happens after upload, so this always reflects the uploaded file's own
        name, never names of files extracted from inside it.
        """
        return self.page.locator("div.bg-surface-base-content span.truncate")

    # -------------------------------
    # Google DataSource Type Elements
    # -------------------------------

    @property
    def google_query_input(self):
        return self.page.locator("input#googleDoc")

    @property
    def error_google_query_input(self):
        return self.page.get_by_text("Google Docs link is required")

    @property
    def google_instructions(self):
        return self.page.locator(
            '[data-onboarding="datasource-google-fields"]'
        ).locator("span.mt-0\\.5")

    # -------------------------------
    # ADO DataSource Type Elements
    # -------------------------------

    @property
    def ado_wiki_name_input(self):
        return self.page.locator("input#wikiName")

    @property
    def page_path_input(self):
        return self.page.locator("input#wikiQuery")

    @property
    def ado_instructions(self):
        return self.page.locator("div.flex.text-text-quaternary.text-xs.mb-3")

    # -------------------------------
    # xWiki DataSource Type Elements
    # -------------------------------

    @property
    def xwiki_space_input(self):
        return self.page.locator("input#xwikiSpace")

    @property
    def xwiki_wiki_input(self):
        return self.page.locator("input#xwikiWiki")

    @property
    def xwiki_option(self):
        """The 'xWiki' entry in the open Datasource Type dropdown, badge included."""
        return self.page.locator("[role='option']").filter(has_text="xWiki")

    # -------------------------------
    # Provider (DSP) DataSource Type Elements
    # -------------------------------

    @property
    def provider_repositories_input(self):
        """The AICE combined provider's `Repositories` field.
        Rendered as a <textarea>, unlike the other provider fields' <input>.
        """
        return self.page.locator("textarea#repositories")

    @property
    def provider_graphdb_username_input(self):
        return self.page.locator("input#graphdb_username")

    @property
    def provider_graphdb_password_input(self):
        return self.page.locator("input#graphdb_password")

    @property
    def provider_graphdb_tenant_url_input(self):
        return self.page.locator("input#graphdb_tenant_url")

    def provider_field_error(self, message: str):
        """Validation error message element for a provider field, e.g. 'Api Url is required'."""
        return self.page.locator(".input-error-message").filter(has_text=message)

    # -------------------------------
    # Reindex Schedule Elements
    # -------------------------------

    @property
    def reindex_type_dropdown(self):
        """Reindex Type dropdown - finds by label text 'Reindex Type'"""
        return (
            self.page.locator("div.flex.flex-col.gap-2")
            .filter(has=self.page.get_by_text("Reindex Type", exact=True))
            .locator(".p-dropdown")
        )

    @property
    def reindex_type_trigger(self):
        """Reindex Type dropdown trigger button"""
        return (
            self.page.locator("div.flex.flex-col.gap-2")
            .filter(has=self.page.get_by_text("Reindex Type", exact=True))
            .locator(".p-dropdown-trigger")
        )

    @property
    def reindex_type_value(self):
        """Reindex Type dropdown selected value"""
        return (
            self.page.locator("div.flex.flex-col.gap-2")
            .filter(has=self.page.get_by_text("Reindex Type", exact=True))
            .locator(".p-dropdown-label")
        )

    @property
    def expression_dropdown(self):
        """Expression dropdown - finds by label text 'Expression'"""
        return (
            self.page.locator("div.flex.flex-col.gap-2")
            .filter(has=self.page.get_by_text("Expression", exact=True))
            .locator(".p-dropdown")
        )

    @property
    def expression_trigger(self):
        """Expression dropdown trigger button"""
        return (
            self.page.locator("div.flex.flex-col.gap-2")
            .filter(has=self.page.get_by_text("Expression", exact=True))
            .locator(".p-dropdown-trigger")
        )

    @property
    def expression_value(self):
        """Expression dropdown selected value"""
        return (
            self.page.locator("div.flex.flex-col.gap-2")
            .filter(has=self.page.get_by_text("Expression", exact=True))
            .locator(".p-dropdown-label")
        )

    # -------------------------------
    # YAML Configuration Elements
    # -------------------------------

    @property
    def yaml_config_editor(self):
        """YAML Configuration ACE editor"""
        return self.page.locator('[data-name="yaml_config"]')

    @property
    def yaml_config_text_layer(self):
        """YAML Configuration text layer - contains all text content"""
        return self.page.locator('[data-name="yaml_config"] .ace_text-layer')

    @property
    def yaml_config_lines(self):
        """YAML Configuration individual lines"""
        return self.page.locator('[data-name="yaml_config"] .ace_line')

    # -----------------
    # Action Methods
    # -----------------
    @step
    def fill_name(self, value: str):
        self.name_input.fill(value)
        return self

    @step
    def clear_name(self):
        self.name_input.clear()
        return self

    @step
    def fill_description(self, value: str):
        self.description_input.fill(value)
        return self

    @step
    def select_project(self, value: str):
        self.selector.search_and_select_project(value)
        # self.dropdown_values(value).click()
        return self

    @step
    def toggle_shared_with_project(self):
        self.shared_with_project_switch.click()
        return self

    @step
    def select_datasource_type(self, value: str):
        self.datasource_type_dropdown.click()
        self.dropdown_values(value).click()
        return self

    @step
    def select_integration(self, value: str):
        self.integration_dropdown.click()
        self.dropdown_values(value).click()
        return self

    @step
    def click_create(self):
        self.create_button.click()
        return self

    @step
    def click_cancel(self):
        self.cancel_button.click()
        return self

    @step
    def click_back(self):
        self.back_button.click()
        return self

    @step
    def click_save_and_reindex(self):
        """Click Save & Reindex button to save datasource changes."""
        self.save_reindex_button.click()
        return self

    @step
    def click_add_integration_button(self):
        """Click 'Add User Integration' to open the Create User Integration dialog."""
        self.add_integration_button.click()
        return self

    @step
    def click_refresh_integrations(self):
        """Click the Refresh button and wait for the async refresh to complete.

        The Refresh button is disabled while indexSettings() is in-flight; waiting
        for it to re-enable confirms the update has been applied before the next step.
        """
        self.refresh_integrations_button.click()
        expect(self.refresh_integrations_button).to_be_enabled(timeout=30000)
        return self

    def _base_create_datasource(
        self,
        name: Optional[str],
        project_name: Optional[str],
        description: Optional[str],
        datasource_type: DataSourceType,
        shared: bool = False,
        integration: Optional[str] = None,
    ):
        """
        Fills common fields for any DataSource type
        (name, description, project, type, shared, integration) but does not click 'Create'.

        Args:
            name: Optional[name], defaults to random if not provided
            project_name: Optional[str], selects a project if provided
            description: Optional[str], defaults to random if empty
            datasource_type: DataSourceType enum member
            shared: If True, enable 'Shared with project' toggle
            integration: Optionally select integration string

        Returns:
            The name used for the datasource
        """
        name = name or get_random_name()
        description = description or get_random_name()
        self.fill_name(name)
        self.fill_description(description)
        if project_name:
            self.selector.search_and_select_project(project_name)
        self.select_datasource_type(datasource_type)
        if shared:
            self.toggle_shared_with_project()
        if integration:
            self.select_integration(integration)
        return name

    @step
    def create_git_datasource(
        self,
        name: Optional[str] = None,
        project_name: Optional[str] = None,
        description: Optional[str] = None,
        shared: bool = False,
        repo_link: Optional[str] = None,
        branch: Optional[str] = None,
        summarization_method: Optional[str] = None,
        embeddings_model: Optional[str] = None,
        integration: Optional[str] = None,
    ):
        """
        Creates a Git DataSource with required and optional fields.
        """
        name = self._base_create_datasource(
            name, project_name, description, DataSourceType.GIT, shared, integration
        )
        if repo_link:
            self.fill_repo_link(repo_link)
        if branch:
            self.fill_branch(branch)
        if summarization_method:
            self.select_summarization_method(summarization_method)
        if embeddings_model:
            self.select_embeddings_model(embeddings_model)
        self.click_create()
        return name

    @step
    def create_confluence_datasource(
        self,
        name: Optional[str] = None,
        project_name: Optional[str] = None,
        description: Optional[str] = None,
        shared: bool = False,
        cql_query: Optional[str] = None,
        integration: Optional[str] = None,
    ):
        """
        Creates a Confluence DataSource with required and optional fields.
        """
        name = self._base_create_datasource(
            name,
            project_name,
            description,
            DataSourceType.CONFLUENCE,
            shared,
            integration,
        )
        if cql_query:
            self.fill_cql_query(cql_query)
        self.click_create()
        return name

    @step
    def create_jira_datasource(
        self,
        name: Optional[str] = None,
        project_name: Optional[str] = None,
        description: Optional[str] = None,
        shared: bool = False,
        jql_query: Optional[str] = None,
        integration: Optional[str] = None,
    ):
        """
        Creates a Jira DataSource with required and optional fields.
        """
        name = self._base_create_datasource(
            name, project_name, description, DataSourceType.JIRA, shared, integration
        )
        if jql_query:
            self.fill_jql_query(jql_query)
        self.click_create()
        return name

    @step
    def create_file_datasource(
        self,
        name: Optional[str] = None,
        project_name: Optional[str] = None,
        description: Optional[str] = None,
        shared: bool = False,
        file_path: Optional[str] = None,
        integration: Optional[str] = None,
    ):
        """
        Creates a File DataSource with required and optional fields.
        """
        name = self._base_create_datasource(
            name, project_name, description, DataSourceType.FILE, shared, integration
        )
        if file_path:
            self.select_file(file_path)
        self.click_create()
        return name

    @step
    def create_google_datasource(
        self,
        name: Optional[str] = None,
        project_name: Optional[str] = None,
        description: Optional[str] = None,
        shared: bool = False,
        google_doc_link: Optional[str] = None,
        integration: Optional[str] = None,
    ):
        """
        Creates a Google DataSource with required and optional fields.
        """
        name = self._base_create_datasource(
            name, project_name, description, DataSourceType.GOOGLE, shared, integration
        )
        if google_doc_link:
            self.fill_google_doc_link(google_doc_link)
        self.click_create()
        return name

    @step
    def create_ado_wiki_datasource(
        self,
        name: Optional[str] = None,
        project_name: Optional[str] = None,
        description: Optional[str] = None,
        shared: bool = False,
        wiki_name: Optional[str] = None,
        integration: Optional[str] = None,
    ):
        """
        Creates a ADO DataSource with required and optional fields.
        """
        name = self._base_create_datasource(
            name, project_name, description, DataSourceType.ADO, shared, integration
        )
        if wiki_name:
            self.fill_ado_wiki_name(wiki_name)
        self.click_create()
        return name

    # -------------------------------
    # Embedding Models Methods
    # -------------------------------

    @step
    def should_see_embeddings_model_field(self):
        expect(self.embeddings_model_input).to_be_visible()
        expect(self.embeddings_model_dropdown).to_be_visible()
        return self

    @step
    def should_see_embeddings_model_dropdown_values(self, labels: list):
        self.embeddings_model_dropdown.click()
        for model in labels:
            expect(self.dropdown_values(model)).to_be_visible()
        self.embeddings_model_dropdown.click()
        return self

    # -------------------------------
    # Git DataSource Type Methods
    # -------------------------------

    @step
    def select_summarization_method(self, value: str):
        self.summarization_method_dropdown.click()
        self.dropdown_values(value).click()
        return self

    @step
    def fill_repo_link(self, value: str):
        self.repo_link_input.fill(value)
        return self

    @step
    def fill_branch(self, value: str):
        self.branch_input.fill(value)
        return self

    @step
    def fill_files_filter(self, value: str):
        self.files_filter_input.fill(value)
        return self

    @step
    def select_embeddings_model(self, value: str):
        self.embeddings_model_dropdown.click()
        self.dropdown_values(value).click()
        return self

    # -------------------------------
    # Confluence DataSource Type Methods
    # -------------------------------

    @step
    def fill_cql_query(self, cql: str):
        self.cql_query_input.fill(cql)
        return self

    # -------------------------------
    # Jira DataSource Type Methods
    # -------------------------------

    @step
    def fill_jql_query(self, jql: str):
        self.jql_input.fill(jql)
        return self

    # -------------------------------
    # File DataSource Type Methods
    # -------------------------------

    @step
    def select_file(self, path: str):
        self.input_file.set_input_files(path)
        return self

    @step
    def add_file(self):
        """Click the file drop zone to trigger additional file selection."""
        self.file_drop_zone.click()
        return self

    # -------------------------------
    # Google DataSource Type Methods
    # -------------------------------

    @step
    def fill_google_doc_link(self, link: str):
        self.google_query_input.fill(link)
        return self

    # -------------------------------
    # ADO DataSource Type Methods
    # -------------------------------

    @step
    def fill_ado_wiki_name(self, name: str):
        self.ado_wiki_name_input.fill(name)
        return self

    @step
    def fill_ado_page_path(self, path: str):
        self.page_path_input.fill(path)
        return self

    # -------------------------------
    # Provider (DSP) DataSource Type Methods
    # -------------------------------

    @step
    def fill_provider_repositories(self, value: str):
        self.provider_repositories_input.fill(value)
        return self

    @step
    def fill_provider_graphdb_username(self, value: str):
        self.provider_graphdb_username_input.fill(value)
        return self

    @step
    def fill_provider_graphdb_password(self, value: str):
        self.provider_graphdb_password_input.fill(value)
        return self

    @step
    def fill_provider_graphdb_tenant_url(self, value: str):
        self.provider_graphdb_tenant_url_input.fill(value)
        return self

    @step
    def select_provider_datasource_type(self, provider_name: str):
        """Select a DSP-based (Provider) entry in the Datasource Type dropdown.

        Providers are listed as '<provider name, Title Cased> - <toolkit
        name>' (verified live: a provider named 'zzprobe_vrt_xxx' is listed
        as 'Zzprobe Vrt Xxx - <ToolkitName>'). Matching on the trailing,
        underscore-free random-suffix segment of a `get_random_name()`-style
        provider name avoids depending on the exact Title Case / toolkit-name
        half of the label, since `dropdown_values` already does a
        case-insensitive substring match.
        """
        self.datasource_type_dropdown.click()
        self.dropdown_values(provider_name.split("_")[-1]).click()
        return self

    @step
    def click_save(self):
        """Click the 'Save' button (persists changes without triggering reindexing)."""
        self.save_button.click()
        return self

    # -------------------------------
    # Reindex Schedule Methods
    # -------------------------------

    @step
    def select_reindex_type(self, value: str):
        """Select reindex type from dropdown (e.g., 'Scheduler', 'Manual')"""
        self.reindex_type_trigger.click()
        self.dropdown_values(value).click()
        return self

    @step
    def select_expression(self, value: str):
        """Select schedule expression from dropdown"""
        self.expression_trigger.click()
        self.dropdown_values(value).click()
        return self

    # -----------------
    # Verification Methods
    # -----------------

    @step
    def get_name_value(self) -> str:
        """
        Return the current value of the datasource name/alias input field.

        Returns:
            str: Current name field value
        """
        return self.name_input.input_value()

    @step
    def should_have_name_matching_pattern(self, pattern: str):
        """
        Assert that the datasource name field value matches the provided regex pattern.

        Args:
            pattern (str): Regex pattern string to match against the name value

        Returns:
            self: For method chaining
        """
        name_value = self.get_name_value()
        assert_that(name_value, matches_regexp(pattern))
        return self

    @step
    def should_have_name_not_empty(self):
        """
        Assert that the datasource name field is pre-populated (not empty).

        Returns:
            self: For method chaining
        """
        name_value = self.get_name_value()
        assert_that(name_value, is_not(empty()))
        return self

    @step
    def should_have_name_empty(self):
        """
        Assert that the datasource name field is empty (not pre-populated).

        Returns:
            self: For method chaining
        """
        name_value = self.get_name_value()
        assert_that(name_value, empty())
        return self

    @step
    def should_see_name_input(self):
        expect(self.name_input).to_be_visible()
        return self

    @step
    def should_see_disabled_name_input(self, name: str):
        expect(self.disabled_name_input).to_be_visible()
        expect(self.disabled_name_input).to_have_value(name)
        return self

    @step
    def should_see_description_input(self):
        expect(self.description_input).to_be_visible()
        return self

    @step
    def should_see_shared_with_project_switch(self):
        expect(self.shared_with_project_switch).to_be_visible()
        return self

    @step
    def should_see_datasource_type_input(self):
        expect(self.datasource_type_selector).to_be_visible()
        # default value is Git
        expect(self.datasource_type_selector).to_have_value("Git")
        return self

    @step
    def should_see_datasource_type_dropdown_values(self):
        self.datasource_type_dropdown.click()
        for ds_type in DATA_SOURCE_TYPES_LIST:
            expect(self.dropdown_values(ds_type)).to_be_visible()
        self.datasource_type_dropdown.click()

    @step
    def should_see_create_button(self):
        expect(self.create_button).to_be_visible()
        return self

    @step
    def should_see_cancel_button(self):
        expect(self.cancel_button).to_be_visible()
        return self

    @step
    def should_see_save_reindex_button(self):
        expect(self.save_reindex_button).to_be_visible()
        return self

    @step
    def should_see_integration_input(self):
        expect(self.integration_input).to_be_visible()
        return self

    @step
    def should_see_add_integration_button(self):
        expect(self.add_integration_button).to_be_visible()
        return self

    @step
    def should_see_automatic_credentials_lookup_switch(self):
        """Verify that the Automatic Credentials Lookup toggle is visible."""
        expect(
            self.page.locator("label").filter(has_text="Automatic Credentials Lookup")
        ).to_be_visible()
        return self

    @step
    def should_see_integration_input_or_button(self):
        """
        Verifies that the integration section is visible in one of the expected forms:
        - The 'Automatic Credentials Lookup' toggle (default ON state, hides dropdown)
        - The integration dropdown input (toggle OFF, integration configured)
        - The 'Add User Integration' button (toggle OFF, no integration configured)
        """
        try:
            self.should_see_automatic_credentials_lookup_switch()
        except AssertionError:
            try:
                self.should_see_integration_input()
            except AssertionError:
                self.should_see_add_integration_button()
        return self

    @step
    def should_see_refresh_integrations_button(self):
        """Assert the Refresh button is visible next to the integrations dropdown."""
        expect(self.refresh_integrations_button).to_be_visible()
        return self

    @step
    def should_see_integration_in_dropdown(self, alias: str):
        """Open the integration dropdown and assert the given alias appears as an option.

        Uses force=True because PrimeReact dropdown label has a click-interception
        issue with its parent container after a disabled→enabled state transition.
        Escape is in a finally block so the dropdown is always closed even on
        assertion failure.
        """
        self.integration_dropdown.click(force=True)
        try:
            expect(self.dropdown_values(alias)).to_be_visible()
        finally:
            self.page.keyboard.press("Escape")
        return self

    @step
    def should_not_see_integration_in_dropdown(self, alias: str):
        """Assert the given integration alias is not present in the integrations dropdown.

        The dropdown must be opened first: PrimeReact removes all [role='option']
        nodes from the DOM when the overlay is closed, so asserting hidden without
        opening the dropdown would trivially pass for any alias.
        """
        self.integration_dropdown.click(force=True)
        try:
            expect(self.dropdown_values(alias)).not_to_be_visible()
        finally:
            self.page.keyboard.press("Escape")
        return self

    @step
    def should_see_selected_integration(self, integration: str):
        expect(self.integration_input).to_have_text(integration)
        return self

    @step
    def should_see_main_fields(self):
        self.should_see_name_input()
        self.should_see_description_input()
        self.selector.should_see_multiselect()
        self.should_see_shared_with_project_switch()
        self.should_see_datasource_type_input()
        self.should_see_create_button()
        self.should_see_cancel_button()
        self.should_see_datasource_type_dropdown_values()
        return self

    @step
    def should_see_error_for_empty_main_fields(self):
        expect(self.error_name_input).to_be_visible()
        expect(self.error_name_input).to_have_text(EMPTY_NAME_ERROR)
        expect(self.error_description_input).to_be_visible()
        expect(self.error_description_input).to_have_text(EMPTY_DESCRIPTION_ERROR)
        return self

    @step
    def should_see_error_for_empty_git_fields(self):
        expect(self.error_repo_link_input).to_be_visible()
        expect(self.error_repo_link_input).to_have_text(EMPTY_REPO_LINK_ERROR)
        expect(self.error_branch_input).to_be_visible()
        expect(self.error_branch_input).to_have_text(EMPTY_BRANCH_ERROR)
        return self

    @step
    def should_see_error_for_empty_confluence_fields(self):
        expect(self.error_cql_query_input).to_be_visible()
        expect(self.error_cql_query_input).to_have_text(EMPTY_CQL_ERROR)
        return self

    @step
    def should_see_error_for_empty_jql_fields(self):
        expect(self.error_jql_query_input).to_be_visible()
        expect(self.error_jql_query_input).to_have_text(EMPTY_JQL_ERROR)
        return self

    @step
    def should_see_error_for_empty_file_fields(self):
        expect(self.error_files_info_text).to_be_visible()
        expect(self.error_files_info_text).to_have_text(EMPTY_FILE_ERROR)
        return self

    @step
    def should_see_error_for_empty_google_fields(self):
        expect(self.error_google_query_input).to_be_visible()
        expect(self.error_google_query_input).to_have_text(EMPTY_GOOGLE_LINK_ERROR)
        return self

    # -------------------------------
    # Git DataSource Type Verification Methods
    # -------------------------------

    @step
    def should_see_summarization_fields(self):
        expect(self.summarization_method_input).to_be_visible()
        expect(self.summarization_method_dropdown).to_be_visible()
        return self

    @step
    def should_see_summarization_dropdown_values(self):
        self.summarization_method_dropdown.click()
        for method in SUMMARIZATION_METHODS_LIST:
            expect(self.dropdown_values(method)).to_be_visible()

    @step
    def should_see_repo_fields(self):
        expect(self.repo_link_input).to_be_visible()
        expect(self.branch_input).to_be_visible()
        return self

    @step
    def should_see_files_filter_textarea(self):
        expect(self.files_filter_input).to_be_visible()
        return self

    @step
    def should_see_git_fields(self):
        self.should_see_summarization_fields()
        self.should_see_repo_fields()
        self.should_see_files_filter_textarea()
        self.should_see_embeddings_model_field()
        self.should_see_integration_input_or_button()
        return self

    # -------------------------------
    # Confluence DataSource Type Verification Methods
    # -------------------------------

    @step
    def should_see_confluence_cql_field(self):
        expect(self.cql_query_input).to_be_visible()
        return self

    # -------------------------------
    # Jira DataSource Type Verification Methods
    # -------------------------------

    @step
    def should_see_jql_field(self):
        expect(self.jql_input).to_be_visible()
        return self

    # -------------------------------
    # File DataSource Type Verification Methods
    # -------------------------------

    @step
    def should_see_file_fields(self):
        expect(self.file_drop_zone).to_be_visible()
        expect(self.file_drop_zone_label).to_be_visible()
        expect(self.files_info_text).to_be_visible()
        expect(self.files_info_text).to_have_text(FILE_INSTRUCTIONS)
        return self

    @step
    def should_see_uploaded_file(self, file_name: str):
        expect(self.file_input_field).to_be_visible()
        expect(self.file_input_field).to_have_text(file_name)
        return self

    # -------------------------------
    # Error Dialog Methods
    # -------------------------------

    @step
    def should_not_see_repository_not_found_error(self):
        """Verify that no 'Repository not found' error dialog appears."""
        error_dialog = self.page.locator('dialog:has-text("Repository not found")')
        expect(error_dialog).not_to_be_visible()
        # Also check for error toast notifications
        error_toast = self.page.locator(
            '.codemie-toast:has-text("Repository not found")'
        )
        expect(error_toast).not_to_be_visible()
        return self

    @step
    def should_not_see_error_dialog(self):
        """Verify that no error dialog is visible."""
        error_dialog = self.page.locator('dialog[role="dialog"]:has([class*="error"])')
        expect(error_dialog).not_to_be_visible()
        return self

    # -------------------------------
    # Google DataSource Type Verification Methods
    # -------------------------------

    @step
    def should_see_google_fields(self):
        expect(self.google_query_input).to_be_visible()
        expect(self.google_instructions.nth(0)).to_be_visible()
        expect(self.google_instructions.nth(0)).to_have_text(GOOGLE_EXAMPLE)
        expect(self.google_instructions.nth(0).locator("a")).to_have_attribute(
            "href", get_google_doc_url()
        )
        expect(self.google_instructions.nth(1)).to_have_text(GOOGLE_DETAILED_EXAMPLE)
        expect(self.google_instructions.nth(1).locator("a")).to_have_attribute(
            "href", GOOGLE_DOC_GUIDE_URL
        )
        return self

    # -------------------------------
    # ADO DataSource Type Verification Methods
    # -------------------------------

    @step
    def should_see_ado_fields(self):
        expect(self.ado_wiki_name_input).to_be_visible()
        expect(self.page_path_input).to_be_visible()
        expect(self.ado_instructions).to_be_visible()
        expect(self.ado_instructions).to_have_text(ADO_INSTRUCTIONS)
        return self

    # -------------------------------
    # xWiki DataSource Type Verification Methods
    # -------------------------------

    @step
    def should_see_new_xwiki_option_in_dropdown(self):
        """Verify the datasource type dropdown offers a selectable 'xWiki' option
        tagged with the 'NEW' badge (DataSourceTypeSelector.tsx itemTemplate)."""
        self.datasource_type_dropdown.click()
        expect(self.xwiki_option).to_be_visible()
        expect(self.xwiki_option.get_by_text("NEW")).to_be_visible()
        self.datasource_type_dropdown.click()
        return self

    @step
    def should_see_xwiki_fields(self):
        expect(self.xwiki_space_input).to_be_visible()
        expect(self.xwiki_wiki_input).to_be_visible()
        return self

    # -------------------------------
    # Provider (DSP) DataSource Type Verification Methods
    # -------------------------------

    @step
    def should_be_ready_to_save(self):
        expect(self.save_button).to_be_enabled()
        expect(self.save_reindex_button).to_be_enabled()
        return self

    @step
    def should_see_provider_graphdb_username_value(self, value: str):
        expect(self.provider_graphdb_username_input).to_have_value(value)
        return self

    @step
    def should_see_provider_field_values(
        self,
        repositories: str = None,
        graphdb_username: str = None,
        graphdb_password: str = None,
        graphdb_tenant_url: str = None,
    ):
        """Verify the create/edit form's AICE provider fields hold the given values — used to confirm a provider's configured
        `default_value` actually pre-populates the form before the user types
        anything, and to confirm persistence of edits after save/refresh/relogin.
        """
        if repositories is not None:
            expect(self.provider_repositories_input).to_have_value(repositories)
        if graphdb_username is not None:
            expect(self.provider_graphdb_username_input).to_have_value(graphdb_username)
        if graphdb_password is not None:
            expect(self.provider_graphdb_password_input).to_have_value(graphdb_password)
        if graphdb_tenant_url is not None:
            expect(self.provider_graphdb_tenant_url_input).to_have_value(
                graphdb_tenant_url
            )
        return self

    @step
    def should_see_provider_fields_prepopulated_from_defaults(
        self,
        repositories: str = None,
        graphdb_username: str = None,
        graphdb_password: str = None,
        graphdb_tenant_url: str = None,
    ):
        """Verify the AICE provider's fields on the Create DataSource form are
        pre-populated from the selected provider's configured `default_value`
        (frontend `getProviderFieldInitialValue`) as soon as the provider
        schema has loaded — before any manual input.
        """
        expect(self.provider_repositories_input).to_be_visible()
        self.should_see_provider_field_values(
            repositories=repositories,
            graphdb_username=graphdb_username,
            graphdb_password=graphdb_password,
            graphdb_tenant_url=graphdb_tenant_url,
        )
        return self

    @step
    def should_see_validation_error(self, message: str):
        error = self.provider_field_error(message)
        expect(error).to_be_visible()
        return self

    # -------------------------------
    # Public Git Datasource Elements and Verification Methods
    # -------------------------------

    @property
    def optional_integration_hint(self):
        """'Integration is optional' informational banner in IntegrationSection for Git datasource.

        Uses a stable partial-text match on a unique sentence fragment so the locator
        remains valid if the hint spans multiple DOM nodes or if surrounding copy changes.
        """
        return self.page.get_by_text("Integration is optional", exact=False)

    @property
    def public_access_error_toast(self):
        """Error notification shown when repository is not publicly accessible.

        The UI renders an `[role='alert']` element whose text begins with
        "Failed to connect to git:" — the exact suffix varies depending on
        whether the repo is unreachable vs. access-denied, but the prefix is
        consistent for all Git connection failures surfaced by the health check.
        """
        return self.page.get_by_role("alert").filter(
            has_text="Failed to connect to git"
        )

    @step
    def should_see_optional_integration_hint(self):
        """Verify optional integration hint is visible on the Git datasource form."""
        expect(self.optional_integration_hint).to_be_visible()
        return self

    @step
    def should_see_public_access_error_notification(self):
        """Verify error notification is visible for inaccessible public repository."""
        expect(self.public_access_error_toast).to_be_visible()
        return self

    # -------------------------------
    # Reindex Schedule Verification Methods
    # -------------------------------

    @step
    def should_see_reindex_type_dropdown(self):
        """Verify Reindex Type dropdown is visible"""
        expect(self.reindex_type_dropdown).to_be_visible()
        return self

    @step
    def should_see_expression_dropdown(self):
        """Verify Expression dropdown is visible"""
        expect(self.expression_dropdown).to_be_visible()
        return self

    @step
    def should_see_reindex_schedule_fields(self):
        """Verify both reindex schedule dropdowns are visible"""
        self.should_see_reindex_type_dropdown()
        self.should_see_expression_dropdown()
        return self

    # -------------------------------
    # Clone Data Source
    # -------------------------------

    @step
    def navigate_to_clone(self, datasource_id: str):
        """Open /data-sources/<id>/clone directly."""
        self.page.goto(f"/data-sources/{datasource_id}/clone")
        self.page.wait_for_load_state("domcontentloaded", timeout=30000)
        expect(self.clone_page_title).to_be_visible(timeout=15000)
        return self

    @step
    def should_be_on_clone_page(self, datasource_id: str):
        """Verify route, page header title and sidebar title/subtitle of the clone page."""
        expect(self.page).to_have_url(
            re.compile(rf"/data-sources/{re.escape(datasource_id)}/clone/?(\?.*)?$"),
            timeout=15000,
        )
        expect(self.clone_page_title).to_be_visible(timeout=15000)
        self.sidebar.should_see_title_subtitle(
            CLONE_SIDEBAR_TITLE, CLONE_SIDEBAR_SUBTITLE
        )
        return self

    @step
    def should_see_clone_form_prefilled(
        self, description: str, repo_link: str, branch: str
    ):
        """Verify the Git clone form carries the source configuration and an empty name.

        Prefilled fields are asserted first (expect() retries until the form has
        loaded) so the empty-name check never runs against a form that has not
        rendered yet.
        """
        expect(self.description_input).to_have_value(description, timeout=15000)
        expect(self.repo_link_input).to_have_value(repo_link)
        expect(self.branch_input).to_have_value(branch)
        expect(self.name_input).to_have_value("")
        return self

    @step
    def should_see_provider_clone_with_blank_secret(
        self, repositories: str, graphdb_username: str
    ):
        """Verify a provider clone keeps the plain settings but shows the secret blank."""
        expect(self.provider_repositories_input).to_have_value(
            repositories, timeout=15000
        )
        expect(self.provider_graphdb_username_input).to_have_value(graphdb_username)
        expect(self.provider_graphdb_password_input).to_have_value("")
        expect(self.name_input).to_have_value("")
        return self

    @step
    def should_see_uploaded_file_by_name(self, file_name: str):
        expect(self.uploaded_file_name(file_name)).to_be_visible(timeout=15000)
        return self

    @step
    def should_see_file_clone_form_without_files(
        self, description: str, file_name: str
    ):
        """Verify the file clone form keeps settings, shows the drop zone and lists no files."""
        expect(self.description_input).to_have_value(description, timeout=15000)
        expect(self.file_drop_zone).to_be_visible()
        expect(self.uploaded_file_name(file_name)).to_have_count(0)
        expect(self.file_input_field).to_have_count(0)
        expect(self.name_input).to_have_value("")
        return self

    @step
    def should_see_name_required_error(self):
        expect(self.error_name_input).to_be_visible()
        expect(self.error_name_input).to_have_text(EMPTY_NAME_ERROR)
        return self

    @step
    def click_create_and_get_create_status(self) -> int:
        """Click Save and return the HTTP status of the create-index request it sends."""
        with self.page.expect_response(
            lambda response: response.request.method == "POST"
            and re.search(r"/application/[^/]+/index/?(\?|$)", response.url),
            timeout=30000,
        ) as response_info:
            self.create_button.click()
        return response_info.value.status

    @step
    def should_see_clone_blocked(self, message: str):
        """Verify the clone page shows a block message instead of the form and Save is disabled."""
        expect(self.block_message(message)).to_be_visible(timeout=15000)
        expect(self.create_button).to_be_disabled()
        return self
