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

import pytest

from codemie_test_harness.tests.enums.tools import Default
from codemie_test_harness.tests.test_data.multipage_pdf_test_data import (
    MultipagePdfDatasourceData,
)
from codemie_test_harness.tests.utils.base_utils import (
    assert_tool_triggered,
    get_random_name,
)
from codemie_test_harness.tests.utils.constants import FILES_PATH


@pytest.mark.datasource
@pytest.mark.file
@pytest.mark.api
def test_indexes_all_pages_of_multipage_pdf_via_file_datasource(
    assistant,
    assistant_utils,
    datasource_utils,
    similarity_check,
    kb_context,
):
    """Regression guard for multi-page PDF indexed via File
    datasource must make content from every page reachable through the KB.

    The fix in base_datasource_processor.py (monotonically-increasing chunk_num
    per source) and rrf.py (dedup by (source, chunk_num)) applies to all
    processor subclasses including File.  This test exercises that code path
    without requiring a live SharePoint connection.

    Scenario:
      - Upload test_multipage.pdf (page 1 + page 2 with a unique marker).
      - Attach the datasource as KB context to an assistant.
      - Ask the assistant for content that exists only on page 2.
      - Assert search_kb was triggered and the response contains the marker.
    """
    test_data = MultipagePdfDatasourceData.default()

    datasource = datasource_utils.create_file_datasource(
        name=get_random_name(),
        description="[Autotest] multi-page PDF all-pages regression",
        files=[str(FILES_PATH / test_data.file_name)],
    )

    test_assistant = assistant(context=kb_context(datasource))

    response, triggered_tools = assistant_utils.ask_assistant(
        test_assistant,
        test_data.page_two_query,
        minimal_response=False,
    )

    assert_tool_triggered(Default.SEARCH_KB, triggered_tools)

    similarity_check.check_similarity(
        response,
        test_data.page_two_expected_fragment,
        assistant_name=test_assistant.name,
    )
