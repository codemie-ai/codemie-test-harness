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

from codemie_test_harness.tests.enums.tools import OpenApiTool

INVOKE_API_TOOL_TASK = (
    "Invoke GET /v1/info endpoint. Url you can get from tools available"
)

# "{version}" is resolved from a live GET /v1/info call at test time (see
# test_create_assistant_with_open_api_tool) instead of being hardcoded here,
# since the platform's own version changes on every release.
RESPONSE_FOR_INVOKE_API = """
    Here are the details from the `/v1/info` endpoint:

    - **Message:** Codemie
    - **Version:** {version}
    - **Description:** Smart AI assistant 'CodeMie'

    If you need further details or assistance, feel free to ask!
"""

OPEN_API_SPEC_TOOL_TASK = "Provide the details about '/v1/assistants' endpoint"

RESPONSE_FOR_OPEN_API_SPEC = """
    The `/v1/assistants` endpoint supports both `GET` and `POST` methods. Here are the details:

    ### GET `/v1/assistants`
    Returns all saved assistants.
    
    - **Tags:** Assistant
    - **Summary:** Index Assistants
    - **Description:** Returns all saved assistants.
    - **Operation ID:** index_assistants_v1_assistants_get
    - **Security:**
      - user-id
      - Authorization
    - **Parameters:**
      - `scope` (query, optional): The scope of assistants to retrieve. Default is `visible_to_user`.
      - `minimal_response` (query, optional): Minimal response flag. Default is `false`.
      - `filters` (query, optional): Filters for the assistants.
      - `page` (query, optional): The page number. Default is `0`.
      - `per_page` (query, optional): Number of items per page. Default is `12`.
    - **Responses:**
      - `200` Successful Response: Returns an array of AssistantListResponse.
      - `422` Validation Error
    
    ### POST `/v1/assistants`
    Creates a new assistant.
    
    - **Tags:** Assistant
    - **Summary:** Create Assistant
    - **Description:** Index user-specific assistant to Elastic with project field.
    - **Operation ID:** create_assistant_v1_assistants_post
    - **Security:**
      - user-id
      - Authorization
    - **Request Body:**
      - Required. The request body must conform to the AssistantRequest schema.
    - **Responses:**
      - `200` Successful Response: Returns a BaseResponse.
      - `422` Validation Error
    
    These endpoints relate to managing assistants, allowing you to list and create assistants in the system.
"""

INVOKE_EXTERNAL_API_TOOL_TASK = (
    "Invoke GET https://api.open-meteo.com/v1/forecast?latitude=51.5&longitude=-0.1"
)

# Only the latitude/longitude the prompt actually asked for are asserted.
# generationtime_ms, utc_offset, timezone and elevation are dropped: they
# either change on every real call to the external api.open-meteo.com API
# or are third-party-supplied facts not echoed from the request.
RESPONSE_EXTERNAL_FOR_INVOKE_API = """
    The response from the Open Meteo API for the latitude 51.5 and longitude -0.1 is as follows:

    - **Latitude**: 51.5
    - **Longitude**: -0.1
"""

open_api_tools_test_data = [
    pytest.param(
        (OpenApiTool.INVOKE_EXTERNAL_API, OpenApiTool.GET_OPEN_API_SPEC),
        INVOKE_API_TOOL_TASK,
        RESPONSE_FOR_INVOKE_API,
        marks=pytest.mark.smoke,
    ),
    (
        OpenApiTool.GET_OPEN_API_SPEC,
        OPEN_API_SPEC_TOOL_TASK,
        RESPONSE_FOR_OPEN_API_SPEC,
    ),
    (
        OpenApiTool.INVOKE_EXTERNAL_API,
        INVOKE_EXTERNAL_API_TOOL_TASK,
        RESPONSE_EXTERNAL_FOR_INVOKE_API,
    ),
]
