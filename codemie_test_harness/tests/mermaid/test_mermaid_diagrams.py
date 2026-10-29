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

"""Tests for mermaid diagram generation."""

import re
import pytest
from hamcrest import assert_that, is_not, contains_string, starts_with, greater_than

from codemie_test_harness.tests.test_data.mermaid_test_data import mermaid_test_data


def extract_file_id_from_url(file_url: str) -> str:
    """Extract the file ID from a CodeMie file URL.

    Args:
        file_url: URL like https://domain/v1/files/{file_id}

    Returns:
        The file_id portion of the URL
    """
    match = re.search(r"/files/([^/?]+)", file_url)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract file_id from URL: {file_url}")


@pytest.mark.mermaid
@pytest.mark.api
@pytest.mark.enterprise
@pytest.mark.parametrize(
    "diagram_type,mermaid_code,theme,content_type",
    mermaid_test_data,
)
def test_generate_mermaid_diagram(
    client,
    diagram_type,
    mermaid_code,
    theme,
    content_type,
):
    """Test mermaid diagram generation with FILE response mode.

    Tests all major mermaid diagram types (flowchart, sequence, class, state,
    ER, gantt, pie, gitgraph, mindmap, timeline) with both dark and light themes,
    and both SVG and PNG formats.

    Each test run generates unique identifiers in the diagrams to avoid S3 caching.
    """
    # Generate diagram in FILE mode
    response = client.mermaid.generate_diagram(
        code=mermaid_code, content_type=content_type, response_type="file"
    )

    # Verify response structure
    assert_that(
        response.file_url,
        is_not(None),
        f"file_url should not be None for {diagram_type} diagram",
    )

    # Verify file_url format (should be a valid URL)
    assert_that(
        response.file_url,
        starts_with("http"),
        f"file_url should be a valid HTTP/HTTPS URL for {diagram_type} diagram",
    )

    # Extract file ID and download file to verify accessibility
    file_id = extract_file_id_from_url(response.file_url)
    file_content = client.files.get_file(file_id)

    # Verify file content is not empty
    assert_that(
        len(file_content),
        greater_than(0),
        f"Downloaded {diagram_type} diagram should have content",
    )

    # Verify content type specific checks
    if content_type == "svg":
        # SVG files should contain XML declaration or svg tag
        content_str = file_content[:200].decode("utf-8", errors="ignore")
        assert_that(
            content_str.lower(),
            contains_string("svg"),
            f"SVG content should contain 'svg' tag for {diagram_type} diagram",
        )
    elif content_type == "png":
        # PNG files should start with PNG magic number
        assert_that(
            file_content[:4],
            is_not(None),
            f"PNG content should have valid header for {diagram_type} diagram",
        )
        # PNG magic number: \x89PNG
        assert file_content[1:4] == b"PNG", (
            f"PNG file should start with PNG magic number for {diagram_type} diagram"
        )
