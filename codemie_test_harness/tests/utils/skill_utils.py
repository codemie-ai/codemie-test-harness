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

"""Utility functions for Skills operations in tests."""

import base64
from typing import List, Optional

from codemie_sdk.models.skill import (
    SkillCompanionFilePayload,
    SkillCreateRequest,
    SkillEventItem,
    SkillEventRequest,
    SkillImportRequest,
    SkillStatsItem,
    SkillUpdateRequest,
    SkillVisibility,
    SingleSkillStatsResponse,
)

from codemie_test_harness.tests import PROJECT
from codemie_test_harness.tests.test_data.skill_test_data import (
    SKILL_CONTENT,
    SKILL_DESCRIPTION,
)
from codemie_test_harness.tests.utils.base_utils import (
    BaseUtils,
    get_random_name,
    wait_for_entity,
)


class SkillsUtils(BaseUtils):
    """Utility class for Skills operations in tests."""

    def send_create_skill_request(
        self,
        skill_name: Optional[str] = None,
        description: Optional[str] = None,
        content: Optional[str] = None,
        project_name: Optional[str] = None,
        visibility: SkillVisibility = SkillVisibility.PROJECT,
        categories: Optional[List[str]] = None,
        enabled_builtin_subagents: Optional[List[str]] = None,
    ):
        """Send create skill request.

        Args:
            skill_name: Skill name (auto-generated if not provided)
            description: Skill description (default: SKILL_DESCRIPTION from test_data)
            content: Skill markdown content (default: VALID_CONTENT from test_data)
            project_name: Project name
            visibility: Skill visibility setting
            categories: List of category IDs

        Returns:
            Tuple of (created skill response, skill name)
        """
        # Skill names must be kebab-case (lowercase letters, numbers, and hyphens only)
        skill_name = skill_name or get_random_name().replace("_", "-")
        description = description or SKILL_DESCRIPTION
        content = content or SKILL_CONTENT

        request = SkillCreateRequest(
            name=skill_name,
            description=description,
            content=content,
            project=project_name or PROJECT,
            visibility=visibility,
            categories=categories or [],
            enabled_builtin_subagents=enabled_builtin_subagents,
        )

        response = self.client.skills.create(request)
        return response, skill_name

    def create_skill(
        self,
        skill_name: Optional[str] = None,
        description: Optional[str] = None,
        content: Optional[str] = None,
        project_name: Optional[str] = None,
        visibility: SkillVisibility = SkillVisibility.PROJECT,
        categories: Optional[List[str]] = None,
        enabled_builtin_subagents: Optional[List[str]] = None,
    ):
        """Create a skill and wait for it to be available.

        Args:
            skill_name: Skill name (auto-generated if not provided)
            description: Skill description (default: SKILL_DESCRIPTION from test_data)
            content: Skill markdown content (default: VALID_CONTENT from test_data)
            project_name: Project name
            visibility: Skill visibility setting
            categories: List of category IDs

        Returns:
            Created skill object with full details (including content)
        """
        response, name = self.send_create_skill_request(
            skill_name=skill_name,
            description=description,
            content=content,
            project_name=project_name,
            visibility=visibility,
            categories=categories,
            enabled_builtin_subagents=enabled_builtin_subagents,
        )

        # Wait for the skill to appear in the list
        skill_from_list = wait_for_entity(
            lambda: self.client.skills.list(per_page=20).skills,
            entity_name=name,
        )

        # Fetch full skill details (including content field)
        return self.client.skills.get(skill_from_list.id)

    def create_skill_with_files(
        self,
        files: List[SkillCompanionFilePayload],
        skill_name: Optional[str] = None,
        visibility: SkillVisibility = SkillVisibility.PROJECT,
    ):
        """Create a skill that carries a bundle of companion files.

        Args:
            files: Bundle files to store with the skill
            skill_name: Kebab-case name (auto-generated if not provided)
            visibility: Skill visibility setting

        Returns:
            The create response (id, name, companion_files metadata, bundle_warning)
        """
        request = SkillCreateRequest(
            name=skill_name or get_random_name().replace("_", "-"),
            description=SKILL_DESCRIPTION,
            content=SKILL_CONTENT,
            project=PROJECT,
            visibility=visibility,
            companion_files=files,
        )
        return self.client.skills.create(request)

    def replace_skill_files(
        self, skill_id: str, files: List[SkillCompanionFilePayload]
    ):
        """Replace the whole companion file set of a skill; unchanged files keep their stored version."""
        return self.client.skills.update(
            skill_id, SkillUpdateRequest(companion_files=files)
        )

    def import_skill(
        self,
        file_content: str,
        filename: str,
        project_name: Optional[str] = None,
        visibility: SkillVisibility = SkillVisibility.PROJECT,
    ):
        """Import a skill from markdown file content.

        Args:
            file_content: Markdown file content (will be base64-encoded)
            filename: Name of the file
            project_name: Project name
            visibility: Skill visibility setting

        Returns:
            Imported skill object with full details (including content)
        """
        # Base64-encode the file content as required by the API
        encoded_content = base64.b64encode(file_content.encode("utf-8")).decode("ascii")

        request = SkillImportRequest(
            file_content=encoded_content,
            filename=filename,
            project=project_name or PROJECT,
            visibility=visibility,
        )

        response = self.client.skills.import_skill(request)

        # Wait for the skill to appear in the list
        skill_from_list = wait_for_entity(
            lambda: self.client.skills.list(per_page=100).skills,
            entity_name=response.name,
        )

        # Fetch full skill details (including content field)
        return self.client.skills.get(skill_from_list.id)

    def update_skill(
        self,
        skill_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        content: Optional[str] = None,
        visibility: Optional[SkillVisibility] = None,
        categories: Optional[List[str]] = None,
        enabled_builtin_subagents: Optional[List[str]] = None,
    ):
        """Update an existing skill.

        Args:
            skill_id: Skill identifier
            name: New skill name
            description: New description
            content: New markdown content
            visibility: New visibility setting
            categories: New category IDs

        Returns:
            Updated skill object
        """
        request = SkillUpdateRequest(
            name=name,
            description=description,
            content=content,
            visibility=visibility,
            categories=categories,
            enabled_builtin_subagents=enabled_builtin_subagents,
        )

        response = self.client.skills.update(skill_id, request)

        # Wait for the skill to be updated in the list
        skill_from_list = wait_for_entity(
            lambda: self.client.skills.list(per_page=100).skills,
            entity_name=response.name,
        )

        # Fetch full skill details (including content field)
        return self.client.skills.get(skill_from_list.id)

    def get_skill_by_id(self, skill_id: str):
        """Get skill by ID.

        Args:
            skill_id: Skill identifier

        Returns:
            Skill object
        """
        return self.client.skills.get(skill_id)

    def get_skill_by_name(self, skill_name: str):
        """Get skill by name.

        Args:
            skill_name: Skill name

        Returns:
            Skill object or None if not found
        """
        skills = self.client.skills.list(per_page=100).skills
        return next((s for s in skills if s.name == skill_name), None)

    def delete_skill(self, skill):
        """Delete a skill.

        Args:
            skill: Skill object or dict with 'id' field

        Returns:
            Deletion response
        """
        skill_id = skill.id if hasattr(skill, "id") else skill["id"]
        return self.client.skills.delete(skill_id)

    def delete_skill_by_id(self, skill_id: str):
        return self.client.skills.delete(skill_id)

    def attach_skill_to_assistant(self, assistant_id: str, skill_id: str):
        """Attach skill to assistant.

        Args:
            assistant_id: Assistant identifier
            skill_id: Skill identifier

        Returns:
            Attachment response
        """
        return self.client.skills.attach_to_assistant(assistant_id, skill_id)

    def detach_skill_from_assistant(self, assistant_id: str, skill_id: str):
        """Detach skill from assistant.

        Args:
            assistant_id: Assistant identifier
            skill_id: Skill identifier

        Returns:
            Detachment response
        """
        return self.client.skills.detach_from_assistant(assistant_id, skill_id)

    def bulk_attach_skill(self, skill_id: str, assistant_ids: List[str]):
        """Bulk attach skill to multiple assistants.

        Args:
            skill_id: Skill identifier
            assistant_ids: List of assistant identifiers

        Returns:
            Bulk attachment response
        """
        return self.client.skills.bulk_attach_to_assistants(skill_id, assistant_ids)

    def get_assistant_skills(self, assistant_id: str):
        """Get all skills attached to assistant.

        Args:
            assistant_id: Assistant identifier

        Returns:
            List of skills
        """
        return self.client.skills.get_assistant_skills(assistant_id)

    def get_skill_assistants(self, skill_id: str):
        """Get all assistants using this skill.

        Args:
            skill_id: Skill identifier

        Returns:
            List of assistants
        """
        return self.client.skills.get_skill_assistants(skill_id)

    def publish_skill(self, skill_id: str, categories: Optional[List[str]] = None):
        """Publish skill to marketplace.

        Args:
            skill_id: Skill identifier
            categories: Optional list of category IDs

        Returns:
            Publication response
        """
        return self.client.skills.publish(skill_id, categories)

    def unpublish_skill(self, skill_id: str):
        """Unpublish skill from marketplace.

        Args:
            skill_id: Skill identifier

        Returns:
            Unpublication response
        """
        return self.client.skills.unpublish(skill_id)

    def export_skill(self, skill_id: str):
        """Export skill.

        Args:
            skill_id: Skill identifier

        Returns:
            Exported skill data
        """
        return self.client.skills.export(skill_id)

    def list_categories(self):
        """List available skill categories.

        Returns:
            List of categories
        """
        return self.client.skills.list_categories()

    def record_event(self, request: SkillEventRequest) -> dict:
        return self.client.skills.record_event(request)

    def get_events(
        self, from_=None, to=None, limit=100, offset=0
    ) -> list[SkillEventItem]:
        return self.client.skills.get_events(
            from_=from_, to=to, limit=limit, offset=offset
        )

    def get_events_stats(
        self, from_=None, to=None, limit=100, offset=0
    ) -> list[SkillStatsItem]:
        return self.client.skills.get_events_stats(
            from_=from_, to=to, limit=limit, offset=offset
        )

    def get_skill_stats(self, slug: str) -> SingleSkillStatsResponse:
        return self.client.skills.get_skill_stats(slug)

    def find_event(self, events: list, slug: str, command: str | None = None):
        return next(
            (
                e
                for e in events
                if e.skill_slug == slug and (command is None or e.command == command)
            ),
            None,
        )

    def find_in_events_stats(self, stats: list, slug: str):
        return next((item for item in stats if item.skill_slug == slug), None)

    def generate_instructions(self, description: str, skill_name: str | None = None):
        return self.client.skills.generate_instructions(
            description=description, skill_name=skill_name
        )
