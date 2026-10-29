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

import json
import os
import random
import re
import string
import tempfile
import time
import unicodedata

from hamcrest import (
    assert_that,
    equal_to,
    contains_string,
    greater_than,
    instance_of,
    is_not,
    none,
)

from codemie_sdk import CodeMieClient
from codemie_test_harness.tests import autotest_entity_prefix


class BaseUtils:
    def __init__(self, client: CodeMieClient):
        self.client = client


def poll_until(fetch, predicate, timeout=10.0, interval=0.5):
    """Poll ``fetch()`` until ``predicate(value)`` holds, or ``timeout`` elapses.

    Useful against endpoints served from a process-local cache on a shared,
    multi-instance environment, where a read landing on a different pod than
    the one that served a preceding write can lag behind by up to the cache's
    documented staleness window. Absorbs that bounded lag before an assertion
    runs — it does not change what is ultimately asserted.

    Returns the last fetched value regardless of whether the predicate held.
    """
    deadline = time.monotonic() + timeout
    value = fetch()
    while not predicate(value) and time.monotonic() < deadline:
        time.sleep(interval)
        value = fetch()
    return value


def get_random_name():
    """Generate a random entity name, always "autotest-"-prefixed for fast
    search-based org-wide cleanup discovery (see cleanup.py, pytest_sessionfinish).
    """
    characters = string.ascii_lowercase
    random_string = "".join(random.choice(characters) for _ in range(15))
    random_name = f"autotest-{autotest_entity_prefix}{random_string}"
    return random_name


def to_camel_case(input_string):
    # Remove non-letter characters
    cleaned = re.sub(r"[^a-zA-Z]", " ", input_string)
    # Split into words
    words = cleaned.split()
    # Convert to camelCase
    camel_case = words[0].capitalize() + "".join(
        word.capitalize() for word in words[1:]
    )
    return camel_case


def clean_json(json_str):
    try:
        # Attempt to parse the JSON string directly
        return json.loads(json_str)
    except json.JSONDecodeError:
        # If JSON parsing fails, try to extract embedded JSON from Markdown-like syntax
        pattern = re.compile(
            r'(\{(?:[^{}"]|"(?:[^"\\]|\\.)*")*\}|\[(?:[^\[\]"]|"(?:[^"\\]|\\.)*")*\])'
        )

        matcher = pattern.search(json_str)

        if matcher:
            unwrapped_json_str = matcher.group(1)
            # Replace non-breaking spaces with regular spaces and remove control characters
            unwrapped_json_str = unwrapped_json_str.replace("\u00a0", " ")
            unwrapped_json_str = "".join(
                c
                for c in unwrapped_json_str
                if not (unicodedata.category(c) == "Cc" and c not in "\r\n\t")
            )
            try:
                return json.loads(unwrapped_json_str)
            except json.JSONDecodeError as inner_exception:
                raise ValueError("Invalid JSON string") from inner_exception
        else:
            raise ValueError("No JSON found in the Markdown string")


def percent_of_relevant_titles(response):
    """
    Calculate the percentage of relevant titles in a response.
    Usage:
        percent = percent_of_relevant_titles(response)
    """
    json_to_parse = clean_json(response)
    search_terms = [
        "ai",
        "artificial intelligence",
        "machine learning",
        "natural language",
    ]
    percent = (
        sum(
            1
            for item in json_to_parse
            if any(term in item.get("title", "").lower() for term in search_terms)
        )
        * 10
    )
    return percent


def wait_for_entity(get_entity_callable, entity_name, timeout=10, poll_interval=3):
    """
    Waits for an entity to be created or available with a timeout.
    :param entity_name: Entity name
    :param get_entity_callable: A callable that attempts to retrieve the entity.
                                Should raise NotFoundError if the entity is not found.
    :param timeout: The maximum time to wait for the entity (in seconds).
    :param poll_interval: The time between consecutive checks (in seconds).
    :return: The entity object if it is successfully retrieved.
    :raises TimeoutError: If the entity is not found within the timeout period.
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        entities = [
            raw
            for raw in get_entity_callable()
            if (hasattr(raw, "name") and entity_name == raw.name)
            or (hasattr(raw, "alias") and entity_name == raw.alias)
            or (hasattr(raw, "prompt") and entity_name == raw.prompt)
        ]

        if len(entities) > 0:
            return entities[0]
        time.sleep(poll_interval)

    # If timeout is reached and entity is not found, raise an error
    raise TimeoutError("Entity was not found within the timeout period.")


def assert_response(response, status_code, message=None):
    assert_that(response.status_code, equal_to(status_code))
    if message:
        error_details = json.loads(response.content)["error"].get("details", "")
        if isinstance(error_details, list):
            assert_that(error_details[0]["msg"], equal_to(message))
        elif error_details:
            assert_that(error_details, equal_to(message))
        else:
            assert_that(
                json.loads(response.content)["error"]["message"], equal_to(message)
            )


def assert_error_details(response, status_code, message):
    assert_that(
        response.status_code, equal_to(status_code), "Status code is not expected."
    )
    error_details = json.loads(response.content)["error"]["details"]
    assert_that(
        error_details, contains_string(message), "Error message is not expected."
    )


def credentials_to_dict(credentials):
    return {cred.key: cred.value for cred in credentials}


def assert_tool_triggered(tool_name, triggered_tools):
    """
    Assert that the expected tool(s) were triggered during assistant interaction.

    Args:
        tool_name: Either a single tool enum or a tuple of tool enums that should be triggered
        triggered_tools: List of tools that were actually triggered

    Raises:
        AssertionError: If any of the expected tools were not found in triggered_tools
                       (for tuples, ALL tools must be present)
    """
    # Handle both single tools and tuples of tools
    if isinstance(tool_name, tuple):
        tools_to_check = tool_name
    else:
        tools_to_check = (tool_name,)

    # Check each expected tool
    found_tools = []
    missing_tools = []

    for tool in tools_to_check:
        tool_value_lower = tool.value.lower()
        tool_value_with_spaces = tool.value.replace("_", " ").lower()

        # Check if this specific tool was triggered
        tool_found = False
        for triggered_tool in triggered_tools:
            if (
                triggered_tool.lower() == tool_value_lower
                or triggered_tool.lower() == tool_value_with_spaces
                or tool_value_with_spaces in triggered_tool.lower()
            ):
                found_tools.append(tool.value)
                tool_found = True
                break

        if not tool_found:
            missing_tools.append(tool.value)

    # Assert that ALL expected tools were found
    if missing_tools:
        expected_tools = [tool.value for tool in tools_to_check]

        if len(tools_to_check) == 1:
            assert False, (
                f"Tool validation failed:\n"
                f"Expected tool '{expected_tools[0]}' to be triggered\n"
                f"But it was not found in triggered tools: {triggered_tools}\n"
            )
        else:
            assert False, (
                f"Tool validation failed:\n"
                f"Expected ALL of these tools to be triggered: {expected_tools}\n"
                f"Missing tools: {missing_tools}\n"
                f"Found tools: {found_tools}\n"
                f"Actually triggered: {triggered_tools}\n"
            )


def assert_tool_not_triggered(tool_name, triggered_tools):
    """
    Assert that the expected tool(s) were NOT triggered during assistant interaction.

    Args:
        tool_name: Either a single tool enum or a tuple of tool enums that should not be triggered
        triggered_tools: List of tools that were actually triggered

    Raises:
        AssertionError: If any of the given tools was found in triggered_tools
    """
    tools_to_check = tool_name if isinstance(tool_name, tuple) else (tool_name,)

    unexpectedly_triggered = []
    for tool in tools_to_check:
        tool_value_lower = tool.value.lower()
        tool_value_with_spaces = tool.value.replace("_", " ").lower()

        for triggered_tool in triggered_tools:
            if (
                triggered_tool.lower() == tool_value_lower
                or triggered_tool.lower() == tool_value_with_spaces
                or tool_value_with_spaces in triggered_tool.lower()
            ):
                unexpectedly_triggered.append(tool.value)
                break

    assert not unexpectedly_triggered, (
        f"Tool validation failed:\n"
        f"Expected these tools NOT to be triggered: {unexpectedly_triggered}\n"
        f"Actually triggered: {triggered_tools}\n"
    )


def extract_file_id_from_response(response):
    """
    Extract file ID from assistant response containing file URLs.

    Args:
        response: The assistant response text containing file URL

    Returns:
        str: The extracted file ID

    Raises:
        AssertionError: If no file URL is found in the response
    """
    file_url_pattern = r"sandbox:/v1/files/([A-Za-z0-9+/=]+)"
    file_url_match = re.search(file_url_pattern, response)

    assert_that(
        file_url_match,
        is_not(none()),
        f"No file URL found in response. Expected pattern 'sandbox:/v1/files/<file_id>' in: {response}",
    )

    return file_url_match.group(1)


def download_and_verify_file(client, file_id):
    """
    Download a file by its ID and verify it was successfully downloaded.

    Args:
        client: CodeMieClient instance
        file_id: The file identifier to download

    Returns:
        bytes: The downloaded file content

    Raises:
        AssertionError: If file download fails or content is invalid
    """
    file_content = client.files.get_file(file_id)

    assert_that(file_content, f"Downloaded file with ID '{file_id}' is empty")
    assert_that(len(file_content), greater_than(0), "Downloaded file has no content")
    assert_that(file_content, instance_of(bytes), "Downloaded content should be bytes")

    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(file_content)
        temp_file_path = temp_file.name

    try:
        assert_that(os.path.exists(temp_file_path), "Temporary file was not created")
        assert_that(
            os.path.getsize(temp_file_path), greater_than(0), "Temporary file is empty"
        )
        assert_that(
            os.path.getsize(temp_file_path),
            equal_to(len(file_content)),
            "Saved file size does not match downloaded content size",
        )
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    return file_content


def extract_file_id_from_url(file_url: str) -> str:
    """Extract the file ID from a CodeMie file URL.

    Args:
        file_url: URL like https://domain/v1/files/{file_id}

    Returns:
        The file_id portion of the URL

    Raises:
        ValueError: If file ID cannot be extracted from URL
    """
    match = re.search(r"/files/([^/?]+)", file_url)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract file_id from URL: {file_url}")


def extract_last_integer(text: str) -> int:
    """Extract the LAST integer found in a raw text string.

    Used to read a numeric value out of free-form, LLM-generated text (e.g. a
    chat response or workflow output) where the exact wording is
    non-deterministic. The *last* match is preferred over the first: prompts
    that ask for "a number from 0 to 10" are frequently echoed back by the
    LLM (e.g. "Here is a number between 0 and 10: 7"), so taking the first
    digit sequence would grab a decoy bound from the echoed prompt instead of
    the actual generated value.

    Raises:
        ValueError: If no integer can be found in ``text``.
    """
    matches = re.findall(r"-?\d+", str(text))
    if matches:
        return int(matches[-1])
    raise ValueError(f"No integer found in text: {text!r}")


def verify_file_accessible(client, file_id: str) -> bytes:
    """Verify that a file is accessible and download its content.

    Args:
        client: CodeMie client instance
        file_id: File identifier

    Returns:
        File content as bytes

    Raises:
        AssertionError: If file is not accessible
    """
    try:
        content = client.files.get_file(file_id)
        assert_that(content, is_not(none()), f"File {file_id} content is None")
        assert_that(len(content), greater_than(0), f"File {file_id} has no content")
        return content
    except Exception as e:
        raise AssertionError(f"File {file_id} is not accessible: {str(e)}")
