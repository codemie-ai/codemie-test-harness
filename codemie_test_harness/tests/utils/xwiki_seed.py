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

"""Seed data for xWiki datasource tests: a persistent page with a known token.

Pure logic only (no HTTP) so it can be unit tested; XWikiUtils performs the
requests. The seed page lives in the configured space under a fixed name and
is rewritten with the same content on every run, so tests never depend on a
hand-prepared instance and repeated runs never create duplicate pages.
"""

from dataclasses import asdict, dataclass

SEED_TITLE = "CodeMie Test Harness Seed Page"
# Page name is the REST identifier; xWiki page names carry no spaces by convention.
SEED_PAGE_NAME = "CodeMieTestHarnessSeedPage"
SEED_TOKEN_VALUE = "xwiki-seed-token-7f3a"
SEED_CONTENT = (
    f"The token value of the CodeMie Test Harness seed is {SEED_TOKEN_VALUE}. "
    "Do not delete or edit this page."
)
# The seed page is always written to the "xwiki" wiki (XWikiUtils._page_endpoint
# targets /rest/wikis/xwiki). Carried on the seed so test data derives the wiki
# name from one place instead of duplicating the literal.
SEED_WIKI = "xwiki"


@dataclass(frozen=True)
class XWikiSeedPage:
    space: str
    page: str = SEED_PAGE_NAME
    title: str = SEED_TITLE
    token: str = SEED_TOKEN_VALUE
    wiki: str = SEED_WIKI

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "XWikiSeedPage":
        return cls(**data)
