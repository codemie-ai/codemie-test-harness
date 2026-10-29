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

from hamcrest import assert_that, contains_string
from playwright.sync_api import Page, expect
from reportportal_client import step


class AssistantViewPage:
    def __init__(self, page: Page):
        self.page = page

    # ----------------
    # --- LOCATORS ---
    # ----------------

    @property
    def page_title(self):
        """Page heading 'Assistant Details'."""
        return self.page.get_by_role("heading", name="Assistant Details", level=1)

    @property
    def pinned_assistant_title(self):
        """Pinned assistant name subtitle shown below the Assistant Details heading."""
        return self.page_title.locator("xpath=following-sibling::div[1]")

    @property
    def assistant_name(self):
        return self.page.locator("h4.name-target")

    @property
    def assistant_author(self):
        return self.page.locator("div.flex.text-xs.text-text-quaternary > p")

    @property
    def about_heading(self):
        return self.page.locator("h5.font-bold.text-sm:text('About Assistant:')")

    @property
    def about_content(self):
        # Paragraph under "About Assistant:"
        return self.about_heading.locator("xpath=../p")

    @property
    def system_instructions_heading(self):
        return self.page.locator(
            "div.flex.bg-new-panel.border.rounded-lg [class*='text-xs']:text('System Instructions')"
        )

    @property
    def system_instructions_content(self):
        return self.page.locator("div.flex.bg-surface-base-secondary > p.text-sm")

    # --- Overview Block ---
    @property
    def overview_section_header(self):
        return self.page.get_by_role("heading", name="OVERVIEW", level=3)

    @property
    def overview_block(self):
        return self.page.get_by_role("heading", name="OVERVIEW", level=3).locator(
            "xpath=.."
        )

    @property
    def overview_project(self):
        return self.overview_block.locator(
            "div.flex:has(p.text-text-quaternary:text('Project:')) > p:not(.text-text-quaternary)"
        )

    @property
    def overview_shared_status(self):
        return self.overview_block.locator(
            "div.flex:has(p.text-text-quaternary:text('Shared status:')) > p:not(.text-text-quaternary)"
        )

    @property
    def overview_assistant_id_label(self):
        return self.overview_block.locator(
            "h4.text-xs.text-text-primary:text('ASSISTANT ID:')"
        )

    @property
    def overview_assistant_id(self):
        return self.overview_block.locator(
            "div.flex.flex-col.gap-2.mt-2.font-semibold input[readonly]"
        )

    @property
    def overview_assistant_id_copy_button(self):
        return self.overview_block.locator(
            "div.flex.flex-col.gap-2.mt-2.font-semibold button[aria-label='Copy']"
        )

    # --- Links Block ---
    @property
    def access_links_section_header(self):
        return self.page.get_by_role("heading", name="ACCESS LINKS", level=3)

    @property
    def access_links_block(self):
        return self.page.get_by_role("heading", name="ACCESS LINKS", level=3).locator(
            "xpath=.."
        )

    @property
    def details_link_input(self):
        return self.access_links_block.locator(
            "div.flex.flex-col.gap-2:has(h4:text('Link to assistant details')) input[readonly]"
        )

    @property
    def chat_link_input(self):
        return self.access_links_block.locator(
            "div.flex.flex-col.gap-2:has(h4:text('Link to start a chat')) input[readonly]"
        )

    @property
    def details_link_copy_button(self):
        return self.access_links_block.locator(
            "div.flex.flex-col.gap-2:has(h4:text('Link to assistant details')) button[aria-label='Copy']"
        )

    @property
    def chat_link_copy_button(self):
        return self.access_links_block.locator(
            "div.flex.flex-col.gap-2:has(h4:text('Link to start a chat')) button[aria-label='Copy']"
        )

    # --- Configuration ---
    @property
    def configuration_section_header(self):
        return self.page.get_by_role("heading", name="CONFIGURATION", level=3)

    @property
    def configuration_block(self):
        return self.page.get_by_role("heading", name="CONFIGURATION", level=3).locator(
            "xpath=.."
        )

    @property
    def config_llm_model(self):
        return self.configuration_block.locator("p:text('LLM model')").locator(
            "xpath=../div"
        )

    @property
    def config_temperature(self):
        return self.configuration_block.locator("p:text('Temperature')").locator(
            "xpath=../div"
        )

    @property
    def config_top_p(self):
        return self.configuration_block.locator("p:text('Top P')").locator(
            "xpath=../div"
        )

    @property
    def config_additional_datasource_context_label(self):
        return self.configuration_block.locator(
            "p:text('Additional datasource context')"
        )

    @property
    def config_additional_datasource_context(self):
        return self.configuration_block.locator(
            "div:has(p:text('Additional datasource context')) div.bg-new-panel.py-1\\.5.px-2"
        )

    @property
    def config_no_datasources_text(self):
        return self.configuration_block.locator(
            "p.text-text-quaternary:text('No datasources chosen')"
        )

    # --- Tools & Capabilities ---

    @property
    def tools_section_header(self):
        return self.page.get_by_role("heading", name="TOOLS & CAPABILITIES", level=3)

    @property
    def tools_block(self):
        """Block containing all toolkits under 'TOOLS & CAPABILITIES'."""
        return self.page.get_by_role(
            "heading", name="TOOLS & CAPABILITIES", level=3
        ).locator("xpath=..")

    def toolkit_block(self, toolkit_name: str):
        """Returns the block for the toolkit (e.g., 'Git', 'VCS', etc.)."""
        return self.tools_block.locator(
            f"div.flex.flex-col.gap-2:has(p.font-semibold.text-text-tertiary.text-xs:has-text('{toolkit_name}'))"
        )

    def toolkit_tool_labels(self, toolkit_name: str):
        """Returns elements for all tool labels under a given toolkit block."""
        return self.toolkit_block(toolkit_name).locator(
            "div.flex.flex-wrap.gap-2 > div.py-1\\.5.px-2.bg-surface-base-chat"
        )

    def toolkit_tool_label(self, toolkit_name: str, tool_label: str):
        """
        Returns the div for a specific tool label.

        Uses case-insensitive matching to handle variations in capitalization
        between test data and UI display (e.g., "Fetch MCP server" vs "Fetch MCP Server").
        """
        # Escape special regex characters and create case-insensitive pattern
        escaped_label = re.escape(tool_label)
        pattern = f"^{escaped_label}$"

        return (
            self.toolkit_block(toolkit_name)
            .locator(
                "div.py-1\\.5.px-2.flex.items-center.gap-2.rounded-lg.bg-surface-base-chat.border.border-border-specific-panel-outline.font-semibold.text-xs"
            )
            .locator(f"text=/{pattern}/i")
        )

    # --- Sub-assistants ---

    @property
    def sub_assistants_section_label(self):
        """Returns the 'SUB ASSISTANTS' label."""
        return self.tools_block.locator(
            "p.text-xs.text-text-quaternary:text('SUB ASSISTANTS')"
        )

    @property
    def sub_assistants_list(self):
        """Returns the container holding all sub-assistant items."""
        return self.tools_block.locator(
            "div.flex.flex-col.gap-2:has(p.text-xs.text-text-quaternary:text('SUB ASSISTANTS'))"
        )

    @property
    def sub_assistant_items(self):
        """Returns all sub-assistant button items."""
        return self.sub_assistants_list.locator(
            "button[type='button'].flex.items-center.gap-2"
        )

    def sub_assistant_item_by_name(self, name: str):
        """Returns a specific sub-assistant item by its name."""
        return self.sub_assistants_list.locator(
            f"button[type='button']:has(p.text-xs.text-text-primary:text('{name}'))"
        )

    def sub_assistant_avatar(self, name: str):
        """Returns the avatar image for a specific sub-assistant."""
        return self.sub_assistant_item_by_name(name).locator("img.rounded-full")

    def sub_assistant_name(self, name: str):
        """Returns the name element for a specific sub-assistant."""
        return self.sub_assistant_item_by_name(name).locator(
            "p.text-xs.text-text-primary"
        )

    def sub_assistant_status(self, name: str):
        """Returns the status element (Private/Public) for a specific sub-assistant."""
        return self.sub_assistant_item_by_name(name).locator(
            "div.flex.items-center.gap-1.text-xs.text-text-quaternary span"
        )

    # --- Skills Section ---
    @property
    def skills_heading(self):
        """Skills section heading.

        Scoped to an h3 heading role so it can't collide with the unrelated "Skills" nav
        link in the sidebar (kept in the DOM but visually hidden when collapsed).
        """
        return self.page.get_by_role("heading", name="SKILLS", level=3)

    @property
    def skills_block(self):
        """Container for the Skills section (heading + attached skill links).

        Scoping lookups to this block avoids matching a same-named skill/entity
        elsewhere on the page (e.g. sub-assistants, nav links).
        """
        return self.skills_heading.locator("xpath=..")

    def attached_skill_badge(self, skill_name: str):
        """Returns the element for a specific attached skill by name, scoped to the Skills section."""
        return self.skills_block.get_by_role("link", name=skill_name)

    # --------------------------
    # --- EXPECT/VERIFY ---
    # --------------------------

    @step
    def should_have_pinned_title(self, expected_name: str):
        """Verify the pinned assistant name subtitle under 'Assistant Details' heading."""
        expect(self.pinned_assistant_title).to_be_visible()
        expect(self.pinned_assistant_title).to_have_text(expected_name)
        return self

    @step
    def should_have_all_form_fields_visible(
        self, name: str, author: str, description: str
    ):
        expect(self.assistant_name).to_be_visible()
        expect(self.assistant_name).to_have_text(name)
        expect(self.assistant_author).to_be_visible()
        expect(self.assistant_author).to_have_text(f"by {author}")
        expect(self.about_content).to_be_visible()
        expect(self.about_content).to_have_text(description)
        expect(self.system_instructions_content).to_be_visible()
        return self

    @step
    def should_have_overview_form_fields_visible(
        self, project: str, status: str, assistant_id: str
    ):
        # expect(self.overview_project).to_be_visible()
        # expect(self.overview_project).to_have_text(project)
        # expect(self.overview_shared_status).to_be_visible()
        # expect(self.overview_shared_status).to_have_text(status)
        expect(self.overview_assistant_id).to_be_visible()
        expect(self.overview_assistant_id).to_have_value(assistant_id)
        return self

    @step
    def should_have_access_links_form_fields_visible(self, assistant_name: str):
        expect(self.details_link_input).to_be_visible()
        assert_that(
            self.details_link_input.input_value(), contains_string(assistant_name)
        )
        expect(self.chat_link_input).to_be_visible()
        assert_that(self.chat_link_input.input_value(), contains_string(assistant_name))
        return self

    @step
    def should_have_configuration_form_fields_visible(
        self, temperature: str, top_p: str
    ):
        expect(self.config_temperature).to_be_visible()
        expect(self.config_temperature).to_have_text(temperature)
        expect(self.config_top_p).to_be_visible()
        expect(self.config_top_p).to_have_text(top_p)
        return self

    @step
    def should_see_assistant_name(self, expected):
        expect(self.assistant_name).to_have_text(expected)

    @step
    def should_see_assistant_author(self, expected):
        expect(self.assistant_author).to_have_text(expected)

    @step
    def should_see_about_content(self, expected):
        expect(self.about_content).to_have_text(expected)

    @step
    def should_see_system_instructions(self, expected):
        expect(self.system_instructions_content).to_have_text(expected)

    @step
    def should_see_overview_project(self, expected):
        expect(self.overview_project).to_have_text(expected)

    @step
    def should_show_project_display_name(self, display_name: str):
        """Verify the OVERVIEW Project field shows technical name with display_name as hover tooltip."""
        self.overview_project.hover()
        self.page.wait_for_timeout(300)
        expect(self.page.locator('[role="tooltip"]')).to_contain_text(display_name)
        return self

    @step
    def should_see_overview_shared_status(self, expected):
        expect(self.overview_shared_status).to_have_text(expected)

    @step
    def should_see_assistant_id(self, expected):
        expect(self.assistant_id_value).to_have_value(expected)

    @step
    def should_see_links(self, details_link, chat_link):
        expect(self.details_link_input).to_have_value(details_link)
        expect(self.chat_link_input).to_have_value(chat_link)

    @step
    def should_see_config_llm_model(self, expected):
        expect(self.config_llm_model).to_have_text(expected)

    @step
    def should_see_config_temperature(self, expected):
        expect(self.config_temperature).to_have_text(expected)

    @step
    def should_see_config_top_p(self, expected):
        expect(self.config_top_p).to_have_text(expected)

    @step
    def should_see_toolkit_visible(self, toolkit_name: str):
        """Assert that the toolkit with the given name is visible."""
        expect(self.toolkit_block(toolkit_name)).to_be_visible()

    @step
    def should_see_toolkit_contains(self, toolkit_name: str, tool_label: str):
        """Assert a toolkit contains a tool label (visible)."""
        expect(self.toolkit_tool_label(toolkit_name, tool_label)).to_be_visible()

    @step
    def should_see_tool_not_present(self, toolkit_name: str, tool_label: str):
        """Assert a toolkit does NOT contain a tool label."""
        expect(self.toolkit_tool_label(toolkit_name, tool_label)).not_to_be_visible()

    @step
    def should_see_toolkit_tools(self, toolkit_name: str, expected_tools: list):
        for tool in expected_tools:
            tool_name = tool.value if hasattr(tool, "value") else tool
            self.should_see_toolkit_contains(toolkit_name, tool_name)

    @step
    def should_have_attached_skill(self, skill_name: str):
        """Assert that a specific skill is attached and visible."""
        # Verify Skills section exists
        expect(self.skills_heading).to_be_visible()
        # Verify the specific skill is displayed as a link, scoped to the Skills
        # section so it can't match an unrelated same-named element elsewhere
        # on the page (e.g. a sub-assistant or nav item).
        expect(self.attached_skill_badge(skill_name)).to_be_visible()
        return self

    @step
    def should_not_have_skill_attached(self, skill_name: str):
        """Assert that a specific skill is NOT attached and not visible.

        The Skills section itself is only rendered when at least one skill is
        attached, so after detaching the last skill `skills_block` won't exist.
        Fall back to a page-wide role-based lookup (still far more specific than
        a raw text match) to assert the skill link is gone either way.
        """
        expect(self.page.get_by_role("link", name=skill_name)).not_to_be_visible()
        return self

    @step
    def should_see_assistant_id_copy_button(self):
        """Assert the assistant ID copy button is visible."""
        expect(self.overview_assistant_id_copy_button).to_be_visible()

    @step
    def should_see_access_link_copy_buttons(self):
        """Assert both access link copy buttons are visible."""
        expect(self.details_link_copy_button).to_be_visible()
        expect(self.chat_link_copy_button).to_be_visible()

    @step
    def should_see_no_datasources_message(self):
        """Assert 'No datasources chosen' message is visible."""
        expect(self.config_no_datasources_text).to_be_visible()
        expect(self.config_no_datasources_text).to_have_text("No datasources chosen")

    @step
    def should_see_sub_assistant(self, name: str):
        """Assert a sub-assistant with the given name is visible."""
        expect(self.sub_assistant_item_by_name(name)).to_be_visible()

    @step
    def should_see_sub_assistant_status(self, name: str, expected_status: str):
        """Assert a sub-assistant has the expected status (e.g., 'Private', 'Public')."""
        expect(self.sub_assistant_status(name)).to_have_text(expected_status)

    @step
    def should_have_sub_assistants_count(self, expected_count: int):
        """Assert the number of sub-assistants matches the expected count."""
        expect(self.sub_assistant_items).to_have_count(expected_count)

    @step
    def should_have_datasource_attached(self, datasource_name: str):
        """
        Verify that a datasource is attached to the assistant.

        Args:
            datasource_name: Name of the datasource to verify

        Returns:
            self: Returns the page object for method chaining
        """
        expect(self.config_additional_datasource_context_label).to_be_visible()
        datasource_badge = self.page.locator(f'text="{datasource_name}"')
        expect(datasource_badge).to_be_visible()
        return self

    # --------------------------
    # --- ACTIONS ---
    # --------------------------

    @step
    def click_assistant_id_copy_button(self):
        """Click the copy button for assistant ID."""
        self.overview_assistant_id_copy_button.click()
        return self

    @step
    def click_details_link_copy_button(self):
        """Click the copy button for assistant details link."""
        self.details_link_copy_button.click()
        return self

    @step
    def click_chat_link_copy_button(self):
        """Click the copy button for chat link."""
        self.chat_link_copy_button.click()
        return self

    @step
    def click_sub_assistant(self, name: str):
        """Click on a sub-assistant item."""
        self.sub_assistant_item_by_name(name).click()
        return self
