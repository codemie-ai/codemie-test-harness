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

"""Seed data for Confluence tests: a persistent marker page.

Pure logic only (no HTTP) so it can be unit tested; ConfluenceUtils performs
the requests. The seed page is created once per Confluence space and reused
by every later run, so tests never depend on pre-existing pages.
"""

from dataclasses import asdict, dataclass
from typing import Optional

SEED_TITLE = "CodeMie Test Harness Seed Page"
SEED_TEXT = (
    "This page is the CodeMie Test Harness Confluence seed page. Do not delete or edit."
)
SEED_BODY = f"<p>{SEED_TEXT}</p>"

CONFLUENCE_SERVER_SEED = "confluence_seed_page"
CONFLUENCE_CLOUD_SEED = "confluence_cloud_seed_page"


@dataclass(frozen=True)
class SeedPage:
    id: str
    space_key: str
    title: str = SEED_TITLE
    body: str = SEED_BODY

    @property
    def cql(self) -> str:
        return build_seed_cql(self.space_key)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SeedPage":
        return cls(**data)


def build_seed_cql(space_key: str) -> str:
    """CQL matching the seed page by exact title within its space.

    Unlike Jira JQL, CQL supports an exact `=` match on title directly, so
    (unlike build_seed_jql) no Python-side exact-match double-check is
    needed for this string itself.
    """
    return f'space = "{space_key}" AND title = "{SEED_TITLE}"'


def find_seed_page_id(pages: list[dict], title: str = SEED_TITLE) -> Optional[str]:
    """Id of the oldest page whose title equals ``title`` exactly."""
    matches = [page for page in pages if page.get("title") == title]
    if not matches:
        return None
    return min(matches, key=lambda page: int(page["id"]))["id"]
