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

"""Test data for the CLI session classification and routing tests."""

from dataclasses import dataclass

import pytest

from codemie_test_harness.tests.utils.cli_classification_utils import (
    ORGANIZATION_ENCODING,
    encode_organization,
)

# Discard reasons and error identifiers of the classification and session guards.
STALE_POLICY = "stale_policy"
ORGANIZATION_INVALID = "organization_invalid"
ORGANIZATION_REQUIRED = "organization_required"
SESSION_ID_REQUIRED = "session_id_required"
EVIDENCE_SESSION_CONFLICT = "evidence_session_conflict"
SESSION_OWNER_CONFLICT = "session_owner_conflict"
SESSION_PROJECT_CONFLICT = "session_project_conflict"
SESSION_PROJECT_UNAVAILABLE = "session_project_unavailable"
DEFAULT_PROJECT_UNAVAILABLE = "default_project_unavailable"

# Values of the subscription_type and project_origin fields.
CODEMIE = "codemie"
CORPORATE = "corporate"
PERSONAL = "personal"
UNKNOWN = "unknown"
LINKED_FOLDER = "linked_folder"
PROFILE = "profile"
REGISTERED_REPOSITORY = "registered_repository"
DEFAULT_PROJECT = "default_project"

# route_note values.
FOLDER_NOT_LINKED = "folder_not_linked"
LINKED_PROJECT_UNAVAILABLE = "linked_project_unavailable"
REGISTERED_PROJECT_INACCESSIBLE = "registered_project_inaccessible"

FOLDER_NOT_LINKED_LABEL = "folder not linked to a project"


# ── Routed-via-CodeMie header precedes any organization ─────────────────────────


@dataclass(frozen=True)
class RoutedCase:
    routed_value: str
    organization: str | None  # key of OrganizationPlan.pick


ROUTED_CASES = [
    pytest.param(RoutedCase("1", "corporate"), id="1-organization-in-list"),
    pytest.param(RoutedCase("true", "other"), id="true-organization-not-in-list"),
    pytest.param(RoutedCase("yes", None), id="yes-no-organization"),
]


# ── Organization spellings that all match the corporate list ────────────────────

ORGANIZATION_SPELLINGS = [
    pytest.param(lambda organization: {"organization": organization}, id="plain"),
    pytest.param(
        lambda organization: {"organization": organization.upper()},
        id="upper-case",
    ),
    pytest.param(
        lambda organization: {
            "organization_encoded": encode_organization(f"  {organization.upper()}  ")
        },
        id="utf8-b64u-v1-encoded-padded-and-upper-case",
    ),
    pytest.param(
        lambda organization: {
            "organization_encoded": encode_organization(organization)
        },
        id="utf8-b64u-v1-encoded",
    ),
]


# ── Classification header validation ────────────────────────────────────────────

# Limits of the encoded organization: payload at most 1366 characters, decoded at most 1024 bytes
# and 256 code points. A code point is at most 4 bytes, so 256 code points never exceed 1024 bytes,
# and 1024 bytes are exactly 1366 unpadded base64url characters: only the code-point limit can be
# broken alone (257 one-byte characters); the byte and payload limits can only be broken together
# with it. Every value is printable text, so a refusal can only come from a size limit.
MAX_ORGANIZATION_CODE_POINTS = 256
MAX_ORGANIZATION_BYTES = 1024
FOUR_BYTE_CODE_POINT = "\U0001f600"

INVALID_ORGANIZATION_ENVELOPES = [
    pytest.param(f"{ORGANIZATION_ENCODING}:!!not-base64url!!", id="malformed-payload"),
    pytest.param(
        encode_organization("a" * (MAX_ORGANIZATION_CODE_POINTS + 1)),
        id="over-256-code-points-under-1024-bytes",
    ),
    pytest.param(
        encode_organization("a" * (MAX_ORGANIZATION_BYTES + 1)),
        id="over-1024-bytes-1366-payload-characters-and-256-code-points",
    ),
    pytest.param(
        encode_organization(FOUR_BYTE_CODE_POINT * (MAX_ORGANIZATION_CODE_POINTS + 1)),
        id="over-1024-bytes-with-four-byte-code-points",
    ),
    pytest.param(encode_organization("org\x07name"), id="control-character"),
    pytest.param("utf8-b64u.v0:YWJj", id="unsupported-version"),
]

# Printable values exactly at the limits: accepted and classified from the decoded name.
ORGANIZATION_ENVELOPES_AT_THE_LIMIT = [
    pytest.param(
        encode_organization("a" * MAX_ORGANIZATION_CODE_POINTS),
        id="256-code-points-256-bytes",
    ),
    pytest.param(
        encode_organization(FOUR_BYTE_CODE_POINT * MAX_ORGANIZATION_CODE_POINTS),
        id="256-code-points-1024-bytes-1366-payload-characters",
    ),
]

CLAIMED_TYPES_NEEDING_ORGANIZATION = ["personal", "corporate"]


# ── Destination order ───────────────────────────────────────────────────────────
# Project keys: A (member, linked), B (member, repository registered), D (member, the default),
# N (enabled, the sender is not a member, repository registered).


@dataclass(frozen=True)
class PlacementRow:
    subscription: str  # corporate | codemie | unknown
    link: str | None  # key of the project in X-CodeMie-Project (linked_folder)
    registered: (
        str | None
    )  # key of the project whose registered remote the session reports
    project: str  # key of the project the session must be stored in
    origin: str
    note: str | None


PLACEMENT_ROWS = [
    pytest.param(
        PlacementRow(CORPORATE, "A", "B", "A", LINKED_FOLDER, None),
        id="corporate-accessible-link-beats-registration",
    ),
    pytest.param(
        PlacementRow(CODEMIE, None, "B", "B", REGISTERED_REPOSITORY, None),
        id="codemie-registered-repository",
    ),
    pytest.param(
        PlacementRow(UNKNOWN, "N", "B", "B", REGISTERED_REPOSITORY, None),
        id="unknown-inaccessible-link-falls-to-registration",
    ),
    pytest.param(
        PlacementRow(
            UNKNOWN, "N", None, "D", DEFAULT_PROJECT, LINKED_PROJECT_UNAVAILABLE
        ),
        id="unknown-inaccessible-link-falls-to-default",
    ),
    pytest.param(
        PlacementRow(
            CORPORATE, None, "N", "D", DEFAULT_PROJECT, REGISTERED_PROJECT_INACCESSIBLE
        ),
        id="corporate-inaccessible-registration-falls-to-default",
    ),
]


@dataclass(frozen=True)
class ProfileRow:
    profile_project: (
        str | None
    )  # key of the project the profile sends (project source profile)
    registered: str | None
    project: str
    origin: str
    note: str | None


PROFILE_ROWS = [
    pytest.param(
        ProfileRow("A", "B", "A", PROFILE, None),
        id="profile-project-beats-registration",
    ),
    pytest.param(
        ProfileRow(None, "B", "B", REGISTERED_REPOSITORY, None),
        id="no-profile-project-falls-to-registration",
    ),
    pytest.param(
        ProfileRow(None, None, "D", DEFAULT_PROJECT, FOLDER_NOT_LINKED),
        id="no-profile-project-no-registration-falls-to-default",
    ),
]


# ── Repository registration API ─────────────────────────────────────────────────

PLACEHOLDER_REMOTE = "https://example.com/autotest/registration-api-check.git"


@dataclass(frozen=True)
class RegistrationErrorRow:
    method: str
    target: str  # personal | shared
    remote: str
    status: int
    message: str


REGISTRATION_ERROR_ROWS = [
    pytest.param(
        RegistrationErrorRow(
            "PUT",
            "personal",
            PLACEHOLDER_REMOTE,
            400,
            "Personal projects cannot have registered repositories",
        ),
        id="register-on-personal-project",
    ),
    pytest.param(
        RegistrationErrorRow(
            "PUT", "shared", "not a remote", 400, "Unparseable repository remote"
        ),
        id="register-unparseable-remote",
    ),
    pytest.param(
        RegistrationErrorRow(
            "DELETE",
            "shared",
            PLACEHOLDER_REMOTE,
            404,
            "Repository registration not found",
        ),
        id="unregister-missing-registration",
    ),
]
