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

import json

from codemie_test_harness.tests.enums.tools import Toolkit, AzureDevOpsWikiTool
from codemie_test_harness.tests.utils.ado_names import (
    ADO_ORGANIZATION_NAME,
    ADO_URL,
    ADO_WIKI_NAME,
)
from codemie_test_harness.tests.utils.ado_seed import ADO_SEED, AdoSeed, SeedIdentity
from codemie_test_harness.tests.utils.jira_seed import Seeded


def _identity_minimal(identity: SeedIdentity) -> dict:
    """``SeedIdentity`` as the reduced shape the wiki comments tool output uses."""
    return {
        "displayName": identity.display_name,
        "id": identity.id,
        "uniqueName": identity.unique_name,
    }


def _wiki_comments_json(seed: AdoSeed) -> str:
    """Wiki comments of the seed child page as the get-comments tool returns them."""
    page = seed.wiki_child
    comments = [
        {
            "reactions": [],
            "artifactId": f"{seed.project_id}/{seed.wiki_repository_id}/{page.id}",
            "id": comment.id,
            "version": 1,
            "text": comment.text,
            "renderedText": "",
            "createdBy": _identity_minimal(comment.author_identity),
            "createdDate": comment.created_date,
            "modifiedBy": _identity_minimal(comment.author_identity),
            "modifiedDate": comment.created_date,
            "state": "active",
        }
        for comment in reversed(page.comments)
    ]
    return json.dumps(
        {
            "comments": comments,
            "count": len(comments),
            "total_count": len(comments),
            "has_more": False,
        },
        indent=2,
    )


def _get_wiki_json(seed: AdoSeed) -> str:
    """The wiki's own metadata as the get-wiki tool returns it."""
    wiki_url = (
        f"{ADO_URL}/{ADO_ORGANIZATION_NAME}/{seed.project_id}"
        f"/_apis/wiki/wikis/{seed.wiki_repository_id}"
    )
    return json.dumps(
        {
            "mapped_path": "/",
            "name": ADO_WIKI_NAME,
            "project_id": seed.project_id,
            "repository_id": seed.wiki_repository_id,
            "type": "projectWiki",
            "id": seed.wiki_repository_id,
            "remote_url": (
                f"{ADO_URL}/{ADO_ORGANIZATION_NAME}/{seed.project_id}"
                f"/_wiki/wikis/{seed.wiki_repository_id}"
            ),
            "url": wiki_url,
            "versions": [{"version": "wikiMaster"}],
        },
        indent=2,
    )


ado_wiki_get_test_data = [
    (
        Toolkit.AZURE_DEVOPS_WIKI,
        AzureDevOpsWikiTool.GET_WIKI_PAGE_COMMENTS_BY_ID,
        Seeded(
            ADO_SEED,
            lambda seed: {
                "wiki_identified": ADO_WIKI_NAME,
                "page_id": seed.wiki_child.id,
            },
        ),
        Seeded(ADO_SEED, _wiki_comments_json),
    ),
    (
        Toolkit.AZURE_DEVOPS_WIKI,
        AzureDevOpsWikiTool.GET_WIKI_PAGE_COMMENTS_BY_PATH,
        Seeded(
            ADO_SEED,
            lambda seed: {
                "wiki_identified": ADO_WIKI_NAME,
                "page_name": seed.wiki_child.path,
            },
        ),
        Seeded(ADO_SEED, _wiki_comments_json),
    ),
    (
        Toolkit.AZURE_DEVOPS_WIKI,
        AzureDevOpsWikiTool.GET_WIKI_PAGE_BY_ID,
        Seeded(
            ADO_SEED,
            lambda seed: {
                "wiki_identified": ADO_WIKI_NAME,
                "page_id": seed.wiki_parent.id,
            },
        ),
        Seeded(ADO_SEED, lambda seed: seed.wiki_parent.content),
    ),
    (
        Toolkit.AZURE_DEVOPS_WIKI,
        AzureDevOpsWikiTool.GET_WIKI,
        {"wiki_identified": ADO_WIKI_NAME},
        Seeded(ADO_SEED, _get_wiki_json),
    ),
    (
        Toolkit.AZURE_DEVOPS_WIKI,
        AzureDevOpsWikiTool.GET_WIKI_PAGE_BY_PATH,
        Seeded(
            ADO_SEED,
            lambda seed: {
                "wiki_identified": ADO_WIKI_NAME,
                "page_name": seed.wiki_parent.path,
            },
        ),
        Seeded(ADO_SEED, lambda seed: seed.wiki_parent.content),
    ),
]

# === NESTED WIKI PAGES TEST DATA FOR DIRECT TOOLS ===

ADO_WIKI_CREATE_NESTED_PARENT_DIRECT = {
    "wiki_identified": ADO_WIKI_NAME,
    "parent_page_path": "/",
    "new_page_name": "{}",
    "page_content": "Parent Page Content",
    "version_identifier": "main",
    "version_type": "branch",
}

ADO_WIKI_CREATE_NESTED_CHILD_DIRECT = {
    "wiki_identified": ADO_WIKI_NAME,
    "parent_page_path": "/{}",
    "new_page_name": "{}",
    "page_content": "Child Page Content",
    "version_identifier": "main",
    "version_type": "branch",
}

ADO_WIKI_GET_NESTED_PAGE_DIRECT = {
    "wiki_identified": ADO_WIKI_NAME,
    "page_name": "/{}/{}",
}

ADO_WIKI_MOVE_PAGE_DIRECT = {
    "wiki_identified": ADO_WIKI_NAME,
    "source_page_path": "/{}",
    "destination_page_path": "/{}",
    "version_identifier": "main",
    "version_type": "branch",
}
