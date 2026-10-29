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

"""The one POST of the CLI Analytics ingest helpers.

Kept at the package root on purpose, like otlp_builder.py: importing it must not import
codemie_test_harness.tests (its __init__ loads the .env file).
"""

import requests

PROJECT_HEADER = "X-CodeMie-Project"


def post_ingest(
    url: str,
    body: bytes,
    headers: dict,
    project: str | None,
    verify_ssl: bool,
    timeout: float,
    *,
    allow_redirects: bool = True,
) -> requests.Response:
    """POST `body`; `project` (None sends no header) goes into X-CodeMie-Project as given,
    an empty string included."""
    headers = dict(headers)
    if project is not None:
        headers[PROJECT_HEADER] = project
    return requests.post(
        url,
        headers=headers,
        data=body,
        verify=verify_ssl,
        timeout=timeout,
        allow_redirects=allow_redirects,
    )
