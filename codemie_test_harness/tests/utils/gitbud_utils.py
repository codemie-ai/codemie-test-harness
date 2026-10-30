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

import time
from time import sleep
from typing import Optional

import gitlab
from gitlab.exceptions import GitlabError
import logging
from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager
from codemie_test_harness.tests.utils.gitlab_seed import (
    SEED_BRANCH_NAMES,
    SEED_DESCRIPTION,
    SEED_FILE_CONTENT,
    SEED_FILE_NAME,
    SEED_SOURCE_BRANCH,
    SEED_TARGET_BRANCH,
    SEED_TITLE,
    SeedBranches,
    SeedImageUpload,
    SeedMergeRequest,
    find_seed_merge_request,
    parse_upload_url,
)

logger = logging.getLogger(__name__)

files_path = "src/main/java/testDirectory/"

SEED_SEARCH_TIMEOUT_SECONDS = 60
SEED_SEARCH_POLL_SECONDS = 3


class GitBudUtils:
    """Utility class for Git operations using GitLab API"""

    def __init__(
        self,
        url: str = CredentialsManager.get_parameter("GITLAB_URL"),
        token: str = CredentialsManager.get_parameter("GITLAB_TOKEN"),
        project_id: str = CredentialsManager.get_parameter("GITLAB_PROJECT_ID"),
    ):
        """
        Initialize GitBudUtils with GitLab credentials
        Args:
            url: GitLab instance URL
            token: GitLab personal access token
            project_id: GitLab project ID or 'namespace/project-name'
        """
        try:
            self.gl = gitlab.Gitlab(url=url, private_token=token)
            self.project = self.gl.projects.get(project_id)
        except GitlabError as e:
            logger.error(f"Failed to initialize GitLab project {project_id}: {str(e)}")
            raise

    def branch_exists(self, branch_name: str) -> bool:
        """
        Check if a remote branch exists in the repository
        Args:
            branch_name: Name of the branch to check
        Returns:
            True if remote branch exists, False otherwise
        """
        if not branch_name:
            return False

        try:
            self.project.branches.get(branch_name)
            return True
        except GitlabError:
            return False

    def delete_branch(self, branch_name: str) -> None:
        """
        Delete a remote git branch
        Args:
            branch_name: Name of the branch to delete
        Raises:
            GitlabError: If branch deletion fails
            ValueError: If branch name is invalid or branch doesn't exist
        """
        if not branch_name:
            raise ValueError("Branch name cannot be empty")

        try:
            branch = self.project.branches.get(branch_name)
            branch.delete()
            logger.info(f"Successfully deleted remote branch: {branch_name}")
        except GitlabError as e:
            if "404" in str(e):
                raise ValueError(f"Remote branch '{branch_name}' does not exist")
            logger.error(f"Failed to delete remote branch {branch_name}: {str(e)}")
            raise

    def create_file(
        self,
        file_name: str,
        branch: str = "main",
        file_content: str = "",
        commit_message: str = "Create file",
    ) -> None:
        """
        Create a new file in the repository
        Args:
            file_name: Name of the file to create in the repository
            branch: Branch name (defaults to 'main')
            file_content: Content to write to the file (defaults to empty string)
            commit_message: Commit message for the creation (defaults to 'Create file')
        Raises:
            GitlabError: If file creation fails
            ValueError: If file name is invalid or file already exists
        """
        if not file_name:
            raise ValueError("File name cannot be empty")

        full_path = files_path + file_name

        try:
            self.project.files.get(file_path=full_path, ref=branch)
            raise ValueError(f"File '{full_path}' already exists in branch {branch}")
        except GitlabError as e:
            # 404 means file doesn't exist, which is what we want
            if "404" not in str(e):
                raise

        # Create the file
        for index in range(1, 5):
            try:
                self.project.files.create(
                    {
                        "file_path": full_path,
                        "branch": branch,
                        "content": file_content,
                        "commit_message": commit_message,
                    }
                )
                logger.info(
                    f"Successfully created file: {full_path} in branch {branch}"
                )
                return
            except GitlabError as e:
                logger.error(
                    f"Failed to create file {full_path} from {index} attempt: {str(e)}"
                )
                if index == 5:
                    raise
                sleep(1)

    def get_file_content(self, file_name: str, branch: str = "main") -> str:
        """
        Get content of a file from the repository
        Args:
            file_name: Name to the file in the repository
            branch: Branch name (defaults to 'main')
        Returns:
            File content as string
        Raises:
            GitlabError: If file retrieval fails
        """
        try:
            file_content = self.project.files.get(
                file_path=files_path + file_name, ref=branch
            )
            return file_content.decode().decode("utf-8")
        except GitlabError as e:
            if "404" in str(e):
                raise ValueError(
                    f"File '{files_path}{file_name}' does not exist in branch {branch}"
                )
            logger.error(
                f"Failed to get file {files_path}{file_name} content: {str(e)}"
            )
            raise

    def file_exists(self, file_name: str, branch: str = "main") -> bool:
        """
        Check if a file exists in the repository
        Args:
            file_name: Name to the file in the repository
            branch: Branch name (defaults to 'main')
        Returns:
            True if file exists, False otherwise
        """
        try:
            return (
                self.project.files.get(file_path=files_path + file_name, ref=branch)
                is not None
            )
        except GitlabError:
            return False

    def delete_file(
        self, file_name: str, branch: str = "main", commit_message: str = "Delete file"
    ) -> None:
        """
        Delete a file from the repository
        Args:
            file_name: Name to the file in the repository
            branch: Branch name (defaults to 'main')
            commit_message: Commit message for the deletion
        Raises:
            GitlabError: If file deletion fails
            ValueError: If file path is invalid or file doesn't exist
        """
        if not file_name:
            raise ValueError("File path cannot be empty")

        try:
            file = self.project.files.get(file_path=files_path + file_name, ref=branch)
            file.delete(branch=branch, commit_message=commit_message)
            logger.info(
                f"Successfully deleted file: {files_path}{file_name} from branch {branch}"
            )
        except GitlabError:
            pass

    def upload_image(self, filename: str, data: bytes) -> SeedImageUpload:
        """
        Upload a file to the project through the GitLab uploads API
        Args:
            filename: Name the file is served under (its extension is what the GitLab tool sees)
            data: Raw file bytes
        Returns:
            SeedImageUpload addressing the file through /api/v4/projects/:id/uploads
        Raises:
            GitlabUploadError: If the upload fails
            ValueError: If GitLab answers with an unexpected upload url
        """
        uploaded = self.project.upload(filename, filedata=data)
        secret, stored_name = parse_upload_url(uploaded["url"])
        logger.info(
            f"Uploaded {stored_name} ({len(data)} bytes) to project {self.project.id}"
        )
        return SeedImageUpload(
            project_id=self.project.id,
            secret=secret,
            filename=stored_name,
            size=len(data),
        )

    def get_merge_request_id_by_title(self, mr_title: str) -> int:
        """
        Get the merge request ID by its title.

        Args:
            mr_title (str): The title of the merge request to search for

        Returns:
            int: The ID of the merge request if found

        Raises:
            ValueError: If no merge request is found with the given title or if multiple merge requests are found
            GitlabError: If there's an error accessing the GitLab API
        """
        try:
            merge_requests = self.project.mergerequests.list(search=mr_title)

            exact_matches = [mr for mr in merge_requests if mr.title == mr_title]

            if not exact_matches:
                raise ValueError(f"No merge request found with title: {mr_title}")

            if len(exact_matches) > 1:
                raise ValueError(
                    f"Multiple merge requests found with title: {mr_title}"
                )

            return exact_matches[0].iid

        except GitlabError as e:
            logger.error(
                f"Failed to get merge request ID for title {mr_title}: {str(e)}"
            )
            raise

    def find_seed_merge_request(self) -> Optional[dict]:
        merge_requests = self.project.mergerequests.list(search=SEED_TITLE)
        return find_seed_merge_request([mr.attributes for mr in merge_requests])

    def _ensure_seed_branch_and_file(self) -> None:
        """Create the seed branch (from the target branch) and its file if missing."""
        if not self.branch_exists(SEED_SOURCE_BRANCH):
            self.project.branches.create(
                {"branch": SEED_SOURCE_BRANCH, "ref": SEED_TARGET_BRANCH}
            )
        if not self.file_exists(SEED_FILE_NAME, branch=SEED_SOURCE_BRANCH):
            self.create_file(
                SEED_FILE_NAME,
                branch=SEED_SOURCE_BRANCH,
                file_content=SEED_FILE_CONTENT,
                commit_message="Add codemie-test-harness seed file",
            )

    def _create_seed_merge_request(self) -> dict:
        self._ensure_seed_branch_and_file()
        mr = self.project.mergerequests.create(
            {
                "source_branch": SEED_SOURCE_BRANCH,
                "target_branch": SEED_TARGET_BRANCH,
                "title": SEED_TITLE,
                "description": SEED_DESCRIPTION,
                "labels": "created-by-agent",
            }
        )
        logger.info(f"Created GitLab seed MR !{mr.iid} in project {self.project.id}")
        # A just-created MR may not be immediately searchable.
        deadline = time.monotonic() + SEED_SEARCH_TIMEOUT_SECONDS
        while self.find_seed_merge_request() is None:
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"GitLab seed MR !{mr.iid} not searchable after "
                    f"{SEED_SEARCH_TIMEOUT_SECONDS}s"
                )
            time.sleep(SEED_SEARCH_POLL_SECONDS)
        return mr.attributes

    def _ensure_seed_branches(self) -> None:
        """Create the persistent marker branches (off the target branch) if missing."""
        for branch_name in SEED_BRANCH_NAMES:
            if not self.branch_exists(branch_name):
                self.project.branches.create(
                    {"branch": branch_name, "ref": SEED_TARGET_BRANCH}
                )

    def ensure_seed_branches(self) -> SeedBranches:
        """Find or create the persistent marker branches.

        Returns the target branch plus the marker branches, oldest/target first,
        so branch-listing test data can rely on a known, seeded set of names
        instead of pre-existing branches no seed created.
        """
        self._ensure_seed_branches()
        return SeedBranches(names=[SEED_TARGET_BRANCH, *SEED_BRANCH_NAMES])

    def ensure_seed_merge_request(self) -> SeedMergeRequest:
        """Find or create the seed merge request."""
        mr = self.find_seed_merge_request() or self._create_seed_merge_request()
        # Fetch the single MR to get diff_refs, which the list/create payloads omit.
        detailed = self.project.mergerequests.get(mr["iid"]).attributes
        diff_refs = detailed.get("diff_refs") or {}
        author = detailed.get("author") or {}
        return SeedMergeRequest(
            iid=detailed["iid"],
            project_id=detailed["project_id"],
            title=detailed["title"],
            description=detailed["description"],
            source_branch=detailed["source_branch"],
            target_branch=detailed["target_branch"],
            state=detailed["state"],
            author=author.get("name", ""),
            author_web_url=author.get("web_url", ""),
            web_url=detailed["web_url"],
            created_at=detailed["created_at"],
            updated_at=detailed["updated_at"],
            sha=detailed.get("sha") or "",
            base_sha=diff_refs.get("base_sha", ""),
            start_sha=diff_refs.get("start_sha", ""),
            head_sha=diff_refs.get("head_sha", ""),
            file_path=f"{files_path}{SEED_FILE_NAME}",
        )
