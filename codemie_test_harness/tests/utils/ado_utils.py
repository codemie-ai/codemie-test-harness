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

import base64
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import quote

import requests

from codemie_test_harness.tests.utils.ado_seed import (
    ATTACHMENT_CONTENT,
    ATTACHMENT_FILE_NAME,
    ATTACHMENT_MIME_TYPE,
    PARENT_WORK_ITEM_COMMENT,
    PARENT_WORK_ITEM_DESCRIPTION,
    PARENT_WORK_ITEM_TITLE,
    TEST_CASE_DESCRIPTION,
    TEST_CASE_TITLE,
    TEST_PLAN_NAME,
    TEST_SUITE_NAME,
    WIKI_CHILD_COMMENTS,
    WIKI_CHILD_CONTENT,
    WIKI_CHILD_TITLE,
    WIKI_PARENT_CONTENT,
    WIKI_PARENT_TITLE,
    WORK_ITEM_DESCRIPTION,
    WORK_ITEM_TITLE,
    AdoSeed,
    SeedAttachment,
    SeedIdentity,
    SeedTestPlan,
    SeedWikiPage,
    SeedWorkItem,
    attachment_id_from_url,
    build_seed_wiql,
    find_attachment_relation,
    select_seed_comments,
)
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 60
WORK_ITEMS_API_VERSION = "7.1"
COMMENTS_API_VERSION = "7.1-preview.4"
WIKI_COMMENTS_API_VERSION = "7.1-preview.1"


class AdoUtils:
    """Azure DevOps REST calls used to find or create the seed data.

    Pure seed rules live in ado_seed.py; this class performs the requests.
    """

    def __init__(self):
        self.url = CredentialsManager.get_parameter("AZURE_DEVOPS_URL")
        self.token = CredentialsManager.get_parameter("AZURE_DEVOPS_TOKEN")
        self.org = CredentialsManager.get_parameter("AZURE_DEVOPS_ORGANIZATION_NAME")
        self.project = CredentialsManager.get_parameter("AZURE_DEVOPS_PROJECT_NAME")
        self.wiki = CredentialsManager.azure_devops_wiki_name()

        if not all([self.url, self.token, self.org, self.project, self.wiki]):
            raise ValueError(
                "AZURE_DEVOPS_URL, AZURE_DEVOPS_TOKEN, AZURE_DEVOPS_ORGANIZATION_NAME, "
                "AZURE_DEVOPS_PROJECT_NAME and AZURE_DEVOPS_WIKI_NAME must be set "
                "to create Azure DevOps seed data"
            )

        auth = base64.b64encode(f":{self.token}".encode()).decode()
        self.headers = {"Authorization": f"Basic {auth}", "Accept": "application/json"}
        self.org_url = f"{self.url}/{self.org}"
        self.project_url = f"{self.org_url}/{self.project}"
        self.wiki_url = f"{self.project_url}/_apis/wiki/wikis/{self.wiki}"

    # === SEED ENTRY POINT ===

    def ensure_seed(self) -> AdoSeed:
        """Find or create the work item and wiki seeds; safe to call on every run."""
        return AdoSeed(
            work_item=self.ensure_work_item(
                WORK_ITEM_TITLE,
                WORK_ITEM_DESCRIPTION,
                comment_texts=(),
                with_attachment=True,
            ),
            parent_work_item=self.ensure_work_item(
                PARENT_WORK_ITEM_TITLE,
                PARENT_WORK_ITEM_DESCRIPTION,
                comment_texts=(PARENT_WORK_ITEM_COMMENT,),
            ),
            wiki_parent=self.ensure_wiki_page(
                WIKI_PARENT_TITLE, WIKI_PARENT_CONTENT, comment_texts=()
            ),
            wiki_child=self.ensure_wiki_page(
                WIKI_CHILD_TITLE,
                WIKI_CHILD_CONTENT,
                comment_texts=WIKI_CHILD_COMMENTS,
                with_attachment=True,
            ),
            project_id=self.get_project_id(),
            wiki_repository_id=self.get_wiki_details()["repositoryId"],
        )

    def get_project_id(self) -> str:
        """The configured project's GUID (assigned by Azure DevOps, not config)."""
        response = requests.get(
            f"{self.org_url}/_apis/projects/{self.project}"
            f"?api-version={WORK_ITEMS_API_VERSION}",
            headers=self.headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()["id"]

    def get_wiki_details(self) -> dict:
        """The configured wiki's metadata, including its underlying git ``repositoryId``."""
        response = requests.get(
            f"{self.wiki_url}?api-version=7.1",
            headers=self.headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()

    # === WORK ITEMS ===

    def find_work_item_id(self, title: str, work_item_type: str = "") -> Optional[int]:
        wiql = build_seed_wiql(self.project, title, work_item_type)
        response = requests.post(
            f"{self.project_url}/_apis/wit/wiql?api-version={WORK_ITEMS_API_VERSION}",
            headers={**self.headers, "Content-Type": "application/json"},
            json={"query": wiql},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        refs = response.json().get("workItems", [])
        if not refs:
            return None
        return min(int(ref["id"]) for ref in refs)

    def get_work_item(self, item_id: int, expand_relations: bool = False) -> dict:
        url = (
            f"{self.org_url}/_apis/wit/workitems/{item_id}"
            f"?api-version={WORK_ITEMS_API_VERSION}"
        )
        if expand_relations:
            url += "&$expand=relations"
        response = requests.get(
            url,
            headers=self.headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()

    def create_work_item(
        self, work_item_type: str, title: str, description: str = ""
    ) -> int:
        operations = [{"op": "add", "path": "/fields/System.Title", "value": title}]
        if description:
            operations.append(
                {
                    "op": "add",
                    "path": "/fields/System.Description",
                    "value": description,
                }
            )
        response = requests.post(
            f"{self.project_url}/_apis/wit/workitems/${quote(work_item_type)}"
            f"?api-version={WORK_ITEMS_API_VERSION}",
            headers={**self.headers, "Content-Type": "application/json-patch+json"},
            json=operations,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return int(response.json()["id"])

    def list_work_item_comments(self, item_id: int) -> list[dict]:
        response = requests.get(
            f"{self.project_url}/_apis/wit/workItems/{item_id}/comments"
            f"?api-version={COMMENTS_API_VERSION}",
            headers=self.headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json().get("comments", [])

    def add_work_item_comment(self, item_id: int, text: str):
        response = requests.post(
            f"{self.project_url}/_apis/wit/workItems/{item_id}/comments"
            f"?api-version={COMMENTS_API_VERSION}",
            headers={**self.headers, "Content-Type": "application/json"},
            json={"text": text},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

    def ensure_work_item(
        self,
        title: str,
        description: str,
        comment_texts: tuple[str, ...],
        with_attachment: bool = False,
    ) -> SeedWorkItem:
        item_id = self.find_work_item_id(title, work_item_type="Task")
        if item_id is None:
            item_id = self.create_work_item("Task", title, description)
            logger.info(f"Created ADO seed work item {item_id} '{title}'")

        item = self.get_work_item(item_id)
        raw_comments = self.list_work_item_comments(item_id)
        existing = {c.get("text") for c in raw_comments}
        for text in comment_texts:
            if text not in existing:
                self.add_work_item_comment(item_id, text)
        if any(text not in existing for text in comment_texts):
            raw_comments = self.list_work_item_comments(item_id)

        fields = item["fields"]
        created_by = fields.get("System.CreatedBy")
        return SeedWorkItem(
            id=item_id,
            title=fields["System.Title"],
            type=fields["System.WorkItemType"],
            # Same read-back approach as _seed_test_plan() for test_case_priority.
            state=fields.get("System.State", "To Do"),
            priority=fields.get("Microsoft.VSTS.Common.Priority", 2),
            reason=fields.get("System.Reason", "Added to backlog"),
            description=fields.get("System.Description", description),
            created_date=fields["System.CreatedDate"],
            url=f"{self.project_url}/_workitems/edit/{item_id}",
            comments=select_seed_comments(raw_comments, comment_texts),
            attachment=self.ensure_work_item_attachment(item_id)
            if with_attachment
            else None,
            created_by=SeedIdentity.from_api(created_by) if created_by else None,
        )

    # === ATTACHMENTS ===

    def upload_attachment(self, file_name: str, content: bytes) -> dict:
        response = requests.post(
            f"{self.project_url}/_apis/wit/attachments"
            f"?fileName={quote(file_name)}&api-version={WORK_ITEMS_API_VERSION}",
            headers={**self.headers, "Content-Type": "application/octet-stream"},
            data=content,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()

    def attach_file_to_work_item(
        self, item_id: int, attachment_url: str, comment: str = ""
    ):
        response = requests.patch(
            f"{self.project_url}/_apis/wit/workitems/{item_id}"
            f"?api-version={WORK_ITEMS_API_VERSION}",
            headers={**self.headers, "Content-Type": "application/json-patch+json"},
            json=[
                {
                    "op": "add",
                    "path": "/relations/-",
                    "value": {
                        "rel": "AttachedFile",
                        "url": attachment_url,
                        "attributes": {"comment": comment},
                    },
                }
            ],
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

    def ensure_work_item_attachment(self, item_id: int) -> SeedAttachment:
        """Find or create the seed attachment on work item ``item_id``.

        A known, plain-text file so GET_WORK_ITEM_ATTACHMENT_CONTENT tests can
        assert its content verbatim instead of depending on a specific
        pre-existing PDF/image and the text/OCR extraction of its content.
        """
        item = self.get_work_item(item_id, expand_relations=True)
        relation = find_attachment_relation(
            item.get("relations", []), ATTACHMENT_FILE_NAME
        )
        if relation is None:
            uploaded = self.upload_attachment(
                ATTACHMENT_FILE_NAME, ATTACHMENT_CONTENT.encode()
            )
            self.attach_file_to_work_item(
                item_id,
                uploaded["url"],
                comment="CodeMie Test Harness seed attachment",
            )
            logger.info(f"Attached seed file to ADO seed work item {item_id}")
            item = self.get_work_item(item_id, expand_relations=True)
            relation = find_attachment_relation(
                item.get("relations", []), ATTACHMENT_FILE_NAME
            )

        return SeedAttachment(
            id=attachment_id_from_url(relation["url"]),
            name=ATTACHMENT_FILE_NAME,
            size=int(
                relation.get("attributes", {}).get(
                    "resourceSize", len(ATTACHMENT_CONTENT.encode())
                )
            ),
            mime_type=ATTACHMENT_MIME_TYPE,
            content=ATTACHMENT_CONTENT,
        )

    def delete_work_item(self, item_id: int):
        """Permanently destroy a work item (used for cleanup of created items)."""
        response = requests.delete(
            f"{self.org_url}/_apis/wit/workitems/{item_id}"
            f"?destroy=true&api-version={WORK_ITEMS_API_VERSION}",
            headers=self.headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

    # === WIKI PAGES ===

    def get_wiki_page(self, path: str, include_content: bool = False) -> Optional[dict]:
        response = requests.get(
            f"{self.wiki_url}/pages?path={quote(path)}"
            f"&includeContent={str(include_content).lower()}"
            "&api-version=7.1",
            headers=self.headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        # The page version lives in the response header, not the JSON body;
        # updating the page later needs it as If-Match.
        page = response.json()
        page["_etag"] = response.headers.get("ETag")
        return page

    def create_wiki_page(self, path: str, content: str, etag: Optional[str] = None):
        """Create a new page, or update an existing one by passing its ``etag``."""
        headers = {**self.headers, "Content-Type": "application/json"}
        if etag:
            headers["If-Match"] = etag
        response = requests.put(
            f"{self.wiki_url}/pages?path={quote(path)}&api-version=7.1",
            headers=headers,
            json={"content": content},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

    def list_wiki_page_comments(self, page_id: int) -> list[dict]:
        response = requests.get(
            f"{self.wiki_url}/pages/{page_id}/comments"
            f"?api-version={WIKI_COMMENTS_API_VERSION}",
            headers=self.headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json().get("comments", [])

    def add_wiki_page_comment(self, page_id: int, text: str):
        response = requests.post(
            f"{self.wiki_url}/pages/{page_id}/comments"
            f"?api-version={WIKI_COMMENTS_API_VERSION}",
            headers={**self.headers, "Content-Type": "application/json"},
            json={"text": text},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

    def ensure_wiki_page(
        self,
        title: str,
        content: str,
        comment_texts: tuple[str, ...],
        with_attachment: bool = False,
    ) -> SeedWikiPage:
        path = f"/{title}"
        page = self.get_wiki_page(path, include_content=True)
        if page is None:
            self.create_wiki_page(path, content)
            page = self.get_wiki_page(path, include_content=True)
            logger.info(f"Created ADO seed wiki page {page['id']} '{path}'")

        page_id = int(page["id"])
        raw_comments = self.list_wiki_page_comments(page_id)
        existing = {c.get("text") for c in raw_comments}
        for text in comment_texts:
            if text not in existing:
                self.add_wiki_page_comment(page_id, text)
        if any(text not in existing for text in comment_texts):
            raw_comments = self.list_wiki_page_comments(page_id)

        return SeedWikiPage(
            id=page_id,
            path=page["path"],
            title=title,
            content=content,
            comments=select_seed_comments(raw_comments, comment_texts),
            attachment=self.ensure_wiki_page_attachment(path, page)
            if with_attachment
            else None,
        )

    # === WIKI ATTACHMENTS ===

    def upload_wiki_attachment(self, file_name: str, content: bytes) -> dict:
        """Upload ``file_name`` as a wiki attachment; tolerate it already existing.

        Despite the ``application/octet-stream`` content type, the ADO wiki
        attachments endpoint rejects a raw byte body ("Invalid length for a
        Base-64 char array or string") and wants it base64-encoded first.

        A duplicate name is also reported as 500 (not 409 as you'd expect),
        wrapping a WikiCreateAttachmentFailedException whose message says
        the path already exists; that case is fine too, since attachments
        can't be overwritten by name anyway.
        """
        response = requests.put(
            f"{self.wiki_url}/attachments?name={quote(file_name)}&api-version=7.1",
            headers={**self.headers, "Content-Type": "application/octet-stream"},
            data=base64.b64encode(content),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code == 409 or (
            response.status_code == 500 and "already exists" in response.text
        ):
            return {"path": f"/.attachments/{file_name}"}
        response.raise_for_status()
        return response.json()

    def ensure_wiki_page_attachment(self, path: str, page: dict) -> SeedAttachment:
        """Find or create the seed attachment and link it from the page at ``path``.

        A known, plain-text file so datasource/search tests can assert on
        content that is stable across runs, instead of depending on a
        specific pre-existing attachment and wiki page id.
        """
        self.upload_wiki_attachment(ATTACHMENT_FILE_NAME, ATTACHMENT_CONTENT.encode())
        page_content = page.get("content", "")
        if ATTACHMENT_FILE_NAME not in page_content:
            updated_content = (
                f"{page_content}\n\n"
                f"[{ATTACHMENT_FILE_NAME}](.attachments/{ATTACHMENT_FILE_NAME})\n"
            )
            self.create_wiki_page(path, updated_content, etag=page.get("_etag"))
            logger.info(f"Linked seed attachment on ADO seed wiki page '{path}'")

        return SeedAttachment(
            id=ATTACHMENT_FILE_NAME,
            name=ATTACHMENT_FILE_NAME,
            size=len(ATTACHMENT_CONTENT.encode()),
            mime_type=ATTACHMENT_MIME_TYPE,
            content=ATTACHMENT_CONTENT,
        )

    # === TEST PLANS ===

    def create_test_plan(self, name: str) -> dict:
        now = datetime.now(timezone.utc)
        response = requests.post(
            f"{self.project_url}/_apis/testplan/plans?api-version=7.1",
            headers={**self.headers, "Content-Type": "application/json"},
            json={
                "name": name,
                "area": {"name": self.project},
                "iteration": self.project,
                "startDate": now.isoformat(),
                "endDate": (now + timedelta(days=365)).isoformat(),
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()

    def create_suite(self, plan_id: int, parent_suite_id: int, name: str) -> dict:
        response = requests.post(
            f"{self.project_url}/_apis/testplan/Plans/{plan_id}/suites?api-version=7.1",
            headers={**self.headers, "Content-Type": "application/json"},
            json={
                "name": name,
                "suiteType": "StaticTestSuite",
                "parentSuite": {"id": parent_suite_id},
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()

    def add_test_case_to_suite(self, plan_id: int, suite_id: int, test_case_id: int):
        response = requests.post(
            f"{self.project_url}/_apis/test/Plans/{plan_id}/suites/{suite_id}"
            f"/testcases/{test_case_id}?api-version=7.1",
            headers=self.headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

    def ensure_test_plan(self) -> SeedTestPlan:
        """Use an existing plan that already has a suite with a test case.

        Creating plans, suites and test cases needs test-management write
        access, which not every token has. Reading does not, so the seed
        plan is preferred, then any other plan that is already usable, and
        only if none exists is a new plan created.
        """
        plans = self.list_test_plans()
        plans.sort(key=lambda plan: plan["name"] != TEST_PLAN_NAME)
        for plan in plans:
            located = self._find_suite_with_test_case(plan)
            if located is not None:
                return self._seed_test_plan(plan, *located)

        plan = next((p for p in plans if p["name"] == TEST_PLAN_NAME), None)
        if plan is None:
            plan = self.create_test_plan(TEST_PLAN_NAME)
            logger.info(f"Created ADO seed test plan {plan['id']}")
        root_suite = plan["rootSuite"]
        suite = self.create_suite(
            int(plan["id"]), int(root_suite["id"]), TEST_SUITE_NAME
        )
        test_case_id = self.create_work_item(
            "Test Case", TEST_CASE_TITLE, TEST_CASE_DESCRIPTION
        )
        self.add_test_case_to_suite(int(plan["id"]), int(suite["id"]), test_case_id)
        return self._seed_test_plan(plan, suite, test_case_id)

    def list_test_plans(self) -> list[dict]:
        response = requests.get(
            f"{self.project_url}/_apis/testplan/plans?api-version=7.1",
            headers=self.headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json().get("value", [])

    def get_test_plan(self, plan_id: int) -> dict:
        """Single-plan GET. Unlike ``list_test_plans``, this includes ``owner``/``updatedBy``."""
        response = requests.get(
            f"{self.project_url}/_apis/testplan/plans/{plan_id}?api-version=7.1",
            headers=self.headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()

    def _find_suite_with_test_case(self, plan: dict) -> Optional[tuple[dict, int]]:
        """First child suite of ``plan`` that holds a test case, with that case's id."""
        plan_id = int(plan["id"])
        root_id = int(plan["rootSuite"]["id"])
        response = requests.get(
            f"{self.project_url}/_apis/testplan/Plans/{plan_id}/suites?api-version=7.1",
            headers=self.headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        for suite in response.json().get("value", []):
            if int(suite["id"]) == root_id:
                continue
            cases = self._suite_test_case_ids(plan_id, int(suite["id"]))
            if cases:
                return suite, min(cases)
        return None

    def _suite_test_case_ids(self, plan_id: int, suite_id: int) -> set[int]:
        response = requests.get(
            f"{self.project_url}/_apis/test/Plans/{plan_id}/suites/{suite_id}"
            "/testcases?api-version=7.1",
            headers=self.headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        ids = set()
        for entry in response.json().get("value", []):
            test_case = entry.get("testCase") or entry.get("workItem") or {}
            if test_case.get("id") is not None:
                ids.add(int(test_case["id"]))
        return ids

    def _seed_test_plan(
        self, plan: dict, suite: dict, test_case_id: int
    ) -> SeedTestPlan:
        fields = self.get_work_item(test_case_id)["fields"]
        root_suite = plan["rootSuite"]
        # list_test_plans() omits owner/updatedBy; the single-plan GET has them.
        plan_details = self.get_test_plan(int(plan["id"]))
        owner = plan_details.get("owner")
        updated_by = plan_details.get("updatedBy")
        return SeedTestPlan(
            id=int(plan["id"]),
            name=plan["name"],
            start_date=plan.get("startDate", ""),
            end_date=plan.get("endDate", ""),
            updated_date=plan.get("updatedDate", ""),
            root_suite_id=int(root_suite["id"]),
            root_suite_name=root_suite["name"],
            suite_id=int(suite["id"]),
            suite_name=suite["name"],
            test_case_id=test_case_id,
            test_case_title=fields["System.Title"],
            test_case_description=fields.get("System.Description", ""),
            test_case_priority=fields.get("Microsoft.VSTS.Common.Priority", 2),
            test_case_automation_status=fields.get(
                "Microsoft.VSTS.TCM.AutomationStatus", "Not Automated"
            ),
            project_id=self.get_project_id(),
            owner=SeedIdentity.from_api(owner) if owner else None,
            updated_by=SeedIdentity.from_api(updated_by) if updated_by else None,
        )
