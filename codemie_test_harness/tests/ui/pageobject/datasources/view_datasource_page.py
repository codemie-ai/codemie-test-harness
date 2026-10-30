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
from datetime import datetime, timedelta

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from hamcrest import (
    assert_that,
    greater_than_or_equal_to,
    less_than_or_equal_to,
    equal_to,
)
from playwright.sync_api import expect
from reportportal_client import step
from codemie_test_harness.tests.ui.pageobject.datasources.datasource_sidebar import (
    DataSourceSidebar,
)


# "Last indexed" renders as e.g. "Jul 17, 14:52 (55 days ago)": minute precision,
# no year, in the browser's local time zone.
LAST_INDEXED_PATTERN = re.compile(r"^\s*([A-Z][a-z]{2}\s+\d{1,2},\s+\d{1,2}:\d{2})")
LAST_INDEXED_FORMAT = "%b %d, %H:%M"


def parse_last_indexed(text: str) -> datetime:
    """Parse the date part of a 'Last indexed' value into a naive local datetime.

    The UI omits the year, so the current year is assumed. Raises ValueError when
    the text does not start with a 'Mon D, HH:MM' timestamp.
    """
    match = LAST_INDEXED_PATTERN.match(text)
    if match is None:
        raise ValueError(f"Unrecognised 'Last indexed' value: {text!r}")
    parsed = datetime.strptime(match.group(1), LAST_INDEXED_FORMAT)
    return parsed.replace(year=datetime.now().year)


class ViewDatasourcePage(BasePage):
    """
    Page object for the 'View DataSource' details page.
    Contains all major section locators and verification methods (with text checks).
    """

    def __init__(self, page):
        self.sidebar = DataSourceSidebar(page)
        self.page = page

    # Main Page Elements
    @property
    def back_button(self):
        return self.page.locator("div.h-layout-header button").first

    @property
    def edit_button(self):
        return self.page.get_by_role("button", name="Edit")

    @property
    def delete_button(self):
        return self.page.get_by_role("button", name="Delete")

    @property
    def clone_button(self):
        """'Clone' button in the details page action row."""
        return self.page.get_by_role("button", name="Clone", exact=True)

    @property
    def main_title(self):
        return self.page.locator("h1.text-h3.text-white.font-semibold")

    # Name/Owner/Shared
    @property
    def datasource_name(self):
        return self.page.locator("h4.text-2xl.font-semibold.font-mono")

    @property
    def owner_text(self):
        return self.page.locator("p").filter(has_text="by ").first

    @property
    def shared_status(self):
        return self.page.locator(
            "span.text-xs.text-switch-label, span.flex.items-center.gap-1"
        )

    # Overview Section
    @property
    def overview_label(self):
        return self.page.get_by_text("OVERVIEW", exact=True)

    @property
    def project_value(self):
        return self.page.locator("div.gap-x-3 p:text('Project:') + p")

    @property
    def datasource_type_value(self):
        return self.page.locator("div.gap-x-3 p:text('Data Source Type:') + p")

    @property
    def datasource_id_field(self):
        return self.page.locator(
            "div.flex.flex-col.gap-2.mt-2.uppercase input[readonly]"
        )

    # Description
    @property
    def description_label(self):
        return self.page.locator("h5.font-bold.text-xs.mb-2", has_text="Description")

    @property
    def description_text(self):
        return self.description_label.locator("xpath=../div")

    # Details Section (provider/DSP-specific fields)
    #
    # Each row is `div.flex.mb-2.text-xs` containing a label div (e.g. "Branch:")
    # and a sibling value-wrapper div. Verified live on
    # the /data-sources/<id> page via playwright-cli:
    # label and value are siblings, so the existing
    # `text=<label> + xpath=following-sibling::*[1]` convention (already used
    # for Project/Data Source Type above) applies directly.
    @property
    def details_label(self):
        return self.page.locator(
            "h5.font-bold.text-xs.leading-none.font-mono", has_text="Details"
        )

    def details_value(self, label: str):
        """Value locator for a 'Details' panel row identified by its exact
        label text including the trailing colon, e.g. 'Branch:', 'Api Url:',
        'Access Token:', 'Datasource Id:', 'Name:', 'Description:',
        'Datasource Root:'.
        """
        return self.page.locator(f"text={label}").locator(
            "xpath=following-sibling::*[1]"
        )

    @property
    def details_datasource_id_value(self):
        return self.details_value("Datasource Id:")

    @property
    def details_name_value(self):
        # Exact match: 'Name:' is a substring of 'Graphdb Username:', so the
        # substring locator used by details_value would hit both rows.
        return self.page.get_by_text("Name:", exact=True).locator(
            "xpath=following-sibling::*[1]"
        )

    @property
    def details_description_value(self):
        return self.details_value("Description:")

    @property
    def details_repositories_value(self):
        return self.details_value("Repositories:")

    @property
    def details_graphdb_username_value(self):
        """Note: the Details panel labels this from the raw parameter name
        ('Graphdb Username:'), unlike the create/edit form which uses the
        schema's display title ('Graph Database Username') — verified live.
        """
        return self.details_value("Graphdb Username:")

    @property
    def details_graphdb_password_value(self):
        return self.details_value("Graphdb Password:")

    @property
    def details_graphdb_tenant_url_value(self):
        return self.details_value("Graphdb Tenant Url:")

    @property
    def last_indexed_label(self):
        """'Last indexed' label on the Data Source Details page."""
        return self.page.get_by_text("Last indexed", exact=False).first

    @property
    def last_indexed_value(self):
        """Value element next to the 'Last indexed' label, e.g. 'Jul 17, 14:52 (55 days ago)'."""
        return self.last_indexed_label.locator("xpath=following-sibling::*[1]")

    # Configuration Section
    @property
    def configuration_label(self):
        return self.page.get_by_text("CONFIGURATION", exact=True)

    @property
    def embeddings_model_label(self):
        return self.page.get_by_text("Embeddings model", exact=True)

    @property
    def embeddings_model_value(self):
        return (
            self.page.locator("text=Embeddings model")
            .locator("xpath=following-sibling::*[1]")
            .first
        )

    @property
    def summarization_model_label(self):
        return self.page.get_by_text("Summarization model:", exact=True)

    @property
    def summarization_model_value(self):
        return (
            self.page.locator("text=Summarization model:")
            .locator("xpath=following-sibling::*[1]")
            .first
        )

    # Usage Details Section
    @property
    def usage_label(self):
        return self.page.locator(
            "p.text-xs.text-text-main.font-semibold", has_text="USAGE DETAILS"
        )

    @property
    def input_tokens_label(self):
        return self.page.locator(
            "p.text-xs.text-text-tertiary", has_text="Input tokens used:"
        )

    @property
    def input_tokens_value(self):
        return self.input_tokens_label.locator("xpath=../div")

    @property
    def output_tokens_label(self):
        return self.page.locator(
            "p.text-xs.text-text-tertiary", has_text="Output tokens used:"
        )

    @property
    def output_tokens_value(self):
        return self.output_tokens_label.locator("xpath=../div")

    @property
    def money_spent_label(self):
        return self.page.locator(
            "p.text-xs.text-text-tertiary", has_text="Money spent:"
        )

    @property
    def money_spent_value(self):
        return self.money_spent_label.locator("xpath=../div")

    # Processing Summary
    @property
    def processing_summary_label(self):
        return self.page.locator(
            "h5.font-bold.text-xs.leading-none.font-mono", has_text="Processing Summary"
        )

    @property
    def total_documents_label(self):
        return self.page.get_by_text("Total documents:", exact=True)

    @property
    def total_documents_count(self):
        return self.page.locator("text=Total documents:").locator(
            "xpath=following-sibling::*[1]"
        )

    @property
    def processed_documents_label(self):
        return self.page.get_by_text("Processed Documents Count:", exact=True)

    @property
    def processed_documents_count(self):
        return self.page.locator("text=Processed Documents Count:").locator(
            "xpath=following-sibling::*[1]"
        )

    @property
    def imported_chunks_label(self):
        return self.page.get_by_text("Imported Chunks Count:", exact=True)

    @property
    def imported_chunks_count(self):
        return self.page.locator("text=Imported Chunks Count:").locator(
            "xpath=following-sibling::*[1]"
        )

    @property
    def skipped_documents_label(self):
        return self.page.get_by_text("Skipped Documents:", exact=True)

    @property
    def skipped_documents_count(self):
        return self.page.locator("text=Skipped Documents:").locator(
            "xpath=following-sibling::*[1]"
        )

    @property
    def total_size_kb_label(self):
        return self.page.get_by_text("Total Size KB:", exact=True)

    @property
    def total_size_kb_count(self):
        return self.page.locator("text=Total Size KB:").locator(
            "xpath=following-sibling::*[1]"
        )

    @property
    def average_file_size_b_label(self):
        return self.page.get_by_text("Average File Size B:", exact=True)

    @property
    def average_file_size_b_count(self):
        return self.page.locator("text=Average File Size B:").locator(
            "xpath=following-sibling::*[1]"
        )

    # Processed Data
    @property
    def processed_data_tab_label(self):
        return self.page.locator("ul li a.p-menuitem-link", has_text="Processed Data")

    @property
    def processed_data_label(self):
        return self.page.locator("h5.text-xs", has_text="Processed Data")

    @property
    def processed_data_list(self):
        return self.page.locator("ul.bg-surface-base-secondary li")

    # --- Verification Methods ---

    @step
    def should_see_title_and_back_button(self):
        expect(self.main_title).to_have_text("Data Source Details")
        expect(self.back_button).to_be_visible()
        return self

    @step
    def should_see_clone_button(self):
        expect(self.clone_button).to_be_visible()
        return self

    @step
    def should_see_ds_name_and_owner(
        self, datasource_name: str = None, owner: str = None
    ):
        expect(self.datasource_name).to_be_visible()
        if datasource_name:
            expect(self.datasource_name).to_have_text(datasource_name)
        expect(self.owner_text).to_be_visible()
        if owner:
            expect(self.owner_text).to_have_text(f"by {owner}")
        return self

    @step
    def should_see_overview(
        self, project: str = None, ds_type: str = None, ds_id: str = None
    ):
        expect(self.overview_label).to_be_visible()
        expect(self.project_value).to_be_visible()
        if project:
            expect(self.project_value).to_have_text(project)
        expect(self.datasource_type_value).to_be_visible()
        if ds_type:
            expect(self.datasource_type_value).to_have_text(ds_type)
        expect(self.datasource_id_field).to_be_visible()
        if ds_id:
            expect(self.datasource_id_field).to_have_value(ds_id)
        return self

    @step
    def should_see_description(self, description: str = None):
        expect(self.description_label).to_be_visible()
        expect(self.description_text).to_be_visible()
        if description:
            expect(self.description_text).to_have_text(description)
        return self

    @step
    def should_see_provider_graphdb_username_value(self, value: str):
        expect(self.details_graphdb_username_value).to_have_text(value)
        return self

    @step
    def should_see_provider_repositories_details(
        self,
        datasource_id: str = None,
        name: str = None,
        description: str = None,
        repositories: str = None,
        graphdb_username: str = None,
        graphdb_password: str = None,
        graphdb_tenant_url: str = None,
    ):
        """Verify the 'Details' panel of an AICE provider datasource
        shows the `Repositories` row plus the datasource's own life-cycle fields.
        `graphdb_*`/`repositories` values are asserted only when given.
        """
        expect(self.details_label).to_be_visible()

        expect(self.details_repositories_value).to_be_visible()
        if repositories is not None:
            expect(self.details_repositories_value).to_have_text(repositories)

        if graphdb_username is not None:
            expect(self.details_graphdb_username_value).to_have_text(graphdb_username)
        if graphdb_password is not None:
            expect(self.details_graphdb_password_value).to_have_text(graphdb_password)
        if graphdb_tenant_url is not None:
            expect(self.details_graphdb_tenant_url_value).to_have_text(
                graphdb_tenant_url
            )

        expect(self.details_datasource_id_value).to_be_visible()
        if datasource_id is not None:
            expect(self.details_datasource_id_value).to_have_text(datasource_id)

        expect(self.details_name_value).to_be_visible()
        if name is not None:
            expect(self.details_name_value).to_have_text(name)

        expect(self.details_description_value).to_be_visible()
        if description is not None:
            expect(self.details_description_value).to_have_text(description)
        return self

    @step
    def should_see_no_repositories_row(
        self,
        datasource_id: str = None,
        name: str = None,
        description: str = None,
    ):
        """Verify the `Repositories` row is gone after its parameter was removed
        from the provider definition, while the datasource id,
        name and description stay.
        """
        expect(self.details_label).to_be_visible()
        expect(self.details_repositories_value).to_have_count(0)

        expect(self.details_datasource_id_value).to_be_visible()
        if datasource_id is not None:
            expect(self.details_datasource_id_value).to_have_text(datasource_id)

        expect(self.details_name_value).to_be_visible()
        if name is not None:
            expect(self.details_name_value).to_have_text(name)

        expect(self.details_description_value).to_be_visible()
        if description is not None:
            expect(self.details_description_value).to_have_text(description)
        return self

    @step
    def get_provider_datasource_id(self) -> str:
        """Read the 'Datasource Id:' value shown in the Details panel."""
        expect(self.details_datasource_id_value).to_be_visible()
        return self.details_datasource_id_value.inner_text().strip()

    @step
    def should_see_configuration(
        self, embeddings_model: str = None, summarization_model: str = None
    ):
        expect(self.configuration_label).to_be_visible()
        expect(self.embeddings_model_label).to_be_visible()
        expect(self.embeddings_model_value).to_be_visible()
        if embeddings_model:
            expect(self.embeddings_model_value).to_have_text(embeddings_model)
        if summarization_model:
            expect(self.summarization_model_label).to_be_visible()
            expect(self.summarization_model_value).to_be_visible()
            expect(self.summarization_model_value).to_have_text(summarization_model)
        return self

    @step
    def should_see_usage_details(self):
        expect(self.usage_label).to_be_visible()
        expect(self.input_tokens_label).to_be_visible()
        expect(self.input_tokens_value).to_be_visible()
        expect(self.output_tokens_label).to_be_visible()
        expect(self.output_tokens_value).to_be_visible()
        expect(self.money_spent_label).to_be_visible()
        expect(self.money_spent_value).to_be_visible()
        return self

    @step
    def should_see_processing_summary(
        self,
        total_documents: str = None,
        processed_documents: str = None,
        imported_chunks: str = None,
        skipped_documents: str = None,
        is_git: bool = False,
    ):
        expect(self.processing_summary_label).to_be_visible()
        expect(self.total_documents_label).to_be_visible()
        expect(self.total_documents_count).to_be_visible()
        if total_documents:
            expect(self.total_documents_count).to_have_text(total_documents)
        expect(self.processed_documents_label).to_be_visible()
        expect(self.processed_documents_count).to_be_visible()
        if processed_documents:
            expect(self.processed_documents_count).to_have_text(processed_documents)
        expect(self.imported_chunks_label).to_be_visible()
        expect(self.imported_chunks_count).to_be_visible()
        if imported_chunks:
            expect(self.imported_chunks_count).to_have_text(imported_chunks)
        expect(self.skipped_documents_label).to_be_visible()
        expect(self.skipped_documents_count).to_be_visible()
        if skipped_documents:
            expect(self.skipped_documents_count).to_have_text(skipped_documents)
        if is_git:
            expect(self.total_size_kb_label).to_be_visible()
            expect(self.total_documents_count).to_be_visible()
            expect(self.average_file_size_b_label).to_be_visible()
            expect(self.average_file_size_b_count).to_be_visible()
        return self

    @step
    def should_open_and_see_processed_data(self, min_count: int = 1):
        expect(self.processed_data_tab_label).to_be_visible()
        self.processed_data_tab_label.click()
        expect(self.processed_data_list.first).to_be_visible()
        count = self.processed_data_list.count()
        assert_that(count, greater_than_or_equal_to(min_count))
        return self

    @step
    def should_see_processed_data(self, min_count: int = 1):
        expect(self.processed_data_label).to_be_visible()
        expect(self.processed_data_list.first).to_be_visible()
        count = self.processed_data_list.count()
        assert_that(count, greater_than_or_equal_to(min_count))
        return self

    @step
    def should_show_project_display_name(self, display_name: str):
        """Verify the Overview Project field shows technical name with display_name as hover tooltip."""
        self.project_value.hover()
        self.page.wait_for_timeout(300)
        expect(self.page.locator('[role="tooltip"]')).to_contain_text(display_name)
        return self

    @step
    def get_last_indexed(self) -> datetime:
        """Return the displayed 'Last indexed' value as a local datetime (minute precision)."""
        expect(self.last_indexed_label).to_be_visible()
        expect(self.last_indexed_value).to_be_visible()
        expect(self.last_indexed_value).to_contain_text(LAST_INDEXED_PATTERN)
        return parse_last_indexed(self.last_indexed_value.inner_text())

    @step
    def try_get_last_indexed(self) -> datetime | None:
        """Return the displayed 'Last indexed' value, or None when the row is absent.

        Used on the shared, session-scoped `code_datasource` fixture, which may
        already carry a value from an earlier test in the same session. Waits for the page header first so a
        still-loading page is not mistaken for an absent row.
        """
        expect(self.datasource_name).to_be_visible()
        if self.last_indexed_label.count() == 0:
            return None
        return self.get_last_indexed()

    @step
    def should_see_last_indexed(self):
        """Verify the 'Last indexed' row is shown with a parsable timestamp."""
        expect(self.last_indexed_label).to_be_visible()
        expect(self.last_indexed_value).to_contain_text(LAST_INDEXED_PATTERN)
        return self

    @step
    def should_see_last_indexed_between(
        self,
        trigger_started: datetime,
        trigger_finished: datetime,
        tolerance: timedelta = timedelta(minutes=1),
    ):
        """Verify 'Last indexed' is the reindex TRIGGER time.

        `trigger_started` / `trigger_finished` bracket the moment the reindex was
        requested. The UI shows minute precision and the stand clock may differ
        slightly from the test machine, so both bounds are truncated to the minute
        and widened by `tolerance`. A stamp taken at completion is rejected only
        when the reindex runs longer than that window; on a faster reindex the two
        times are indistinguishable at minute precision.
        """
        shown = self.get_last_indexed()
        lower = trigger_started.replace(second=0, microsecond=0) - tolerance
        upper = trigger_finished.replace(second=0, microsecond=0) + tolerance
        assert_that(
            shown,
            greater_than_or_equal_to(lower),
            "Last indexed must not be earlier than the reindex trigger time",
        )
        assert_that(
            shown,
            less_than_or_equal_to(upper),
            "Last indexed must equal the reindex trigger time, not a later completion time",
        )
        return self

    @step
    def should_see_last_indexed_equal_to(self, expected: datetime):
        """Verify 'Last indexed' is exactly the previously read value (not reverted)."""
        assert_that(
            self.get_last_indexed(),
            equal_to(expected),
            "Last indexed must stay unchanged after refreshing and reopening the details",
        )
        return self
