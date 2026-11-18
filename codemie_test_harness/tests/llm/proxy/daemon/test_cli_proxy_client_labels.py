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
Tests of how one CodeMie CLI proxy daemon serves every client: the client a request is
served as is named by the gateway key it sends, and the label the upstream receives follows it.

Each test runs the installed `codemie` CLI in an isolated HOME with a local stub upstream as
the profile's API, so the forwarded headers and bodies can be read. No stand is involved.
"""

import pytest
import requests
from hamcrest import (
    assert_that,
    equal_to,
    has_entries,
    is_,
    is_not,
    none,
    starts_with,
)

from codemie_test_harness.tests.test_data.cli_proxy_daemon_test_data import (
    CLIENT_CLAUDE_DESKTOP,
    CLIENT_CODEX_DESKTOP,
    CLIENT_DAEMON,
    CLIENT_VSCODE_BYOK,
    CLIENT_VSCODE_CLAUDE_CODE,
    INVALID_KEY_BODY,
    LEGACY_RECORDS,
    NON_DESKTOP_CLIENTS,
    REFUSED_KEYS,
    SIGN_IN_KEYS,
    SIGN_IN_PROMPT_START,
)
from codemie_test_harness.tests.utils.cli_proxy_utils import (
    STREAM_ANSWER,
    reject_replayed_reasoning_once,
)

# Carries what each normaliser changes: an enabled thinking budget (Claude), an undated model
# name and an empty tool description (Codex).
NORMALISER_BODY = {
    "thinking": {"type": "enabled", "budget_tokens": 10000},
    "tools": [{"name": "lookup", "description": ""}],
    "messages": [],
}
REPLAYED_REASONING = {
    "model": "gpt-5-2-2026-01-15",
    "include": ["reasoning.encrypted_content"],
    "input": [
        {"type": "reasoning", "encrypted_content": "abc=="},
        {"type": "message", "role": "user", "content": "hi"},
    ],
}


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_two_clients_stream_concurrently_through_one_daemon_with_own_labels(
    cli_proxy_env_factory,
):
    # @case cli-proxy-one-daemon-serves_TC_001
    env = cli_proxy_env_factory(stream=True, release_after_arrivals=2)
    env.start_daemon()

    desktop, codex = env.post_concurrently(
        (
            "/v1/messages",
            env.bearer(CLIENT_CLAUDE_DESKTOP),
            {"model": "claude-sonnet-5", **NORMALISER_BODY},
        ),
        (
            "/v1/responses",
            env.bearer(CLIENT_CODEX_DESKTOP),
            {"model": "gpt-5.2", **NORMALISER_BODY},
        ),
    )

    assert_that(desktop.status_code, equal_to(200), "Desktop stream status")
    assert_that(codex.status_code, equal_to(200), "Codex stream status")
    assert_that(desktop.text, equal_to(STREAM_ANSWER), "Desktop stream completed")
    assert_that(codex.text, equal_to(STREAM_ANSWER), "Codex stream completed")
    assert_that(
        env.stub.peak_open,
        equal_to(2),
        "both streams were open at the upstream at once",
    )
    desktop_seen = env.stub.model_requests("/v1/messages")[0]
    codex_seen = env.stub.model_requests("/v1/responses")[0]
    assert_that(desktop_seen.client, equal_to(CLIENT_CLAUDE_DESKTOP), "Desktop label")
    assert_that(codex_seen.client, equal_to(CLIENT_CODEX_DESKTOP), "Codex label")
    # Only the Claude normaliser touched the Desktop request: thinking became adaptive, the model
    # name stayed, the empty tool description stayed.
    assert_that(
        desktop_seen.json,
        has_entries(
            model="claude-sonnet-5",
            thinking={"type": "adaptive"},
            tools=[{"name": "lookup", "description": ""}],
        ),
        "Desktop body after the Claude normaliser only",
    )
    # Only the Codex normaliser touched the Codex request: model resolved to a deployment, the
    # empty tool description repaired, thinking left as sent.
    assert_that(
        codex_seen.json,
        has_entries(
            model="gpt-5-2-2026-01-15",
            thinking={"type": "enabled", "budget_tokens": 10000},
            tools=[{"name": "lookup", "description": "lookup"}],
        ),
        "Codex body after the Codex normaliser only",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("client_name", NON_DESKTOP_CLIENTS)
def test_non_desktop_client_carries_own_label_and_no_cowork_repository(
    daemon_env, client_name
):
    # @case cli-proxy-one-daemon-serves_TC_002
    daemon_env.start_daemon()

    response = daemon_env.post(
        "/v1/responses",
        daemon_env.bearer(client_name),
        {"model": "gpt-5.2", "input": []},
    )

    assert_that(response.status_code, equal_to(200), "request is forwarded")
    seen = daemon_env.stub.model_requests()[-1]
    assert_that(seen.client, equal_to(client_name), "own label")
    assert_that(
        seen.client, is_not(equal_to(CLIENT_CLAUDE_DESKTOP)), "no Desktop label"
    )
    assert_that(
        seen.headers.get("x-codemie-repository"), is_(none()), "no Cowork repository"
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_desktop_client_is_the_only_one_carrying_the_cowork_repository(daemon_env):
    # @case cli-proxy-one-daemon-serves_TC_002
    daemon_env.start_daemon()

    daemon_env.post(
        "/v1/messages",
        daemon_env.bearer(CLIENT_CLAUDE_DESKTOP),
        {"model": "claude-opus-4-5", "messages": []},
    )

    seen = daemon_env.stub.model_requests()[-1]
    assert_that(seen.client, equal_to(CLIENT_CLAUDE_DESKTOP), "Desktop label")
    assert_that(
        seen.headers.get("x-codemie-repository"),
        equal_to("Cowork"),
        "Cowork repository, Desktop only",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("key_template", REFUSED_KEYS)
def test_key_naming_no_known_client_is_refused_like_a_wrong_key(
    daemon_env, key_template
):
    # @case cli-proxy-one-daemon-serves_TC_003
    daemon_env.start_daemon()
    bearer = key_template.format(key=daemon_env.gateway_key)

    response = daemon_env.post(
        "/v1/responses", bearer, {"model": "gpt-5.2", "input": []}
    )

    assert_that(response.status_code, equal_to(401), "refused")
    assert_that(response.json(), equal_to(INVALID_KEY_BODY), "same body as a wrong key")
    assert_that(
        daemon_env.stub.model_requests(), equal_to([]), "nothing reached the upstream"
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_key_naming_the_generic_client_is_accepted(daemon_env):
    # @case cli-proxy-one-daemon-serves_TC_003
    daemon_env.start_daemon()

    response = daemon_env.post(
        "/v1/responses",
        daemon_env.bearer(CLIENT_DAEMON),
        {"model": "gpt-5.2", "input": []},
    )

    assert_that(response.status_code, equal_to(200), "accepted, not 401")
    assert_that(
        daemon_env.stub.model_requests()[-1].client,
        equal_to(CLIENT_DAEMON),
        "served as the generic client",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("record_fields, label", LEGACY_RECORDS)
def test_shared_key_is_served_as_the_client_the_older_cli_recorded(
    daemon_env, record_fields, label
):
    # @case cli-proxy-one-daemon-serves_TC_005
    daemon_env.write_record(**record_fields)
    daemon_env.start_daemon()

    response = daemon_env.post(
        "/v1/responses", daemon_env.bearer(), {"model": "gpt-5.2", "input": []}
    )

    assert_that(response.status_code, equal_to(200), "request is forwarded")
    assert_that(
        daemon_env.stub.model_requests()[-1].client,
        equal_to(label),
        "label of the recorded identity",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_upstream_rejecting_replayed_reasoning_strips_only_that_client(
    cli_proxy_env_factory,
):
    # @case cli-proxy-one-daemon-serves_TC_015
    env = cli_proxy_env_factory(
        responder=reject_replayed_reasoning_once(CLIENT_CODEX_DESKTOP)
    )
    env.start_daemon()

    rejected = env.post(
        "/v1/responses", env.bearer(CLIENT_CODEX_DESKTOP), REPLAYED_REASONING
    )
    other = env.post(
        "/v1/responses", env.bearer(CLIENT_VSCODE_BYOK), REPLAYED_REASONING
    )
    again = env.post(
        "/v1/responses", env.bearer(CLIENT_CODEX_DESKTOP), REPLAYED_REASONING
    )

    assert_that(
        rejected.status_code,
        equal_to(400),
        "the first Codex request is rejected upstream",
    )
    assert_that(other.status_code, equal_to(200), "the other client is served")
    assert_that(again.status_code, equal_to(200), "the next Codex request is served")
    first_codex, other_client, next_codex = env.stub.model_requests("/v1/responses")
    assert_that(
        first_codex.json["input"],
        equal_to(REPLAYED_REASONING["input"]),
        "first request carries its reasoning state",
    )
    assert_that(
        other_client.json["input"],
        equal_to(REPLAYED_REASONING["input"]),
        "other client keeps its reasoning state",
    )
    assert_that(
        other_client.json["include"],
        equal_to(["reasoning.encrypted_content"]),
        "other client keeps its include",
    )
    assert_that(
        next_codex.json["input"],
        equal_to([REPLAYED_REASONING["input"][1]]),
        "rejecting client is stripped",
    )
    assert_that(
        next_codex.json["include"],
        equal_to([]),
        "rejecting client no longer asks for encrypted content",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
@pytest.mark.parametrize("key_kind", SIGN_IN_KEYS)
def test_accepted_key_gets_the_sign_in_prompt_while_daemon_awaits_login(
    cli_proxy_env_factory, key_kind
):
    # @case cli-proxy-one-daemon-serves_TC_022
    env = cli_proxy_env_factory(signed_in=False)
    env.write_sign_in_lock()
    result = env.cold_start()
    assert_that(
        result.returncode,
        equal_to(0),
        f"daemon started: {result.stdout}{result.stderr}",
    )
    bearer = env.bearer() if key_kind == "shared" else env.bearer(CLIENT_CLAUDE_DESKTOP)

    response = env.post(
        "/v1/messages", bearer, {"model": "claude-opus-4-5", "messages": []}
    )

    assert_that(response.status_code, equal_to(401), "sign-in 401")
    assert_that(response.json()["error"]["type"], equal_to("authentication_error"))
    assert_that(response.json()["error"]["message"], starts_with(SIGN_IN_PROMPT_START))
    assert_that(env.stub.model_requests(), equal_to([]), "nothing reached the upstream")


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_unaccepted_key_gets_invalid_key_while_daemon_awaits_login(
    cli_proxy_env_factory,
):
    # @case cli-proxy-one-daemon-serves_TC_022
    env = cli_proxy_env_factory(signed_in=False)
    env.write_sign_in_lock()
    env.cold_start()

    response = env.post(
        "/v1/messages",
        "not-the-gateway-key",
        {"model": "claude-opus-4-5", "messages": []},
    )

    assert_that(response.status_code, equal_to(401), "refused")
    assert_that(
        response.json(),
        equal_to(INVALID_KEY_BODY),
        "Invalid API key, not the sign-in prompt",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_analytics_request_and_health_do_not_start_a_sign_in_while_daemon_awaits_login(
    cli_proxy_env_factory,
):
    # @case cli-proxy-one-daemon-serves_TC_022
    env = cli_proxy_env_factory(signed_in=False)
    env.write_sign_in_lock()
    env.cold_start()
    lock_before = (env.codemie_home / "sso-login.lock").read_text()

    analytics = env.post("/v1/analytics/events", env.bearer(), {})
    health = requests.get(env.url("/health"), timeout=30)

    assert_that(
        analytics.status_code, equal_to(401), "analytics is refused without a login"
    )
    assert_that(
        analytics.json()["error"]["message"],
        is_not(starts_with(SIGN_IN_PROMPT_START)),
        "analytics gets no sign-in prompt",
    )
    assert_that(health.status_code, equal_to(200), "/health answers")
    assert_that(
        (env.codemie_home / "sso-login.lock").read_text(),
        equal_to(lock_before),
        "no sign-in was started: the lock is untouched",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_shared_key_request_of_a_cowork_session_is_relabelled_claude_desktop(
    daemon_env,
):
    # @case cli-proxy-one-daemon-serves_TC_023
    daemon_env.write_record(clientType=CLIENT_CODEX_DESKTOP)
    daemon_env.start_daemon()
    working_dir = daemon_env.home / "cowork-project"
    working_dir.mkdir()
    cowork_session = "cw-session-0001"
    daemon_env.write_cowork_session(cowork_session, working_dir)
    headers = {"x-claude-code-session-id": cowork_session}
    body = {"model": "claude-opus-4-5", "messages": []}

    daemon_env.post("/v1/messages", daemon_env.bearer(), body, headers)
    daemon_env.post(
        "/v1/messages", daemon_env.bearer(CLIENT_CODEX_DESKTOP), body, headers
    )

    shared, named = daemon_env.stub.model_requests()
    assert_that(
        shared.client,
        equal_to(CLIENT_CLAUDE_DESKTOP),
        "shared key of a Cowork session is relabelled",
    )
    assert_that(
        named.client,
        equal_to(CLIENT_CODEX_DESKTOP),
        "named key with the same header keeps its own label",
    )
    assert_that(
        named.headers.get("x-codemie-repository"),
        is_(none()),
        "named key takes no Cowork repository",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_shared_key_request_of_no_cowork_session_keeps_the_default_client(daemon_env):
    # @case cli-proxy-one-daemon-serves_TC_023
    daemon_env.write_record(clientType=CLIENT_CODEX_DESKTOP)
    daemon_env.start_daemon()

    daemon_env.post(
        "/v1/messages",
        daemon_env.bearer(),
        {"model": "claude-opus-4-5", "messages": []},
        {"x-claude-code-session-id": "no-such-cowork-session"},
    )

    assert_that(
        daemon_env.stub.model_requests()[-1].client,
        equal_to(CLIENT_CODEX_DESKTOP),
        "an unattributed shared-key request stays the default client",
    )


@pytest.mark.llm
@pytest.mark.proxy
@pytest.mark.api
def test_vscode_claude_code_is_served_as_claude_desktop_without_the_cowork_fallback(
    daemon_env,
):
    # @case cli-proxy-one-daemon-serves_TC_024
    daemon_env.start_daemon()
    body = {"model": "claude-sonnet-5", **NORMALISER_BODY}

    response = daemon_env.post(
        "/v1/messages", daemon_env.bearer(CLIENT_VSCODE_CLAUDE_CODE), body
    )

    assert_that(response.status_code, equal_to(200), "request is forwarded")
    seen = daemon_env.stub.model_requests()[-1]
    assert_that(
        seen.client,
        equal_to(CLIENT_CLAUDE_DESKTOP),
        "extension keeps the Desktop label",
    )
    assert_that(
        seen.json,
        has_entries(thinking={"type": "adaptive"}),
        "Claude normalisation applied",
    )
    assert_that(
        seen.headers.get("x-codemie-repository"), is_(none()), "no Cowork repository"
    )
