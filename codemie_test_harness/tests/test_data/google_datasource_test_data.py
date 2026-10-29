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

"""Test data constants for Google Datasource tests"""

from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

GOOGLE_DOC_GUIDE_URL = "https://docs.codemie.ai/user-guide/data-source/datasources-types/add-google-data-source/"
USER_PROMPT = 'Tell context of the What is "Platform A"? section?'

RESPONSE_FOR_GOOGLE_DOC = """
    The context for the "What is 'Platform A'?" section is as follows:
    - The heading for the title must be at level 3.
    - The title number must follow the format (x.x.x.).
    - The section content is just a paragraph.
"""


def get_google_doc_url() -> str:
    """Google Doc URL used by the Google Docs datasource tests.

    Read from the GOOGLE_DOC_URL environment variable (or, as a fallback, the
    AWS Parameter Store parameter /codemie/autotests/integrations/google_docs,
    path "document_url") instead of a hardcoded constant, so the target test
    document can change without a code change. RESPONSE_FOR_GOOGLE_DOC still
    asserts against that document's content, so update it too if you point
    this at a different document.

    Raises a clear error instead of silently falling back to a stale
    hardcoded URL when the value is not configured.
    """
    url = CredentialsManager.get_parameter("GOOGLE_DOC_URL")
    if not url:
        raise ValueError(
            "GOOGLE_DOC_URL is not configured. Set the GOOGLE_DOC_URL "
            "environment variable, or set 'document_url' in the AWS "
            "Parameter Store parameter /codemie/autotests/integrations/google_docs."
        )
    return url
