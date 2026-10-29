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

"""A workspace script run straight through the REST API has no tool context.

Without an assistant or a workflow there is nothing that bounds which tools a script may
call, so every tool call from such a run is refused with a clear error.
"""

import uuid

import pytest
from hamcrest import assert_that, has_entries, has_key

from codemie_test_harness.tests import API_DOMAIN, VERIFY_SSL
from codemie_test_harness.tests.test_data.workspace_script_test_data import (
    CODE_NO_CONTEXT,
    NO_CONTEXT_MARKER,
    NO_CONTEXT_SCRIPT,
)
from codemie_test_harness.tests.utils.http_utils import RequestHandler
from codemie_test_harness.tests.utils.workspace_script_utils import (
    extract_marked_json,
    unique_script_name,
)


@pytest.fixture
def workspace_api(client):
    return RequestHandler(API_DOMAIN, client.token, VERIFY_SSL)


@pytest.mark.workspace
@pytest.mark.api
def test_tool_call_from_directly_run_script_is_refused(workspace_api):
    """Create a workspace, put the script in it, run it via the REST route: the tool call gets no_context."""
    script_name = unique_script_name("direct")
    workspace = workspace_api.post(
        "/v1/workspaces",
        dict,
        json_data={"conversation_id": str(uuid.uuid4()), "name": script_name},
    )
    workspace_api.put(
        f"/v1/workspaces/{workspace['id']}/files",
        json_data={"file_path": script_name, "content": NO_CONTEXT_SCRIPT},
        response_model=dict,
    )

    result = workspace_api.post(
        f"/v1/workspaces/{workspace['id']}/execute",
        dict,
        json_data={"script_path": script_name},
    )

    assert_that(result, has_key("output"))
    outcome = extract_marked_json(result["output"], NO_CONTEXT_MARKER)
    assert_that(outcome["error"], has_entries(code=CODE_NO_CONTEXT))
