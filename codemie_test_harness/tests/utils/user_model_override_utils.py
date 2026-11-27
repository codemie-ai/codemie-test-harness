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

"""User model override utilities.

Thin wrapper over the per-user model override calls of a project, plus the helpers the
override tests share: picking models that need no status change, reading the model list a
user sees in a project, and setting the model restriction and default of a project.
"""

from codemie_sdk import CodeMieClient
from codemie_sdk.models.llm import LLMModel, ModelStatus

from codemie_test_harness.tests.utils.base_utils import BaseUtils
from codemie_test_harness.tests.utils.llm_model_status_utils import (
    AUTOTEST_MODEL_LABEL_SUFFIX,
)


def pick_override_models(count: int, *clients: CodeMieClient) -> list[str]:
    """Base names of enabled chat models that every client sees, cheapest first.

    Neither the platform default nor a router nor a "(Autotest)" model is picked: the tests
    that change a status or the default own those, so the picked models stay as they are.
    May return fewer than `count` names when the stand has no more.
    """
    catalogs = [{model.base_name: model for model in c.llms.list()} for c in clients]
    shared = set.intersection(*(set(catalog) for catalog in catalogs))
    candidates = [
        model
        for name, model in catalogs[0].items()
        if name in shared
        and model.enabled
        and not model.is_router
        and not model.default
        and model.status in (None, ModelStatus.ENABLED)
        and not (model.label or "").endswith(AUTOTEST_MODEL_LABEL_SUFFIX)
    ]
    candidates.sort(
        key=lambda m: (m.cost.output if m.cost else float("inf"), m.base_name)
    )
    return [model.base_name for model in candidates[:count]]


def resolve_models(tokens: list[str], named: dict[str, str]) -> list[str]:
    """Replace each token that names a picked model with its base name; keep any other text."""
    return [named.get(token, token) for token in tokens]


def pick_web_hidden_model(client: CodeMieClient, project_name: str) -> str | None:
    """Base name of an enabled chat model that the default list leaves out as forbidden for web."""
    shown = {m.base_name for m in client.llms.list_for_project(project_name)}
    return next(
        (
            model.base_name
            for model in client.llms.list_for_project(project_name, include_all=True)
            if model.forbidden_for_web
            and model.enabled
            and not model.is_router
            and model.base_name not in shown
            and model.status in (None, ModelStatus.ENABLED)
        ),
        None,
    )


def platform_default_of(client: CodeMieClient) -> str | None:
    """Base name of the model the unscoped list of the client flags as default."""
    return next((m.base_name for m in client.llms.list() if m.default), None)


class UserModelOverrideUtils(BaseUtils):
    """Reads and writes the model overrides of the project members as the wrapped client."""

    # ── Overrides ─────────────────────────────────────────────────────────────

    def set_override(
        self,
        project_name: str,
        user_id: str,
        allowed_models: list[str],
        default_model: str | None = None,
    ):
        return self.client.projects.set_user_model_override(
            project_name, user_id, allowed_models, default_model
        )

    def get_override(self, project_name: str, user_id: str):
        return self.client.projects.get_user_model_override(project_name, user_id)

    def list_overrides(self, project_name: str, skip: int = 0, limit: int = 100):
        return self.client.projects.list_user_model_overrides(
            project_name, skip=skip, limit=limit
        )

    def users_with_override(self, project_name: str) -> list[str]:
        """IDs of the project members that have an override."""
        return [o.user_id for o in self.list_overrides(project_name)]

    def delete_override(self, project_name: str, user_id: str) -> None:
        self.client.projects.delete_user_model_override(project_name, user_id)

    def batch_grant(
        self,
        project_name: str,
        user_ids: list[str],
        allowed_models: list[str] | None,
        default_model: str | None = None,
    ):
        return self.client.projects.batch_user_model_overrides(
            project_name, "grant", user_ids, allowed_models, default_model
        )

    def batch_revoke(self, project_name: str, user_ids: list[str]):
        """Remove the override of every listed user; answers with the overrides it removed."""
        return self.client.projects.batch_user_model_overrides(
            project_name, "revoke", user_ids
        )

    def batch(
        self,
        project_name: str,
        operation: str,
        user_ids: list[str],
        allowed_models: list[str] | None = None,
    ):
        """A batch request with any operation, as the platform must refuse the invalid ones."""
        return self.client.projects.batch_user_model_overrides(
            project_name, operation, user_ids, allowed_models
        )

    # ── Project model settings ────────────────────────────────────────────────

    def restrict_project_models(
        self, project_name: str, allowed_models: list[str], default_model: str
    ):
        """Limit the project to the models, starting on the default one."""
        return self.client.projects.update_allowed_models(
            project_name, allowed_models=allowed_models, default_model=default_model
        )

    def set_project_default(self, project_name: str, default_model: str | None):
        """Make the model the project default, or remove every project model setting for None."""
        self.client.projects.reset_allowed_models(project_name)
        if default_model:
            self.client.projects.update_allowed_models(
                project_name, default_model=default_model
            )

    # ── Model list of a user in a project ─────────────────────────────────────

    @staticmethod
    def models_listed(
        client: CodeMieClient, project_name: str, include_all: bool = False
    ) -> list[LLMModel]:
        """Models of GET /v1/llm_models?project_id=<project> for the user behind the client."""
        return client.llms.list_for_project(project_name, include_all=include_all)

    @staticmethod
    def base_names_listed(
        client: CodeMieClient, project_name: str, include_all: bool = False
    ) -> list[str]:
        return [
            model.base_name
            for model in UserModelOverrideUtils.models_listed(
                client, project_name, include_all
            )
        ]

    @staticmethod
    def default_base_names_listed(
        client: CodeMieClient, project_name: str
    ) -> list[str]:
        """Base names of the models that the project list flags as default."""
        return [
            model.base_name
            for model in UserModelOverrideUtils.models_listed(client, project_name)
            if model.default
        ]
