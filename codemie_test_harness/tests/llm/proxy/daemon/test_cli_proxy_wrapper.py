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

"""
Test of the codemie-codex wrapper, which is served by a proxy of its own and not by the shared
daemon. The wrapper runs in an isolated HOME against a local stub upstream, so what it forwards
can be read; no stand and no live login are involved.
"""

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_length,
    not_none,
)

from codemie_test_harness.tests.utils.cli_proxy_utils import (
    PROJECT_NAME,
    completed_response_stream,
)

WRAPPER_LABEL = "codemie-codex"


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_codemie_codex_task_is_served_by_its_own_proxy_not_the_shared_daemon(
    cli_proxy_env_factory,
):
    # @case cli-proxy-one-daemon-serves_TC_018
    env = cli_proxy_env_factory(responder=completed_response_stream)
    env.make_git_repository()

    result = env.run("codemie-codex", "--task", "Say hello", timeout=120)

    assert_that(
        result.returncode,
        equal_to(0),
        f"the command exits 0: {result.stdout}{result.stderr}",
    )
    assert_that(
        result.stdout + result.stderr, contains_string("hello"), "the task output"
    )
    served = env.stub.model_requests("/responses")
    assert_that(served, has_length(1), "the task request reached the upstream once")
    assert_that(
        served[0].client, equal_to(WRAPPER_LABEL), "served as the wrapper's own client"
    )
    assert_that(
        served[0].headers.get("x-litellm-session-id"),
        not_none(),
        "the codemie-codex session affinity header",
    )
    assert_that(
        served[0].headers["x-codemie-project"],
        equal_to(PROJECT_NAME),
        "the profile project",
    )
    assert_that(env.state(), equal_to(None), "no shared daemon state was written")
    assert_that(env.daemon_pids(), equal_to([]), "no shared daemon process was started")
