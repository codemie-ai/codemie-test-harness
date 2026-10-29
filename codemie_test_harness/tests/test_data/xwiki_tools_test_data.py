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

"""Test data for xWiki datasource and tool tests.

The space, page, title and token come from the seed page that ensure_seed_page()
writes on every run (see utils/xwiki_seed.py), not from hardcoded values.
"""

import pytest

from codemie_test_harness.tests.enums.tools import XWikiTool
from codemie_test_harness.tests.utils.jira_seed import Seeded
from codemie_test_harness.tests.utils.xwiki_seed import SEED_TITLE

XWIKI_DATASOURCE_PROMPT = f"What is the token value stored on the {SEED_TITLE} page?"

# Read-only tools, exercised against the persistent seed page so no page has to
# be created for them. Seeded rows resolve against the `xwiki_seed_page` fixture.
#
# These check a plain substring (via hamcrest's contains_string), not the LLM
# similarity grader: the live wiki is shared and keeps growing (other spaces,
# pages, tags get added over time, and xdist runs other tests' pages concurrently),
# so "list"/"search" responses are long and mostly irrelevant to any one row.
# The grader scores *overall* closeness between actual and expected, not whether
# expected's claim is entailed by actual — a short, single-fact expected_response
# gets swamped and scored low even when the fact is right there in a longer actual
# (verified live: a 60-threshold grading of a correct "List Spaces" answer scored
# 45 because the real response also listed several other, unrelated spaces).
# A plain substring check has no such problem.
xwiki_read_test_data = [
    pytest.param(
        XWikiTool.LIST_WIKIS,
        "List all wikis available in the xWiki instance.",
        Seeded("xwiki_seed_page", lambda seed: seed.wiki),
    ),
    pytest.param(
        XWikiTool.GET_WIKI,
        Seeded(
            "xwiki_seed_page",
            lambda seed: f"Show the details of the '{seed.wiki}' wiki.",
        ),
        Seeded("xwiki_seed_page", lambda seed: seed.wiki),
    ),
    pytest.param(
        XWikiTool.LIST_SPACES,
        Seeded(
            "xwiki_seed_page",
            lambda seed: "List the top-level spaces in the 'xwiki' wiki.",
        ),
        Seeded("xwiki_seed_page", lambda seed: seed.space.split(".")[0]),
    ),
    pytest.param(
        XWikiTool.GET_SPACE,
        Seeded(
            "xwiki_seed_page",
            lambda seed: f"Get the details of the space '{seed.space}' in the 'xwiki' wiki.",
        ),
        Seeded("xwiki_seed_page", lambda seed: seed.space.split(".")[0]),
    ),
    pytest.param(
        XWikiTool.LIST_PAGES,
        Seeded(
            "xwiki_seed_page",
            lambda seed: f"List the pages in the space '{seed.space}' of the 'xwiki' wiki.",
        ),
        Seeded("xwiki_seed_page", lambda seed: seed.page),
    ),
    pytest.param(
        XWikiTool.LIST_WIKI_PAGES,
        Seeded(
            "xwiki_seed_page",
            lambda seed: f"List up to 500 pages across the whole 'xwiki' wiki and "
            f"check whether the page '{seed.page}' is included.",
        ),
        Seeded("xwiki_seed_page", lambda seed: seed.page),
    ),
    pytest.param(
        XWikiTool.GET_PAGE,
        Seeded(
            "xwiki_seed_page",
            lambda seed: f"Get the page '{seed.page}' in space '{seed.space}' of the "
            "'xwiki' wiki and tell me the token value stored in it.",
        ),
        Seeded("xwiki_seed_page", lambda seed: seed.token),
    ),
    pytest.param(
        XWikiTool.SEARCH_WIKI,
        Seeded(
            "xwiki_seed_page",
            lambda seed: f"Search the whole 'xwiki' wiki for pages whose title is "
            f"'{seed.title}' (use the 'title' scope).",
        ),
        Seeded("xwiki_seed_page", lambda seed: seed.title),
    ),
    pytest.param(
        XWikiTool.SEARCH_SPACE,
        Seeded(
            "xwiki_seed_page",
            lambda seed: f"Search within the space '{seed.space}' for the phrase "
            "'token value of the CodeMie Test Harness seed'.",
        ),
        Seeded("xwiki_seed_page", lambda seed: seed.title),
    ),
]

# ---------------------------------------------------------------------------
# Lifecycle tools: a fresh space created per test run (not the shared seed
# space), so pages, tags, comments and attachments can be created, read back
# and deleted without touching the persistent datasource seed. Every dict
# below is .format()-ed with (space, page_name[, tag_or_comment[, comment_id]]).
# ---------------------------------------------------------------------------

XWIKI_CREATE_WEBHOME = {
    "prompt_to_assistant": "In the xWiki space '{0}', create a page named 'WebHome' "
    "with title 'Autotest Home' and content 'Root page for autotest xWiki tool "
    "coverage.'",
    "expected_llm_answer": "The page 'WebHome' was created in space '{0}' with the "
    "title 'Autotest Home'.",
}

XWIKI_CREATE_CHILD_PAGE = {
    "prompt_to_assistant": "In the xWiki space '{0}', create a page named '{1}' with "
    "title '{1}' and content 'Child page content before modification.'",
    "expected_llm_answer": "The page '{1}' was created in space '{0}' with the title "
    "'{1}'.",
}

XWIKI_LIST_PAGE_CHILDREN = {
    "prompt_to_assistant": "List the direct child pages of the page '{1}' in space "
    "'{0}'.",
    "expected_llm_answer": "The page '{1}' in space '{0}' has no child pages; the "
    "list of children is empty.",
}

XWIKI_MODIFY_CHILD_PAGE = {
    "prompt_to_assistant": "In space '{0}', update the content of page '{1}' to "
    "'Child page content after modification.', keeping the existing title.",
    "expected_llm_answer": "The page '{1}' in space '{0}' was updated; its content "
    "is now 'Child page content after modification.'",
}

XWIKI_SET_PAGE_TAGS = {
    "prompt_to_assistant": "Set the tags of page '{1}' in space '{0}' to exactly: {2}.",
    "expected_llm_answer": "The tags of page '{1}' in space '{0}' are now set to {2}.",
}

XWIKI_LIST_PAGE_TAGS = {
    "prompt_to_assistant": "List the tags currently applied to page '{1}' in space "
    "'{0}'.",
    "expected_llm_answer": "The tags on page '{1}' in space '{0}' include {2}.",
}

#  Checked with contains_string, not similarity_check: the wiki-wide tag list
# grows over time and under xdist other workers' tests add their own tags
# concurrently, so a short expected claim gets swamped the same way the "List
# Spaces" read test's did (see xwiki_read_test_data's comment above).
XWIKI_LIST_WIKI_TAGS = {
    "prompt_to_assistant": "List all tags used across the 'xwiki' wiki and tell me "
    "whether the tag {2} is among them.",
}

XWIKI_CREATE_PAGE_COMMENT = {
    "prompt_to_assistant": "Add a comment with the text '{2}' to page '{1}' in space "
    "'{0}'. Reply with the created comment's numeric 'id' field in the exact format "
    "COMMENT_ID: <id> (id may legitimately be 0 — xWiki numbers comments per-page "
    "starting at 0).",
    "expected_llm_answer": "The comment '{2}' was added to page '{1}'; its numeric "
    "id is reported as COMMENT_ID: <some number>.",
}

XWIKI_LIST_PAGE_COMMENTS = {
    "prompt_to_assistant": "List the comments on page '{1}' in space '{0}'.",
    "expected_llm_answer": "The comments on page '{1}' include the text '{2}'.",
}

XWIKI_GET_PAGE_COMMENT = {
    "prompt_to_assistant": "Get the comment with id {3} on page '{1}' in space '{0}'.",
    "expected_llm_answer": "The comment with id {3} on page '{1}' has the text '{2}'.",
}

# CreatePageAttachmentTool used to multipart-POST to the attachments collection
# resource, which xWiki's CSRF filter rejected with 403 "Invalid or missing form
# token" under both Bearer and Basic Auth (verified live); it now PUTs to the named
# attachment resource instead, which the filter doesn't intercept.
XWIKI_CREATE_PAGE_ATTACHMENT = {
    "file_name": "test.txt",
    "prompt_to_assistant": "Attach the uploaded file to page '{1}' in space '{0}'.",
    "expected_llm_answer": "The file 'test.txt' was attached to page '{1}'.",
}

XWIKI_LIST_PAGE_ATTACHMENTS = {
    "prompt_to_assistant": "List the attachments on page '{1}' in space '{0}'.",
    "expected_llm_answer": "The attachments on page '{1}' include the file 'test.txt'.",
}

XWIKI_GET_PAGE_ATTACHMENT = {
    "prompt_to_assistant": "Get the metadata of the attachment 'test.txt' on page "
    "'{1}' in space '{0}'.",
    "expected_llm_answer": "The attachment 'test.txt' on page '{1}' has mime type "
    "text/plain.",
}

XWIKI_READ_PAGE_ATTACHMENT_CONTENT = {
    "prompt_to_assistant": "Read the content of the attachment 'test.txt' on page "
    "'{1}' in space '{0}'.",
    "expected_llm_answer": "The content of the attachment 'test.txt' is: This file "
    "is for test purpose.",
}

XWIKI_DELETE_PAGE_ATTACHMENT = {
    "prompt_to_assistant": "Delete the attachment 'test.txt' from page '{1}' in "
    "space '{0}'.",
    "expected_llm_answer": "The attachment 'test.txt' was deleted from page '{1}'.",
}

XWIKI_DELETE_PAGE = {
    "prompt_to_assistant": "Delete the page '{1}' in space '{0}'.",
    "expected_llm_answer": "The page '{1}' in space '{0}' was deleted.",
}
