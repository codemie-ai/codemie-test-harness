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

"""Helpers for tests of skill bundle files in the conversation workspace."""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from typing import Iterable

from codemie_test_harness.tests.test_data.skill_workspace_test_data import (
    SEED_PROMPT,
    SKILL_FOLDER_ID_LENGTH,
    SKILL_FOLDER_PREFIX,
    BundleFile,
)
from codemie_test_harness.tests.utils.workspace_script_utils import build_file_token


def skill_folder(skill) -> str:
    """The workspace folder that holds a skill's files: ``skills/<name>-<first 8 chars of id>``."""
    return f"{SKILL_FOLDER_PREFIX}{skill.name}-{skill.id[:SKILL_FOLDER_ID_LENGTH]}"


def folder_paths(skill, bundle: Iterable[BundleFile]) -> list[str]:
    """Workspace paths the files of ``bundle`` take once ``skill`` is placed in a workspace."""
    folder = skill_folder(skill)
    return [f"{folder}/{bundle_file.path}" for bundle_file in bundle]


def list_paths(client, workspace_id: str) -> list[str]:
    """Paths of every file currently listed in the workspace."""
    return [item.path for item in client.workspaces.list_files(workspace_id)]


def skill_blob_token(skill_id: str, path: str, content: str) -> str:
    """File reference of a skill's stored file, as the backend encodes it.

    The stored file lives under the owner ``skill-<skill id>`` with a content-addressed name
    ``<first 32 hex chars of the content's sha-256>/<path>``.
    """
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return build_file_token("text/plain", f"skill-{skill_id}", f"{digest[:32]}/{path}")


def send_message(assistant_utils, assistant, conversation_id: str) -> str:
    """Send one message in the conversation; the skill files are placed before the assistant answers."""
    return assistant_utils.ask_assistant(
        assistant, SEED_PROMPT, conversation_id=conversation_id
    )


def send_messages_in_parallel(
    assistant_utils, assistant, conversation_id: str, count: int
) -> list[str]:
    """Send ``count`` messages at the same moment in one conversation and return the replies."""
    with ThreadPoolExecutor(max_workers=count) as pool:
        futures = [
            pool.submit(send_message, assistant_utils, assistant, conversation_id)
            for _ in range(count)
        ]
        return [future.result() for future in futures]
