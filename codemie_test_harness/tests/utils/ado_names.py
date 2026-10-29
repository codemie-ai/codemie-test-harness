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

"""Azure DevOps project, wiki and organization names for test text.

The names come from the configured integration
(/codemie/autotests/integrations/azuredevops, or the matching env vars), never
from literals in test data. Test data writes the placeholders ``<ADO_PROJECT>``,
``<ADO_WIKI>`` and ``<ADO_ORG>``; ``ado_text`` swaps them in.

``ado_text`` uses plain ``.replace`` rather than an f-string, so templates that
are filled in later with ``.format(...)`` keep their ``{}`` placeholders intact.
"""

from codemie_test_harness.tests.utils.credentials_manager import CredentialsManager

ADO_URL = CredentialsManager.get_parameter("AZURE_DEVOPS_URL")
ADO_PROJECT_NAME = CredentialsManager.get_parameter("AZURE_DEVOPS_PROJECT_NAME")
ADO_WIKI_NAME = CredentialsManager.get_parameter("AZURE_DEVOPS_WIKI_NAME")
ADO_ORGANIZATION_NAME = CredentialsManager.get_parameter(
    "AZURE_DEVOPS_ORGANIZATION_NAME"
)


def ado_text(text: str) -> str:
    """Replace the ``<ADO_*>`` placeholders in ``text`` with configured values."""
    return (
        text.replace("<ADO_URL>", ADO_URL)
        .replace("<ADO_WIKI>", ADO_WIKI_NAME)
        .replace("<ADO_PROJECT>", ADO_PROJECT_NAME)
        .replace("<ADO_ORG>", ADO_ORGANIZATION_NAME)
    )
