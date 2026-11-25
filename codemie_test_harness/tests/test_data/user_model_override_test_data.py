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

"""Test data for the user model override API tests."""

from dataclasses import dataclass

# Capabilities of a stand: the override of a user, and the model settings of a project.
BOTH_FEATURES = ("features:userModelOverride", "features:projectModelOverride")

# Messages and details the platform answers with.
BATCH_FAILED_MESSAGE = "Batch operation failed; no users updated"
NOT_A_MEMBER_REASON = "User not a member of this project"
OVERRIDE_NOT_FOUND_MESSAGE = "Override not found"
PROJECT_NOT_FOUND_MESSAGE = "Project not found"
DEPRECATED_NOT_ADDED_MESSAGE = "Deprecated model ids cannot be added to an override"
NOT_IN_OVERRIDE_DETAILS = (
    "Model is not in the user's model override. Please use available models."
)
DEFAULT_OUTSIDE_ALLOWED_DETAILS = (
    "default_model must be one of the override's allowed_models"
)

# Activity events of the user management domain.
ACTIVITY_DOMAIN = "user_management"
OVERRIDE_SET_EVENT = "user.model_override.set"
OVERRIDE_REMOVED_EVENT = "user.model_override.removed"

# Bounds of the override requests.
MAX_ALLOWED_MODELS = 100
MAX_BATCH_USER_IDS = 500


def not_allowed_message(model: str, project: str) -> str:
    """Message of the refusal for a model that a project or an override does not allow."""
    return f"Model '{model}' is not allowed for project '{project}'"


def deprecated_not_added_message(*models: str) -> str:
    """Message of the refusal for deprecated models the override does not already list."""
    return f"{DEPRECATED_NOT_ADDED_MESSAGE}: {list(models)}"


# ── Routes: name → call as (utils, project, user_id, models) ─────────────────

OVERRIDE_ROUTES = {
    "put": lambda utils, project, user_id, models: utils.set_override(
        project, user_id, models
    ),
    "get": lambda utils, project, user_id, models: utils.get_override(project, user_id),
    "list": lambda utils, project, user_id, models: utils.list_overrides(project),
    "delete": lambda utils, project, user_id, models: utils.delete_override(
        project, user_id
    ),
    "batch": lambda utils, project, user_id, models: utils.batch_grant(
        project, [user_id], models
    ),
    "batch_revoke": lambda utils, project, user_id, models: utils.batch_revoke(
        project, [user_id]
    ),
}


# ── Invalid requests ──────────────────────────────────────────────────────────
# Model names are given as keys of the picked models ("a", "b"); any other text is sent as it is.


@dataclass(frozen=True)
class InvalidOverride:
    """A request the platform must refuse: what it carries, the status and the text it answers with."""

    allowed_models: list[str]
    default_model: str | None
    status: int
    message_part: str = ""
    details_part: str = ""


INVALID_PUT_REQUESTS = {
    "blank_model_id": InvalidOverride(
        allowed_models=["a", "   "],
        default_model=None,
        status=422,
        message_part="model ids must not be blank",
    ),
    "empty_allowed_models": InvalidOverride(
        allowed_models=[],
        default_model=None,
        status=422,
        message_part="at least 1 item",
    ),
    "too_many_models": InvalidOverride(
        allowed_models=[f"model-{index}" for index in range(MAX_ALLOWED_MODELS + 1)],
        default_model=None,
        status=422,
        message_part=f"at most {MAX_ALLOWED_MODELS} items",
    ),
    "default_outside_allowed_models": InvalidOverride(
        allowed_models=["a"],
        default_model="b",
        status=400,
        message_part="is not allowed for project",
        details_part=DEFAULT_OUTSIDE_ALLOWED_DETAILS,
    ),
}


@dataclass(frozen=True)
class InvalidBatch:
    """A batch request the platform must refuse; user ids are the project members unless counted."""

    operation: str
    user_count: int | None
    allowed_models: list[str] | None
    message: str

    def user_ids(self, member_ids: list[str]) -> list[str]:
        """The members, or as many made-up ids as the request must carry."""
        if self.user_count is None:
            return member_ids
        return [f"user-{index}" for index in range(self.user_count)]

    def models(self, named: dict[str, str]) -> list[str] | None:
        """The models of the request with the picked ones named; None when it carries none."""
        if self.allowed_models is None:
            return None
        return [named.get(token, token) for token in self.allowed_models]


INVALID_BATCH_REQUESTS = {
    "grant_without_models": InvalidBatch(
        operation="grant",
        user_count=None,
        allowed_models=None,
        message="allowed_models required for grant operation",
    ),
    "no_users": InvalidBatch(
        operation="grant",
        user_count=0,
        allowed_models=["a"],
        message="user_ids must not be empty",
    ),
    "too_many_users": InvalidBatch(
        operation="grant",
        user_count=MAX_BATCH_USER_IDS + 1,
        allowed_models=["a"],
        message=f"user_ids is limited to {MAX_BATCH_USER_IDS} entries",
    ),
    "unknown_operation": InvalidBatch(
        operation="merge",
        user_count=None,
        allowed_models=["a"],
        message="operation must be one of ['grant', 'revoke']",
    ),
}


# ── Model list default ────────────────────────────────────────────────────────
# Models are named by role: "x" and "y" are two models, "platform" is the platform default.


@dataclass(frozen=True)
class DefaultTier:
    """What the project and the override set, and the model the list must flag as default."""

    project_default: str | None
    override_default: str | None
    expected: str


DEFAULT_TIERS = {
    "override_default_wins": DefaultTier(
        project_default="y", override_default="x", expected="x"
    ),
    "project_default_without_override_default": DefaultTier(
        project_default="y", override_default=None, expected="y"
    ),
    "platform_default_without_any": DefaultTier(
        project_default=None, override_default=None, expected="platform"
    ),
}
