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

"""Page object for the Create / Edit Project modal.

Used on /settings/administration/projects.
"""

import json
import re

from playwright.sync_api import Locator, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage


class ProjectModal(BasePage):
    """Create / Edit project modal — display_name input, slug field, save/cancel."""

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def modal(self) -> Locator:
        """The modal dialog element."""
        return self.page.get_by_role("dialog")

    @property
    def display_name_input(self) -> Locator:
        """The 'Display Name' text input inside the modal."""
        return self.modal.get_by_label("Display Name")

    @property
    def technical_name_input(self) -> Locator:
        """The read-only technical name / slug field inside the modal (id='name')."""
        return self.modal.locator("#name")

    @property
    def description_input(self) -> Locator:
        """The description textarea inside the modal."""
        return self.modal.get_by_label("Description")

    @property
    def description_label(self) -> Locator:
        """The Description field's own <label>, including any required-asterisk suffix."""
        return self.modal.locator("label[for='description']")

    @property
    def description_error(self) -> Locator:
        """The inline validation-error node for the Description field (rendered only when
        the Textarea component receives a non-empty `error` prop; id="description-error").
        """
        return self.modal.locator("#description-error")

    @property
    def save_button(self) -> Locator:
        """The Save (edit) or Create (create) button that submits the modal."""
        return self.modal.get_by_role("button", name="Save", exact=True).or_(
            self.modal.get_by_role("button", name="Create", exact=True)
        )

    @property
    def cancel_button(self) -> Locator:
        """The Cancel button that dismisses the modal without saving."""
        return self.modal.get_by_role("button", name="Cancel")

    # ── CLI Analytics setting ─────────────────────────────────
    # FE source of truth (codemie-ui, branch for this feature):
    #   src/pages/settings/administration/projectsManagement/ProjectModal.tsx:248-276
    #     <div data-tooltip-content="Only Global Administrators and Maintainers can change
    #          this setting"  (set only for non-writers)>
    #       <Switch id="cli_analytics_enabled" label="Enable CLI Analytics" hint="Allow analytics
    #               ingestion for this project. ..." disabled={!canWriteCliAnalytics} />
    #   src/components/form/Switch/Switch.tsx:68-128: <label><input id role="switch"
    #     type="checkbox" class="sr-only"/> ... label text ... <TooltipButton content=hint/></label>
    #   src/components/TooltipButton/TooltipButton.tsx: <button aria-label="More information"
    #     data-tooltip-content=hint/> plus <div role="status" class="sr-only">hint</div>
    # The branch has no data-testid for this control, so the stable hooks are the input id and
    # the role/ARIA attributes above. The switch is rendered only in edit mode, only when the
    # backend sent the key (ProjectModal.tsx:82-85), and never for personal projects.

    READ_ONLY_TOOLTIP = (
        "Only Global Administrators and Maintainers can change this setting"
    )
    CLI_ANALYTICS_HINT = (
        "Allow analytics ingestion for this project. Turning this off discards incoming "
        "analytics; existing data remains available."
    )

    @property
    def enable_ai_attribution_switch(self) -> Locator:
        """The 'Enable AI Attribution' switch input (id='cli_analytics_enabled', role=switch)."""
        return self.modal.locator("#cli_analytics_enabled")

    @property
    def enable_ai_attribution_row(self) -> Locator:
        """The <label> that wraps the switch, its text and the hint button."""
        # `has` must be relative to the label (not rooted at the dialog), hence page.locator here
        return self.modal.locator("label").filter(
            has=self.page.locator("#cli_analytics_enabled")
        )

    @property
    def enable_ai_attribution_label_text(self) -> Locator:
        """The visible 'Enable AI Attribution' text."""
        return self.enable_ai_attribution_row.get_by_text(
            "Enable AI Attribution", exact=True
        )

    @property
    def cli_analytics_hint_button(self) -> Locator:
        """The info button whose data-tooltip-content carries the hint."""
        return self.enable_ai_attribution_row.get_by_role(
            "button", name="More information"
        )

    @property
    def cli_analytics_hint_status(self) -> Locator:
        """The screen-reader copy of the hint (role=status)."""
        return self.enable_ai_attribution_row.get_by_role("status")

    @property
    def cli_analytics_read_only_tooltip(self) -> Locator:
        """The wrapper carrying the read-only tooltip (present for non-writers only)."""
        return self.modal.locator(f'[data-tooltip-content="{self.READ_ONLY_TOOLTIP}"]')

    # ── Edit Project with a second dialog open ────────────────
    # While the enforcement confirmation is open there are two dialogs, so the generic `modal`
    # locator above is ambiguous. These are scoped to the Edit Project dialog by its header.
    # FE source of truth (codemie-ui):
    #   src/pages/settings/administration/projectsManagement/ProjectModal.tsx (header 'Edit Project')
    #   .../components/EnforceMemberSpendLimitsField.tsx (Switch id='enforce_member_spend_limits',
    #     label 'Enforce member spend limits')

    @property
    def edit_dialog(self) -> Locator:
        """The Edit Project dialog, told apart from a dialog stacked above it."""
        return self.page.get_by_role("dialog", name="Edit Project")

    @property
    def edit_description_input(self) -> Locator:
        """The description textarea inside the Edit Project dialog."""
        return self.edit_dialog.get_by_label("Description", exact=True)

    @property
    def enforce_switch(self) -> Locator:
        """The 'Enforce member spend limits' switch input (id='enforce_member_spend_limits')."""
        return self.edit_dialog.locator("#enforce_member_spend_limits")

    @property
    def enforce_switch_label(self) -> Locator:
        """The visible label text of the enforcement switch (the input is visually hidden)."""
        return self.edit_dialog.get_by_text("Enforce member spend limits", exact=True)

    @property
    def edit_save_button(self) -> Locator:
        """The Save button of the Edit Project dialog."""
        return self.edit_dialog.get_by_role("button", name="Save", exact=True)

    # ── Actions ───────────────────────────────────────────────────────────────

    @step
    def save_capturing_request(self, project_name: str) -> dict:
        """Click Save and return the JSON body of the PATCH /v1/projects/<name> it sends."""
        with self.page.expect_request(
            lambda r: r.method == "PATCH" and f"/v1/projects/{project_name}" in r.url,
            timeout=15000,
        ) as request_info:
            self.click_save()
        return request_info.value.post_data_json

    @step
    def save_edit_capturing_request(self, project_name: str) -> dict:
        """Click Save in the Edit Project dialog and return the JSON body of the
        PATCH /v1/projects/<name> it sends. The click is scoped to Edit Project, so a
        confirmation still fading out above it cannot make the locator ambiguous."""
        with self.page.expect_request(
            lambda r: r.method == "PATCH" and f"/v1/projects/{project_name}" in r.url,
            timeout=15000,
        ) as request_info:
            self.edit_save_button.click()
        return request_info.value.post_data_json

    @step
    def start_counting_save_requests(self, project_name: str):
        """Count every project PATCH the browser sends from now on (held or not)."""
        pattern = re.compile(rf"/v1/projects/{re.escape(project_name)}(\?.*)?$")
        self._counted_saves = []

        def count(request):
            if request.method == "PATCH" and pattern.search(request.url):
                self._counted_saves.append(request.url)

        self._save_counter = count
        self.page.on("request", count)
        return self

    @property
    def sent_save_count(self) -> int:
        """How many project PATCHes the browser sent since start_counting_save_requests()."""
        return len(self._counted_saves)

    @step
    def stop_counting_save_requests(self) -> int:
        """Stop counting and return how many project PATCHes were sent."""
        self.page.remove_listener("request", self._save_counter)
        return self.sent_save_count

    @step
    def press_escape(self):
        """Press the Escape key, then let the browser render two frames so a dialog that the
        key closes is gone before any assertion runs."""
        self.page.keyboard.press("Escape")
        self.page.evaluate(
            "() => new Promise(resolve => requestAnimationFrame("
            "() => requestAnimationFrame(resolve)))"
        )
        return self

    @step
    def toggle_cli_analytics(self):
        """Click the switch's label (the input itself is visually hidden)."""
        self.enable_ai_attribution_label_text.click()
        return self

    @step
    def append_to_edit_description(self, suffix: str):
        """Append text to the description in the Edit Project dialog."""
        current = self.edit_description_input.input_value()
        self.edit_description_input.fill(current + suffix)
        return self

    @step
    def toggle_enforcement(self):
        """Click the enforcement switch's label (the input itself is visually hidden)."""
        self.enforce_switch_label.click()
        return self

    @step
    def click_save_to_confirm_enforcement(self):
        """Click Save in Edit Project, which opens the enforcement confirmation."""
        self.edit_save_button.click()
        return self

    @step
    def hold_save_requests(self, project_name: str):
        """Hold the project PATCH the browser sends, without answering it.

        The held request is later sent unchanged to the real backend by
        release_held_save_requests(): the response is never faked. Other requests to the same
        URL (the project GET) pass through at once.
        """
        self._held_saves = []
        self._held_save_pattern = re.compile(
            rf"/v1/projects/{re.escape(project_name)}(\?.*)?$"
        )

        def hold(route):
            if route.request.method == "PATCH":
                self._held_saves.append(route)
            else:
                route.continue_()

        self.page.route(self._held_save_pattern, hold)
        return self

    @step
    def release_held_save_requests(self):
        """Send every held project PATCH to the real backend and stop holding."""
        for held in self._held_saves:
            held.continue_()
        self._held_saves.clear()
        self.page.unroute(self._held_save_pattern)
        return self

    @step
    def fail_next_save_request(self, project_name: str, message: str):
        """Make the browser's next project PATCH fail with HTTP 500 carrying `message` and let
        every later request through.

        Client-side fault injection: the failed request never reaches the backend, so the test
        can then check that nothing was stored and that a retry reaches the real backend. The
        route lives as long as the page; after the one failure it only passes requests on.
        """
        self._failing_save_pattern = re.compile(
            rf"/v1/projects/{re.escape(project_name)}(\?.*)?$"
        )
        self._failed_once = False

        def fail_once(route):
            if route.request.method == "PATCH" and not self._failed_once:
                self._failed_once = True
                route.fulfill(
                    status=500,
                    content_type="application/json",
                    body=json.dumps({"error": {"message": message}}),
                )
            else:
                route.continue_()

        self.page.route(self._failing_save_pattern, fail_once)
        return self

    @step
    def fill_display_name(self, value: str):
        """Type a value into the Display Name field."""
        self.display_name_input.fill(value)
        return self

    @step
    def fill_technical_name(self, value: str):
        """Type a value into the technical Name field (create mode only)."""
        self.technical_name_input.fill(value)
        return self

    @step
    def fill_description(self, value: str):
        """Type a value into the Description field."""
        self.description_input.fill(value)
        return self

    @step
    def click_save(self):
        """Click the Save / Create button."""
        self.save_button.click()
        self.page.wait_for_timeout(1000)
        return self

    @step
    def click_cancel(self):
        """Click the Cancel button."""
        self.cancel_button.click()
        self.page.wait_for_timeout(500)
        return self

    # ── Assertions ────────────────────────────────────────────────────────────

    @step
    def should_be_visible(self):
        """Verify the modal is open."""
        expect(self.modal).to_be_visible()
        return self

    @step
    def should_have_display_name_input(self):
        """Verify the Display Name input field is present in the modal."""
        expect(self.display_name_input).to_be_visible()
        return self

    @step
    def should_have_display_name_value(self, expected_value: str):
        """Verify the Display Name input shows the expected value."""
        expect(self.display_name_input).to_have_value(expected_value)
        return self

    @step
    def should_have_technical_name_input(self):
        """Verify the Name * field is present and editable (create mode)."""
        expect(self.technical_name_input).to_be_visible()
        expect(self.technical_name_input).not_to_be_disabled()
        return self

    @step
    def should_have_technical_name_disabled(self):
        """Verify that the technical name field is disabled (edit mode)."""
        expect(self.technical_name_input).to_be_disabled()
        return self

    @step
    def should_have_technical_name_value(self, expected_value: str):
        """Verify the technical name field shows the expected slug."""
        expect(self.technical_name_input).to_have_value(expected_value)
        return self

    @step
    def should_have_technical_name_slug_populated(self, timeout: int = 5000):
        """Verify the technical name field is populated with a valid slug derived from display_name.

        Uses Playwright retry-until-pass semantics to avoid a race with the async JS slug
        generator. Asserts: non-empty, lowercase, no spaces (pattern ^[a-z][a-z0-9_-]*$).
        """
        expect(self.technical_name_input).to_have_value(
            re.compile(r"^[a-z][a-z0-9_-]*$"), timeout=timeout
        )
        return self

    @step
    def should_show_display_name_validation_error(self):
        """Verify the inline Yup validation error for a display_name exceeding 150 chars."""
        expect(
            self.modal.get_by_text("Display name cannot exceed 150 characters")
        ).to_be_visible(timeout=5000)
        return self

    @step
    def should_not_show_description_required_indicator(self):
        """Verify the Description label carries no required-field asterisk."""
        expect(self.description_label).to_have_text("Description")
        return self

    @step
    def should_not_show_description_validation_error(self):
        """Verify no inline validation-error node is rendered for the Description field."""
        expect(self.description_error).to_have_count(0)
        return self

    # ── CLI Analytics assertions ──────────────────────────────

    @step
    def should_show_cli_analytics_switch(self):
        """Verify the 'Enable CLI Analytics' switch and its label are shown."""
        expect(self.enable_ai_attribution_switch).to_be_attached(timeout=10000)
        expect(self.enable_ai_attribution_label_text).to_be_visible()
        return self

    @step
    def should_not_show_cli_analytics_switch(self):
        """Verify the switch is not rendered at all (a hidden field, not a disabled one)."""
        expect(self.modal).to_be_visible()
        expect(self.enable_ai_attribution_switch).to_have_count(0)
        expect(self.enable_ai_attribution_label_text).to_have_count(0)
        return self

    @step
    def should_have_cli_analytics_value(self, enabled: bool):
        """Verify the switch state (checked == enabled)."""
        if enabled:
            expect(self.enable_ai_attribution_switch).to_be_checked()
        else:
            expect(self.enable_ai_attribution_switch).not_to_be_checked()
        return self

    @step
    def should_have_cli_analytics_editable(self):
        """Verify the switch can be changed (writer view)."""
        expect(self.enable_ai_attribution_switch).to_be_enabled()
        expect(self.cli_analytics_read_only_tooltip).to_have_count(0)
        return self

    @step
    def should_have_cli_analytics_read_only(self):
        """Verify the switch is disabled and carries the read-only tooltip (Project Admin view)."""
        expect(self.enable_ai_attribution_switch).to_be_disabled()
        expect(self.cli_analytics_read_only_tooltip).to_have_count(1)
        return self

    @step
    def should_show_project_updated_toast(self, project_name: str):
        """Verify the 'Project <name> updated successfully' toast is shown."""
        self.toast.should_show(
            f"Project {project_name} updated successfully", ("info",)
        )
        return self

    @step
    def should_show_cli_analytics_hint(self, expected: str | None = None):
        """Verify the hint copy, both the tooltip attribute and the screen-reader text."""
        expected = expected or self.CLI_ANALYTICS_HINT
        expect(self.cli_analytics_hint_button).to_have_attribute(
            "data-tooltip-content", expected
        )
        expect(self.cli_analytics_hint_status).to_have_text(expected)
        return self

    # ── Enforcement switch assertions ─────────────────────────

    @step
    def should_show_enforcement_switch(self):
        """Verify the Edit Project dialog is open and offers the enforcement switch."""
        expect(self.edit_dialog).to_be_visible()
        expect(self.enforce_switch).to_be_attached(timeout=10000)
        expect(self.enforce_switch).to_be_enabled()
        return self

    @step
    def should_have_enforcement_value(self, enabled: bool):
        """Verify the enforcement switch state (checked == enforcement on)."""
        if enabled:
            expect(self.enforce_switch).to_be_checked()
        else:
            expect(self.enforce_switch).not_to_be_checked()
        return self

    @step
    def should_have_edit_description(self, expected_value: str):
        """Verify the description in the Edit Project dialog."""
        expect(self.edit_description_input).to_have_value(expected_value)
        return self

    @step
    def should_remain_open_for_editing(self):
        """Verify Edit Project is still open and its Save button offered."""
        expect(self.edit_dialog).to_be_visible()
        expect(self.edit_save_button).to_be_visible()
        return self

    @step
    def should_have_save_disabled(self):
        """Verify Edit Project is open and its Save button is disabled."""
        expect(self.edit_dialog).to_be_visible()
        expect(self.edit_save_button).to_be_disabled()
        return self

    @step
    def should_show_save_error(self, message: str):
        """Verify an error toast tells the user the save failed, with the backend's message."""
        self.toast.should_show_error_text(message)
        return self

    @step
    def should_not_show_enforcement_switch(self):
        """Verify the Edit Project dialog is open and does not offer the enforcement switch."""
        expect(self.edit_dialog).to_be_visible()
        expect(self.enforce_switch).to_have_count(0)
        return self

    @step
    def should_not_have_edit_dialog(self):
        """Verify no Edit Project dialog is open (nor, therefore, an enforcement switch).

        Meaningful only after the dialog was open, or after an action that would open it."""
        expect(self.edit_dialog).to_have_count(0)
        return self
