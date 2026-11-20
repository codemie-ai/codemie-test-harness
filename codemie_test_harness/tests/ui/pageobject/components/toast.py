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

from playwright.sync_api import Locator, expect
from reportportal_client import step

TOAST_TIMEOUT_MS = 15_000
VARIANT_CLASSES = {
    "success": "codemie-toast-success",
    "info": "codemie-toast-info",
    "error": "codemie-toast-err",
}
ERROR_TOAST_SELECTOR = f".{VARIANT_CLASSES['error']}"
ALL_VARIANTS = tuple(VARIANT_CLASSES)
CONFIRMATION_VARIANTS = ("success", "info")


class Toast:
    """Toast notifications stacked in the app's toast container (codemie-toast markup)."""

    def __init__(self, page):
        self.page = page

    @property
    def container(self) -> Locator:
        """Region the toasts are stacked in."""
        return self.page.locator("#toast-container")

    @property
    def all_toasts(self) -> Locator:
        """Every open toast, whatever its variant."""
        return self.container.locator(".codemie-toast")

    @property
    def error(self) -> Locator:
        """The first error toast."""
        return self.container.locator(ERROR_TOAST_SELECTOR).first

    @property
    def error_header(self) -> Locator:
        """Header of the first error toast."""
        return self.error.locator(".codemie-toast-header")

    def _toasts(self, variants) -> Locator:
        return self.container.locator(
            ", ".join(f".{VARIANT_CLASSES[variant]}" for variant in variants)
        )

    def _with_text(self, text: str, variants, exact: bool = False) -> Locator:
        if exact:
            return self._toasts(variants).filter(
                has=self.page.get_by_text(text, exact=True)
            )
        return self._toasts(variants).filter(has_text=text)

    @step
    def should_show(
        self,
        text: str,
        variants=CONFIRMATION_VARIANTS,
        exact: bool = False,
    ):
        """A toast of the variants shows the text in its header or content.

        `exact` asks for an element whose whole text is `text`.
        """
        expect(self._with_text(text, variants, exact).first).to_be_visible(
            timeout=TOAST_TIMEOUT_MS
        )
        return self

    @step
    def should_show_any(self, variants=CONFIRMATION_VARIANTS, timeout=TOAST_TIMEOUT_MS):
        """A toast of the variants is visible, whatever its text."""
        expect(self._toasts(variants).first).to_be_visible(timeout=timeout)
        return self

    @step
    def should_not_show(self, text: str = None, variants=ALL_VARIANTS):
        """No toast of the variants is open, or none of them shows the text."""
        toasts = self._toasts(variants)
        if text is not None:
            toasts = toasts.filter(has_text=text)
        expect(toasts).to_have_count(0)
        return self

    @step
    def should_show_error(self, header: str, content: str):
        """The error toast shows the header and contains the content."""
        expect(self.error).to_be_visible(timeout=TOAST_TIMEOUT_MS)
        expect(self.error_header).to_have_text(header)
        expect(self.error.locator(".codemie-toast-content")).to_contain_text(content)
        return self

    @step
    def should_show_error_text(self, text: str, timeout=TOAST_TIMEOUT_MS):
        """The error toast contains the text."""
        expect(self.error).to_contain_text(text, timeout=timeout)
        return self

    @step
    def should_disappear(self, timeout=TOAST_TIMEOUT_MS, move_cursor_away=True):
        """Every toast leaves the screen by itself, with no click.

        The cursor moves off the toasts first, as hovering a toast holds it open; pass
        `move_cursor_away=False` to check that a toast goes away under the cursor.
        """
        if move_cursor_away:
            self.page.mouse.move(0, 0)
        expect(self.all_toasts).to_have_count(0, timeout=timeout)
        return self
