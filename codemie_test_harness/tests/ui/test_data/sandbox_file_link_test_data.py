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

"""Test data for sandbox file links and file names in the chat UI.

A sandbox link is `sandbox:/v1/files/<token>`; the token is the base64 of a
length-prefixed `mime~owner~name` triple that the back end issues. The front end shows a
chip or a decoded name only for a token it can decode strictly.
"""

import base64
from dataclasses import dataclass

from codemie_test_harness.tests.utils.base_utils import get_random_name

SANDBOX_LINK_PREFIX = "sandbox:/v1/files/"


def serialize_token(*parts: str) -> str:
    """Build a file token the way the back end's StringSerializer does: each part as
    `<length>~<part>`, joined, then standard base64 with padding."""
    raw = "".join(f"{len(part)}~{part}" for part in parts)
    return base64.b64encode(raw.encode("utf-8")).decode("utf-8")


# Encoded exactly like an issued token (same serializer, padded standard base64, length a
# multiple of 4, valid UTF-8, token alphabet) but holding one part instead of the three
# `mime`, `owner`, `name`. The only thing wrong with it is its part count, so the front
# end's strict decoder must refuse it for that reason.
INVENTED_ARTIFACT_TOKEN = serialize_token("invented-file.txt")

FILE_BODY = "alpha\nbeta"


@dataclass(frozen=True)
class InventedSandboxLink:
    """A reply carrying a sandbox link whose token no back end issued."""

    label: str
    link: str

    @property
    def reply(self) -> str:
        return f"Here is the file: [{self.label}]({self.link})"


def build_invented_sandbox_link() -> InventedSandboxLink:
    return InventedSandboxLink(
        label=get_random_name(),
        link=f"{SANDBOX_LINK_PREFIX}{INVENTED_ARTIFACT_TOKEN}",
    )


def build_mention_file_names(non_latin_stem: str) -> tuple:
    """Names of two files to upload: one ASCII, one carrying `non_latin_stem`."""
    return (
        f"{get_random_name()}.txt",
        f"{get_random_name()}-{non_latin_stem}.txt",
    )
