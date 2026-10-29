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

import pytest

from codemie_test_harness.tests.enums.tools import Toolkit, AzureDevOpsWorkItemTool
from codemie_test_harness.tests.utils.ado_names import ADO_PROJECT_NAME, ado_text
from codemie_test_harness.tests.utils.ado_seed import ADO_SEED, SeedIdentity
from codemie_test_harness.tests.utils.jira_seed import Seeded


def _identity_camel(identity: SeedIdentity) -> dict:
    """``SeedIdentity`` as the camelCase shape raw ADO API identities use
    (``System.CreatedBy``, ``System.ChangedBy``, ...)."""
    return {
        "displayName": identity.display_name,
        "url": identity.profile_url,
        "_links": {"avatar": {"href": identity.avatar_url}},
        "id": identity.id,
        "uniqueName": identity.unique_name,
        "imageUrl": identity.avatar_url,
        "descriptor": identity.descriptor,
    }


def _identity_snake(identity: SeedIdentity) -> dict:
    """``SeedIdentity`` as the snake_case shape the comments tool output uses."""
    return {
        "_links": {},
        "descriptor": identity.descriptor,
        "display_name": identity.display_name,
        "url": identity.profile_url,
        "id": identity.id,
        "image_url": identity.avatar_url,
        "unique_name": identity.unique_name,
    }


def _get_work_item_json(seed) -> str:
    return json.dumps(
        {
            "id": seed.work_item.id,
            "url": seed.work_item.url,
            "System.AreaPath": ADO_PROJECT_NAME,
            "System.TeamProject": ADO_PROJECT_NAME,
            "System.IterationPath": ADO_PROJECT_NAME,
            "System.WorkItemType": seed.work_item.type,
            "System.State": seed.work_item.state,
            "System.Reason": seed.work_item.reason,
            "System.CreatedDate": seed.work_item.created_date,
            "System.CreatedBy": _identity_camel(seed.work_item.created_by),
            "System.ChangedDate": seed.work_item.created_date,
            "System.ChangedBy": _identity_camel(seed.work_item.created_by),
            "System.CommentCount": 0,
            "System.Title": seed.work_item.title,
            "Microsoft.VSTS.Common.StateChangeDate": seed.work_item.created_date,
            "Microsoft.VSTS.Common.Priority": seed.work_item.priority,
            "System.Description": seed.work_item.description,
        },
        indent=2,
    )


def _get_comments_json(seed) -> str:
    comment = seed.parent_work_item.comments[0]
    return json.dumps(
        [
            {
                "url": f"{seed.parent_work_item.url}/comments/{comment.id}",
                "created_by": _identity_snake(comment.author_identity),
                "created_date": comment.created_date,
                "format": "html",
                "id": comment.id,
                "mentions": [],
                "modified_by": _identity_snake(comment.author_identity),
                "modified_date": comment.created_date,
                "rendered_text": "",
                "text": comment.text,
                "version": 1,
                "work_item_id": seed.parent_work_item.id,
            }
        ],
        indent=2,
    )


# Regression data for create/update work_item_json payloads
# containing literal (unescaped) newlines inside HTML field values, the
# real-world shape of the LLM-generated payload that triggered
# "Expecting ',' delimiter" before the _sanitize_json_control_chars fix
# (codemie/src/codemie_tools/azure_devops/work_item/tools.py). The `\n`
# below are genuine embedded newline bytes, not the two-character escape
# sequence `\n` a valid JSON string would use.
ADO_WORK_ITEM_CREATE_MALFORMED_JSON_DIRECT = {
    "wi_type": "Task",
    "work_item_json": ado_text(
        '{{"fields":{{'
        '"System.Title":"{title}",'
        '"System.Description":"<p><strong>Summary</strong><br/>\n'
        "Analyse the existing implementation and orchestration\n"
        'across the affected tables.</p>",'
        '"Microsoft.VSTS.Common.AcceptanceCriteria":"<p><strong>1. Flow documented</strong><br/>\n'
        "Given existing documentation and code have been reviewed,\n"
        'when the analysis is complete, then the flow is documented.</p>",'
        '"System.AreaPath":"<ADO_PROJECT>",'
        '"Microsoft.VSTS.Common.ValueArea":"Business",'
        '"System.IterationPath":"<ADO_PROJECT>",'
        '"System.Tags":"AI-Assisted;AI-Assistant-BA"'
        "}}}}"
    ),
}

ADO_WORK_ITEM_UPDATE_MALFORMED_JSON_DIRECT = {
    "work_item_json": (
        '{{"fields":{{'
        '"System.Title":"{title}",'
        '"System.Description":"<p><strong>Updated summary</strong><br/>\n'
        "Revised after analysis, spanning\n"
        'multiple literal lines.</p>",'
        '"Microsoft.VSTS.Common.AcceptanceCriteria":"<p><strong>1. Revised criteria</strong><br/>\n'
        "Given the update payload has literal newlines,\n"
        'when the tool parses it, then it must not fail.</p>",'
        '"System.Tags":"AI-Assisted;AI-Assistant-BA"'
        "}}}}"
    ),
}

ado_work_item_get_test_data = [
    (
        Toolkit.AZURE_DEVOPS_WORK_ITEM,
        AzureDevOpsWorkItemTool.GET_WORK_ITEM,
        Seeded(ADO_SEED, lambda seed: {"id": str(seed.work_item.id)}),
        Seeded(ADO_SEED, _get_work_item_json),
    ),
    (
        Toolkit.AZURE_DEVOPS_WORK_ITEM,
        AzureDevOpsWorkItemTool.GET_COMMENTS,
        Seeded(
            ADO_SEED,
            lambda seed: {"work_item_id": str(seed.parent_work_item.id)},
        ),
        Seeded(ADO_SEED, _get_comments_json),
    ),
    (
        Toolkit.AZURE_DEVOPS_WORK_ITEM,
        AzureDevOpsWorkItemTool.GET_RELATION_TYPES,
        {},
        """
            {
              "Affects" : "Microsoft.VSTS.Common.Affects-Forward",
              "Affected By" : "Microsoft.VSTS.Common.Affects-Reverse",
              "Referenced By" : "Microsoft.VSTS.TestCase.SharedParameterReferencedBy-Forward",
              "References" : "Microsoft.VSTS.TestCase.SharedParameterReferencedBy-Reverse",
              "Tested By" : "Microsoft.VSTS.Common.TestedBy-Forward",
              "Tests" : "Microsoft.VSTS.Common.TestedBy-Reverse",
              "Test Case" : "Microsoft.VSTS.TestCase.SharedStepReferencedBy-Forward",
              "Shared Steps" : "Microsoft.VSTS.TestCase.SharedStepReferencedBy-Reverse",
              "Produces For" : "System.LinkTypes.Remote.Dependency-Forward",
              "Consumes From" : "System.LinkTypes.Remote.Dependency-Reverse",
              "Duplicate" : "System.LinkTypes.Duplicate-Forward",
              "Duplicate Of" : "System.LinkTypes.Duplicate-Reverse",
              "Successor" : "System.LinkTypes.Dependency-Forward",
              "Predecessor" : "System.LinkTypes.Dependency-Reverse",
              "Child" : "System.LinkTypes.Hierarchy-Forward",
              "Parent" : "System.LinkTypes.Hierarchy-Reverse",
              "Related" : "System.LinkTypes.Related",
              "Remote Related" : "System.LinkTypes.Remote.Related",
              "Attached File" : "AttachedFile",
              "Hyperlink" : "Hyperlink",
              "Artifact Link" : "ArtifactLink"
            }
        """,
    ),
    (
        Toolkit.AZURE_DEVOPS_WORK_ITEM,
        AzureDevOpsWorkItemTool.SEARCH_WORK_ITEMS,
        Seeded(
            ADO_SEED,
            lambda seed: {
                "query": "SELECT [System.Id], [System.Title], [System.State] FROM WorkItems WHERE "
                f"[System.TeamProject] = '{ADO_PROJECT_NAME}' AND "
                f"[System.Title] = '{seed.work_item.title}'",
                "limit": 1,
            },
        ),
        Seeded(
            ADO_SEED,
            lambda seed: f"""
            [ {{
              "id" : {seed.work_item.id},
              "url" : "{seed.work_item.url}",
              "System.Title" : "{seed.work_item.title}",
              "System.State" : "{seed.work_item.state}",
              "System.AssignedTo" : "N/A",
              "System.CreatedDate" : "{seed.work_item.created_date}",
              "System.ChangedDate" : "{seed.work_item.created_date}"
            }} ]
        """,
        ),
    ),
    pytest.param(
        Toolkit.AZURE_DEVOPS_WORK_ITEM,
        AzureDevOpsWorkItemTool.GET_WORK_ITEM_ATTACHMENT_CONTENT,
        Seeded(
            ADO_SEED,
            lambda seed: {
                "work_item_id": str(seed.work_item.id),
                "attachment_name": seed.work_item.attachment.name,
            },
        ),
        Seeded(
            ADO_SEED,
            lambda seed: f"""
            {{
              "work_item_id" : "{seed.work_item.id}",
              "filename" : "{seed.work_item.attachment.name}",
              "mime_type" : "{seed.work_item.attachment.mime_type}",
              "size_bytes" : {seed.work_item.attachment.size},
              "content_type" : "text",
              "content" : "{seed.work_item.attachment.content}"
            }}
        """,
        ),
        marks=pytest.mark.smoke,
    ),
]
