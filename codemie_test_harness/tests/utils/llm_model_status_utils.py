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

"""Model status utilities.

Thin wrapper over the admin model status and global default calls, plus the
helpers the status tests share: picking a dedicated test model, waiting until
the model catalog shows a new status, and putting everything back.

The status and the global default are platform-wide: every test that changes
one must restore it in a fixture teardown and carry
``xdist_group(name="model_status")`` so that such tests never overlap.
"""

from codemie_sdk import CodeMieClient
from codemie_sdk.models.admin import (
    AdminLLMModel,
    GlobalDefaultLLMModel,
    LLMModelStatusBulkItem,
    LLMModelStatusBulkResult,
    LLMModelStatusUpdate,
)
from codemie_sdk.models.llm import LLMModel, ModelStatus

from codemie_test_harness.tests.utils.base_utils import BaseUtils, poll_until
from codemie_test_harness.tests.utils.logger_util import setup_logger

logger = setup_logger(__name__)

# Models the stand keeps for status tests carry this suffix in their label. Only
# they are ever disabled or deprecated, so other tests keep every regular model.
AUTOTEST_MODEL_LABEL_SUFFIX = "(Autotest)"

# Statuses are served from a per-instance cache with a short lifetime, so a read
# that lands on another instance can lag behind the write that preceded it.
CATALOG_PROPAGATION_TIMEOUT = 30.0

# One read that shows the status only proves that the instance serving it is
# up to date. The call under test may land on another instance, so the status
# must be shown by this many reads in a row.
CONSISTENT_CATALOG_READS = 4


class LlmModelStatusUtils(BaseUtils):
    """Reads and writes model statuses and the global default model."""

    def __init__(self, client: CodeMieClient):
        super().__init__(client)

    # ── Admin API ─────────────────────────────────────────────────────────────

    def list_statuses(self) -> list[AdminLLMModel]:
        """Models the administrator can manage, with their persisted status."""
        return self.client.admin.list_llm_model_statuses()

    def status_of(self, base_name: str) -> ModelStatus | None:
        """Persisted status of one model in the admin list, None when it is not listed."""
        return next(
            (m.status for m in self.list_statuses() if m.base_name == base_name),
            None,
        )

    def set_status(self, base_name: str, status: ModelStatus) -> LLMModelStatusUpdate:
        return self.client.admin.set_llm_model_status(base_name, status)

    def bulk_set_statuses(
        self, updates: list[tuple[str, ModelStatus]]
    ) -> LLMModelStatusBulkResult:
        return self.client.admin.bulk_set_llm_model_statuses(
            [
                LLMModelStatusBulkItem(base_name=base_name, status=status)
                for base_name, status in updates
            ]
        )

    def get_default(self) -> GlobalDefaultLLMModel:
        return self.client.admin.get_global_default_llm_model()

    def set_default(self, base_name: str) -> GlobalDefaultLLMModel:
        return self.client.admin.set_global_default_llm_model(base_name)

    def reset_default(self) -> GlobalDefaultLLMModel:
        return self.client.admin.reset_global_default_llm_model()

    # ── Catalog as a user sees it ─────────────────────────────────────────────

    @staticmethod
    def catalog_of(client: CodeMieClient) -> dict[str, LLMModel]:
        """Models of GET /v1/llm_models for the user behind the client, by base name."""
        return {model.base_name: model for model in client.llms.list()}

    def wait_until_catalog_shows(
        self,
        base_name: str,
        status: ModelStatus,
        *clients: CodeMieClient,
    ) -> None:
        """Wait until the catalog of each client reflects the status of a model.

        A Disabled model leaves the catalog; any other status keeps it listed with
        that status. The status must show on several reads in a row, because the
        reads may be served by different instances. Never raises: whatever the
        catalog still shows when the time is up is what the test asserts on.
        """

        def reflects(catalog: dict[str, LLMModel]) -> bool:
            model = catalog.get(base_name)
            if status == ModelStatus.DISABLED:
                return model is None
            return model is not None and model.status == status

        for client in (self.client, *clients):
            streak = 0

            def reflects_in_a_row(catalog: dict[str, LLMModel]) -> bool:
                nonlocal streak
                streak = streak + 1 if reflects(catalog) else 0
                return streak >= CONSISTENT_CATALOG_READS

            poll_until(
                lambda c=client: self.catalog_of(c),
                reflects_in_a_row,
                timeout=CATALOG_PROPAGATION_TIMEOUT,
            )

    def apply_status(
        self, base_name: str, status: ModelStatus, *clients: CodeMieClient
    ) -> LLMModelStatusUpdate:
        """Set a status and wait until the catalog shows it to the admin and to `clients`."""
        updated = self.set_status(base_name, status)
        self.wait_until_catalog_shows(base_name, status, *clients)
        return updated

    # ── Test model selection and restore ──────────────────────────────────────

    def pick_autotest_models(
        self, count: int, *clients: CodeMieClient
    ) -> list[AdminLLMModel]:
        """Dedicated test models whose status may be changed.

        Only models labelled "(Autotest)" qualify, so no regular model is ever
        disabled or deprecated. A model qualifies when it is Enabled, not a router,
        not the global default, listed in the catalog of the admin and of every
        client in `clients`, and its label is not part of any other model's label
        (so a row, picker option or badge can be found by label alone). Cheapest
        first, so a chat in a test costs as little as possible.

        May return fewer than `count` models when the stand has none left.
        """
        entries = self.list_statuses()
        labels = [entry.label.lower() for entry in entries]
        visible = [
            {
                model.base_name
                for model in user_client.llms.list()
                if model.enabled and not model.is_router and not model.default
            }
            for user_client in (self.client, *clients)
        ]
        shared = set.intersection(*visible)

        def label_is_unique(entry: AdminLLMModel) -> bool:
            label = entry.label.lower()
            return sum(1 for other in labels if label in other) == 1

        candidates = [
            entry
            for entry in entries
            if entry.label.endswith(AUTOTEST_MODEL_LABEL_SUFFIX)
            and entry.model_type == "chat"
            and entry.enabled
            and entry.status == ModelStatus.ENABLED
            and entry.router_type is None
            and entry.base_name in shared
            and label_is_unique(entry)
        ]
        candidates.sort(
            key=lambda e: (
                e.cost.output if e.cost else float("inf"),
                e.base_name,
            )
        )
        return candidates[:count]

    def restore_enabled(self, base_names: list[str]) -> None:
        """Set the models back to Enabled; a failure is logged, never raised."""
        for base_name in base_names:
            try:
                self.set_status(base_name, ModelStatus.ENABLED)
            except Exception as e:
                logger.warning(f"Failed to restore status of model {base_name}: {e}")

    def restore_default(self, saved_base_name: str | None) -> None:
        """Put the saved global default back; a failure is logged, never raised."""
        try:
            if saved_base_name:
                self.set_default(saved_base_name)
            else:
                self.reset_default()
        except Exception as e:
            logger.warning(f"Failed to restore the global default model: {e}")
