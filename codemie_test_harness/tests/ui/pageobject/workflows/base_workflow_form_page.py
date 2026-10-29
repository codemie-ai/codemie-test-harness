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

from playwright.sync_api import Locator, Page, expect
from reportportal_client import step

from codemie_test_harness.tests.ui.pageobject.base_page import BasePage
from codemie_test_harness.tests.ui.pageobject.components import Menu, WorkflowSidebar
from codemie_test_harness.tests.ui.pageobject.workflows.workflow_config_panel import (
    WorkflowConfigPanel,
)


class BaseWorkflowFormPage(BasePage):
    """Base class for workflow form pages with common elements and methods for Visual Editor."""

    def __init__(self, page: Page):
        super().__init__(page)
        self.sidebar = WorkflowSidebar(page)
        self._menu = Menu(page)
        self._config_panel = WorkflowConfigPanel(page)

    # ==============================================
    # PROPERTIES - UI ELEMENTS
    # ==============================================

    # ------ Header Elements ------

    @property
    def cancel_button(self) -> Locator:
        """Cancel button in the header."""
        # Use nth(0) to explicitly get the first Cancel button (header)
        # when node config panel is open, there are multiple Cancel buttons
        return self.page.get_by_role("button", name="Cancel").nth(0)

    @property
    def save_button(self) -> Locator:
        """Save button in the header."""
        return self.page.get_by_role("button", name="Save", exact=True).first

    @property
    def save_and_run_button(self) -> Locator:
        """Save and Run button in the header."""
        return self.page.get_by_role("button", name="Save and Run")

    # ------ Toolbar Elements ------

    @property
    def load_example_button(self) -> Locator:
        """Load Example button in toolbar."""
        return self.page.get_by_role("button", name="Load Example")

    @property
    def beautify_button(self) -> Locator:
        """Beautify layout button in toolbar."""
        return self.page.get_by_role("button", name="Beautify layout")

    @property
    def yaml_button(self) -> Locator:
        """YAML button in toolbar."""
        return self.page.get_by_role("button", name="YAML")

    @property
    def workflow_config_button(self) -> Locator:
        """Workflow Config button in toolbar."""
        return self.page.get_by_role("button", name="Workflow Config")

    # ------ Visual Editor Sidebar (Nodes Palette) ------

    @property
    def nodes_sidebar(self) -> Locator:
        """Left sidebar with draggable nodes."""
        return self.page.get_by_role("complementary").filter(
            has=self.page.get_by_role("heading", name="Nodes")
        )

    @property
    def collapse_sidebar_button(self) -> Locator:
        """Collapse sidebar button."""
        return self.page.get_by_role("button", name="Collapse sidebar")

    @property
    def conditional_node_button(self) -> Locator:
        """Conditional node button in palette."""
        return self.page.get_by_role("button", name="Conditional")

    @property
    def switch_node_button(self) -> Locator:
        """Switch node button in palette."""
        return self.page.get_by_role("button", name="Switch")

    @property
    def iterator_node_button(self) -> Locator:
        """Iterator node button in palette."""
        return self.page.get_by_role("button", name="Iterator")

    @property
    def assistant_node_button(self) -> Locator:
        """Assistant node button in palette."""
        return self.page.get_by_role("button", name="Assistant", exact=True)

    @property
    def tool_node_button(self) -> Locator:
        """Tool node button in palette."""
        return self.page.get_by_role("button", name="Tool").first

    @property
    def custom_node_button(self) -> Locator:
        """Custom node button in palette."""
        return self.page.get_by_role("button", name="Custom")

    @property
    def transform_node_button(self) -> Locator:
        """Transform node button in palette."""
        return self.page.get_by_role("button", name="Transform")

    @property
    def note_node_button(self) -> Locator:
        """Note node button in palette."""
        return self.page.get_by_role("button", name="Note")

    # ------ Visual Editor Canvas ------

    @property
    def canvas(self) -> Locator:
        """Main visual editor canvas."""
        return self.page.locator('[role="application"]')

    @property
    def start_node(self) -> Locator:
        """Start node on canvas."""
        return self.canvas.get_by_text("Start")

    @property
    def end_node(self) -> Locator:
        """End node on canvas."""
        return self.canvas.get_by_text("End")

    @property
    def canvas_zoom_in_button(self) -> Locator:
        """Zoom in button on canvas."""
        return self.page.get_by_role("button", name="Zoom in")

    @property
    def canvas_zoom_out_button(self) -> Locator:
        """Zoom out button on canvas."""
        return self.page.get_by_role("button", name="Zoom out")

    @property
    def canvas_fit_view_button(self) -> Locator:
        """Fit view button on canvas."""
        return self.page.get_by_role("button", name="Fit view")

    @property
    def canvas_lock_button(self) -> Locator:
        """Lock button on canvas."""
        return self.page.get_by_role("button", name="Lock")

    @property
    def canvas_download_button(self) -> Locator:
        """Download button on canvas."""
        return self.page.get_by_role("button", name="Download")

    @property
    def canvas_nodes(self) -> Locator:
        """All node elements rendered on the visual editor canvas.

        The Visual Editor is built on ReactFlow. Confirmed via live
        playwright-cli DOM inspection
        (Edit Workflow page): each node renders with class
        ``react-flow__node react-flow__node-<type>`` and
        ``data-testid="rf__node-<state_id>"`` (e.g. ``rf__node-start``,
        ``rf__node-end``, ``rf__node-<assistant_state_id>``).
        """
        return self.canvas.locator(".react-flow__node")

    @property
    def non_default_canvas_nodes(self) -> Locator:
        """Canvas nodes excluding the default "Start"/"End" nodes.

        Uses the confirmed ``data-testid="rf__node-start"``/``rf__node-end``
        attributes (stable regardless of node display text) rather than
        text-based filtering. Useful for asserting that content (e.g.
        AI-generated states) was actually added to the canvas, without
        depending on non-deterministic generated node names/content.
        """
        return self.canvas.locator(
            '.react-flow__node:not([data-testid="rf__node-start"])'
            ':not([data-testid="rf__node-end"])'
        )

    # ==============================================
    # METHODS - ACTIONS & INTERACTIONS
    # ==============================================

    # ------ Header Actions ------
    @step
    def click_back(self):
        """Click the back button."""
        self.back_button.click()

    @step
    def click_cancel(self):
        """Click the cancel button."""
        self.cancel_button.click()

    @step
    def click_save(self):
        """Click the save button."""
        self.save_button.click()

    @step
    def wait_for_save_redirect(self):
        """Wait for the page to stabilize after saving the workflow."""
        self.page.wait_for_load_state("networkidle", timeout=30000)

    @step
    def click_save_and_run(self):
        """Click the save and run button."""
        self.save_and_run_button.click()

    # ------ Toolbar Actions ------
    @step
    def open_workflow_config_panel(self) -> WorkflowConfigPanel:
        """
        Open the workflow config panel if not already open.

        Returns:
            WorkflowConfigPanel: The config panel component instance
        """
        if not self._config_panel.is_visible():
            self.workflow_config_button.click()
            expect(self._config_panel.config_panel).to_be_visible()

        return self._config_panel

    @step
    def open_yaml_panel(self) -> WorkflowConfigPanel:
        """
        Open Workflow config panel with YAML tab.

        Returns:
            WorkflowConfigPanel: The config panel component instance
        """
        self.yaml_button.click()
        expect(self._config_panel.yaml_tab).to_be_visible()
        return self._config_panel

    @step
    def click_beautify(self):
        """Click beautify layout button."""
        self.beautify_button.click()

    # ------ Node Palette Actions ------
    @step
    def add_assistant_node(self):
        """Add assistant node to canvas by clicking it in palette."""
        self.assistant_node_button.click()
        # Wait for the node to be added and state to update
        self.canvas.get_by_text("Assistant_1").wait_for(state="visible", timeout=5000)

    @step
    def add_tool_node(self):
        """Add tool node to canvas by clicking it in palette."""
        self.tool_node_button.click()

    @step
    def add_conditional_node(self):
        """Add conditional node to canvas by clicking it in palette."""
        self.conditional_node_button.click()

    @step
    def add_iterator_node(self):
        """Add iterator node to canvas by clicking it in palette."""
        self.iterator_node_button.click()

    @step
    def click_first_generated_node(self):
        """Click the first non-default (non Start/End) node on the canvas.

        Opens that node's configuration panel, mirroring the behavior of
        clicking a manually-added node (see ``add_assistant_node``).
        """
        self.non_default_canvas_nodes.first.click()
        return self

    @step
    def open_assistant_node_config_panel(self):
        """Click the first assistant node on the canvas and wait for its config panel.

        Returns:
            AssistantNodeConfigPanel: The config panel component instance.
        """
        from codemie_test_harness.tests.ui.pageobject.workflows.assistant_node_config_panel import (
            AssistantNodeConfigPanel,
        )

        self.non_default_canvas_nodes.first.click()
        panel = AssistantNodeConfigPanel(self.page)
        expect(panel.config_panel).to_be_visible()
        return panel

    @step
    def drag_node_by_offset(self, node: Locator, dx: float, dy: float):
        """Drag a canvas node by the given pixel offset using mouse actions.

        Args:
            node: Locator for the node to drag (e.g. ``non_default_canvas_nodes.first``).
            dx: Horizontal offset in pixels.
            dy: Vertical offset in pixels.

        Returns:
            The node's bounding box before the drag, for position-change assertions.
        """
        box = node.bounding_box()
        assert box is not None, "Node should be visible before dragging"
        start_x = box["x"] + box["width"] / 2
        start_y = box["y"] + box["height"] / 2

        self.page.mouse.move(start_x, start_y)
        self.page.mouse.down()
        self.page.mouse.move(start_x + dx, start_y + dy, steps=10)
        self.page.mouse.up()
        return box

    # ==============================================
    # METHODS - VERIFICATION & ASSERTIONS (continued)
    # ==============================================
    @step
    def should_have_node_moved(
        self, node: Locator, original_box: dict, min_delta: float = 20
    ):
        """Verify a node's bounding box moved by at least ``min_delta`` px from ``original_box``."""
        moved_box = node.bounding_box()
        assert moved_box is not None, (
            "Node should still be present on the canvas after drag"
        )
        assert (
            abs(moved_box["x"] - original_box["x"]) > min_delta
            or abs(moved_box["y"] - original_box["y"]) > min_delta
        ), (
            f"Expected node position to change after drag. "
            f"Before: {original_box}, After: {moved_box}"
        )
        return self

    # ==============================================
    # METHODS - VERIFICATION & ASSERTIONS
    # ==============================================

    # ------ Canvas Verifications ------
    @step
    def should_have_canvas_visible(self):
        """Verify that the visual editor canvas is visible."""
        expect(self.canvas).to_be_visible()
        expect(self.start_node).to_be_visible()
        expect(self.end_node).to_be_visible()

    @step
    def should_have_node_on_canvas(self, node_type: str):
        """Verify that a node of the specified type exists on canvas."""
        node = self.canvas.get_by_text(node_type)
        expect(node).to_be_visible()

    @step
    def should_have_assistant_node_visible(self, node_name: str):
        """Verify that an assistant node with the specified name is visible on canvas."""
        assistant_node = self.canvas.get_by_text(node_name)
        expect(assistant_node).to_be_visible()

    @step
    def should_have_generated_nodes(self):
        """Verify at least one non-default (AI-generated) node is on the canvas.

        Does not assert on exact node count/content, since generation is
        LLM-driven and non-deterministic — only that generation populated the
        canvas beyond the default Start/End nodes.
        """
        expect(self.non_default_canvas_nodes.first).to_be_visible(timeout=10000)
        return self

    # NOTE: Old visualization section methods removed as the UI has changed to Visual Editor

    # ------ General Form Verifications ------
    @step
    def should_have_all_form_sections_visible(self):
        """Verify that all main visual editor sections are visible."""
        expect(self.canvas).to_be_visible()
        expect(self.nodes_sidebar).to_be_visible()
        return self

    # ------ Header Button Verifications ------
    @step
    def should_have_save_button_enabled(self):
        """Verify that the save button is enabled."""
        expect(self.save_button).to_be_enabled()
        return self

    @step
    def should_have_save_button_disabled(self):
        """Verify that the save button is disabled."""
        expect(self.save_button).to_be_disabled()
        return self
