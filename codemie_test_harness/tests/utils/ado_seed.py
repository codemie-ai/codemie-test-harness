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

"""Seed data for Azure DevOps tests: persistent work items, wiki pages and a test plan.

Pure logic only (no HTTP) so it can be unit tested; AdoUtils performs the
requests. Every seed is created once in the configured project and reused by
every later run, so tests never depend on pre-existing IDs.
"""

import re
from dataclasses import asdict, dataclass
from typing import Optional

WORK_ITEM_TITLE = "CodeMie Test Harness Seed Work Item"
WORK_ITEM_DESCRIPTION = "Seed work item used by codemie-test-harness Azure DevOps tests. Do not delete or edit."
PARENT_WORK_ITEM_TITLE = "CodeMie Test Harness Seed Parent Work Item"
PARENT_WORK_ITEM_DESCRIPTION = "Seed parent work item used by codemie-test-harness Azure DevOps tests. Do not delete or edit."
PARENT_WORK_ITEM_COMMENT = "CodeMie autotest verification comment."

ATTACHMENT_FILE_NAME = "codemie-test-harness-seed-attachment.txt"
ATTACHMENT_CONTENT = (
    "This is the CodeMie Test Harness seed attachment. Do not delete or edit."
)
ATTACHMENT_MIME_TYPE = "text/plain"

WIKI_PARENT_TITLE = "CodeMie Test Harness Seed Parent Page"
WIKI_PARENT_CONTENT = "Parent Page Content"
WIKI_CHILD_TITLE = "CodeMie Test Harness Seed Child Page"
WIKI_CHILD_CONTENT = "Child Page Content"
WIKI_CHILD_COMMENTS = (
    "This is comment for the seed child page",
    "And second comment",
)

TEST_PLAN_NAME = "CodeMie Test Harness Seed Test Plan"
TEST_SUITE_NAME = "CodeMie Test Harness Seed Test Suite"
TEST_CASE_TITLE = "CodeMie Test Harness Seed Test Case"
TEST_CASE_DESCRIPTION = (
    "Verify ADO Test Plan tools against the CodeMie Test Harness seed plan."
)

ADO_SEED = "ado_seed"
ADO_TEST_PLAN_SEED = "ado_test_plan_seed"


@dataclass(frozen=True)
class SeedIdentity:
    """An Azure DevOps identity, as the API reports it for a creator/owner/author.

    Read from the live API at seed time, never hardcoded: the values belong to
    whichever account the configured access token belongs to.
    """

    display_name: str
    unique_name: str
    id: str
    descriptor: str
    profile_url: str
    avatar_url: str

    @classmethod
    def from_api(cls, data: dict) -> "SeedIdentity":
        """Build from a raw identity object (``createdBy``, ``System.CreatedBy``, ``owner``...)."""
        return cls(
            display_name=data["displayName"],
            unique_name=data["uniqueName"],
            id=data["id"],
            descriptor=data.get("descriptor", ""),
            profile_url=data.get("url", ""),
            avatar_url=data.get("imageUrl")
            or data.get("_links", {}).get("avatar", {}).get("href", ""),
        )

    @classmethod
    def from_dict(cls, data: dict) -> "SeedIdentity":
        return cls(**data)


@dataclass(frozen=True)
class SeedComment:
    id: int
    text: str
    author: str
    created_date: str
    author_identity: Optional[SeedIdentity] = None

    @classmethod
    def from_dict(cls, data: dict) -> "SeedComment":
        identity = data.get("author_identity")
        return cls(
            **{
                **data,
                "author_identity": SeedIdentity.from_dict(identity)
                if identity
                else None,
            }
        )


@dataclass(frozen=True)
class SeedAttachment:
    """A known file attached to a seed work item or wiki page.

    Deliberately a plain-text file: its content is asserted verbatim by
    tests, so it must not depend on PDF/image text-extraction or OCR.
    """

    id: str
    name: str
    size: int
    mime_type: str
    content: str

    @classmethod
    def from_dict(cls, data: dict) -> "SeedAttachment":
        return cls(**data)


@dataclass(frozen=True)
class SeedWorkItem:
    id: int
    title: str
    type: str
    # Read from the live API after creation, not hardcoded: the initial
    # state/reason and default priority are defined by the project's
    # process template (Basic, Agile, Scrum, CMMI...) and can differ across
    # organizations/projects.
    state: str
    priority: int
    reason: str
    description: str
    created_date: str
    url: str
    comments: tuple[SeedComment, ...] = ()
    attachment: Optional[SeedAttachment] = None
    created_by: Optional[SeedIdentity] = None

    @classmethod
    def from_dict(cls, data: dict) -> "SeedWorkItem":
        attachment = data.get("attachment")
        created_by = data.get("created_by")
        return cls(
            **{
                **data,
                "comments": tuple(
                    SeedComment.from_dict(c) for c in data.get("comments", ())
                ),
                "attachment": SeedAttachment.from_dict(attachment)
                if attachment
                else None,
                "created_by": SeedIdentity.from_dict(created_by)
                if created_by
                else None,
            }
        )


@dataclass(frozen=True)
class SeedWikiPage:
    id: int
    path: str
    title: str
    content: str
    comments: tuple[SeedComment, ...] = ()
    attachment: Optional[SeedAttachment] = None

    @classmethod
    def from_dict(cls, data: dict) -> "SeedWikiPage":
        attachment = data.get("attachment")
        return cls(
            **{
                **data,
                "comments": tuple(
                    SeedComment.from_dict(c) for c in data.get("comments", ())
                ),
                "attachment": SeedAttachment.from_dict(attachment)
                if attachment
                else None,
            }
        )


@dataclass(frozen=True)
class SeedTestPlan:
    id: int
    name: str
    start_date: str
    end_date: str
    updated_date: str
    root_suite_id: int
    root_suite_name: str
    suite_id: int
    suite_name: str
    test_case_id: int
    test_case_title: str
    test_case_description: str
    test_case_priority: int
    test_case_automation_status: str
    project_id: str = ""
    owner: Optional[SeedIdentity] = None
    updated_by: Optional[SeedIdentity] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SeedTestPlan":
        owner = data.get("owner")
        updated_by = data.get("updated_by")
        return cls(
            **{
                **data,
                "owner": SeedIdentity.from_dict(owner) if owner else None,
                "updated_by": SeedIdentity.from_dict(updated_by)
                if updated_by
                else None,
            }
        )


@dataclass(frozen=True)
class AdoSeed:
    work_item: SeedWorkItem
    parent_work_item: SeedWorkItem
    wiki_parent: SeedWikiPage
    wiki_child: SeedWikiPage
    # Read from the live API (GET project / GET wiki), not hardcoded: these
    # GUIDs are assigned by Azure DevOps and differ per org/project/wiki.
    project_id: str
    wiki_repository_id: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AdoSeed":
        return cls(
            work_item=SeedWorkItem.from_dict(data["work_item"]),
            parent_work_item=SeedWorkItem.from_dict(data["parent_work_item"]),
            wiki_parent=SeedWikiPage.from_dict(data["wiki_parent"]),
            wiki_child=SeedWikiPage.from_dict(data["wiki_child"]),
            project_id=data["project_id"],
            wiki_repository_id=data["wiki_repository_id"],
        )


def build_seed_wiql(project: str, title: str, work_item_type: str = "") -> str:
    """WIQL matching work items by exact title within the project."""
    type_clause = (
        f" AND [System.WorkItemType] = '{work_item_type}'" if work_item_type else ""
    )
    return (
        "SELECT [System.Id] FROM WorkItems "
        f"WHERE [System.TeamProject] = '{project}' "
        f"AND [System.Title] = '{title}'{type_clause}"
    )


def find_attachment_relation(relations: list[dict], file_name: str) -> Optional[dict]:
    """The work item's ``AttachedFile`` relation for ``file_name``, if it already has one."""
    return next(
        (
            rel
            for rel in relations
            if rel.get("rel") == "AttachedFile"
            and rel.get("attributes", {}).get("name") == file_name
        ),
        None,
    )


def attachment_id_from_url(url: str) -> str:
    """The attachment GUID embedded in its ADO download URL."""
    match = re.search(r"attachments/([0-9a-fA-F-]{36})", url)
    if not match:
        raise ValueError(f"Could not find an attachment id in URL: {url}")
    return match.group(1)


def select_seed_comments(
    raw_comments: list[dict], comment_texts: tuple[str, ...]
) -> tuple[SeedComment, ...]:
    """Seed comments (oldest first) whose text is one of ``comment_texts``."""
    wanted = set(comment_texts)
    return tuple(
        SeedComment(
            id=int(c["id"]),
            text=c["text"],
            author=c["createdBy"]["displayName"],
            created_date=c["createdDate"],
            author_identity=SeedIdentity.from_api(c["createdBy"]),
        )
        for c in sorted(raw_comments, key=lambda c: int(c["id"]))
        if c.get("text") in wanted
    )
