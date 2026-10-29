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

from dataclasses import dataclass


@dataclass
class MultipagePdfDatasourceData:
    file_name: str
    page_two_query: str
    page_two_expected_fragment: str

    @staticmethod
    def default() -> "MultipagePdfDatasourceData":
        return MultipagePdfDatasourceData(
            file_name="test_multipage.pdf",
            page_two_query="What is the unique content on page two of the document?",
            page_two_expected_fragment="MULTIPAGE_MARKER_P2",
        )
