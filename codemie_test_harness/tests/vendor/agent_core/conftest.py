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

"""Fixtures shared across AgentCore vendor tests."""

import pytest
from requests import HTTPError


@pytest.fixture
def install_endpoint(vendor_runtime_utils):
    """Factory fixture that installs an endpoint with structured config and uninstalls it on teardown."""
    state = {"vendor": None, "ai_run_id": None}

    def _with_config(vendor_type, runtime_id, endpoint_name, setting_id, **kwargs):
        state["vendor"] = vendor_type
        summary = vendor_runtime_utils.install_endpoint_with_config(
            vendor=vendor_type,
            runtime_id=runtime_id,
            endpoint_name=endpoint_name,
            setting_id=setting_id,
            **kwargs,
        )
        state["ai_run_id"] = summary.aiRunId
        return summary

    yield _with_config

    if state["ai_run_id"]:
        try:
            vendor_runtime_utils.uninstall_endpoint(
                vendor=state["vendor"], ai_run_id=state["ai_run_id"]
            )
        except HTTPError as exc:
            if exc.response.status_code != 404:
                raise


@pytest.fixture
def managed_conversation(conversation_utils):
    """Factory fixture that creates a conversation and deletes it on teardown."""
    _conversation_id = None

    def _create(initial_assistant_id):
        nonlocal _conversation_id
        conv = conversation_utils.create_conversation(
            initial_assistant_id=initial_assistant_id
        )
        _conversation_id = conv["id"]
        return conv

    yield _create

    if _conversation_id:
        conversation_utils.delete_conversation(_conversation_id)
