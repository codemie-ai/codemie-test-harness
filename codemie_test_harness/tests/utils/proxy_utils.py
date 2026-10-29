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
Utilities for testing LLM proxy endpoints.
"""

import json
import requests
from typing import Dict, Any, List, Optional

from codemie_test_harness.tests import API_DOMAIN, VERIFY_SSL
from codemie_test_harness.tests.utils.base_utils import BaseUtils


class ProxyUtils(BaseUtils):
    """Utilities for testing LLM proxy endpoints."""

    def __init__(self, client):
        super().__init__(client)
        self.messages_url = f"{API_DOMAIN}/v1/messages"
        self.count_tokens_url = f"{API_DOMAIN}/v1/messages/count_tokens"
        self.embeddings_url = f"{API_DOMAIN}/v1/embeddings"
        self._headers = {
            "Authorization": f"Bearer {client.token}",
            "Content-Type": "application/json",
            "X-CodeMie-Client": "test-harness",
            "X-CodeMie-Branch": "Función nueva",
        }

    def send_messages_request(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        max_tokens: int = 100,
        stream: bool = False,
        integration_id: Optional[str] = None,
        timeout: int = 30,
        extra_headers: Optional[Dict[str, str]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> requests.Response:
        """
        Send request to /v1/messages endpoint.
        """
        headers = self._headers.copy()
        if integration_id:
            headers["X-CodeMie-Integration"] = integration_id
        if extra_headers:
            headers.update(extra_headers)

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if stream:
            payload["stream"] = True
        if tools:
            payload["tools"] = tools

        return requests.post(
            self.messages_url,
            headers=headers,
            json=payload,
            verify=VERIFY_SSL,
            stream=stream,
            timeout=timeout,
        )

    def send_count_tokens_request(
        self,
        model: str,
        messages: List[Dict[str, str]],
        integration_id: Optional[str] = None,
        timeout: int = 10,
    ) -> requests.Response:
        """
        Send request to /v1/messages/count_tokens endpoint.
        """
        headers = self._headers.copy()
        if integration_id:
            headers["X-CodeMie-Integration"] = integration_id

        payload = {"model": model, "messages": messages}

        return requests.post(
            self.count_tokens_url,
            headers=headers,
            json=payload,
            verify=VERIFY_SSL,
            timeout=timeout,
        )

    def send_embeddings_request(
        self,
        model: str,
        input_text: Any,
        integration_id: Optional[str] = None,
        timeout: int = 30,
    ) -> requests.Response:
        """
        Send request to /v1/embeddings endpoint.
        """
        headers = self._headers.copy()
        if integration_id:
            headers["X-CodeMie-Integration"] = integration_id

        payload = {"model": model, "input": input_text}

        return requests.post(
            self.embeddings_url,
            headers=headers,
            json=payload,
            verify=VERIFY_SSL,
            timeout=timeout,
        )

    def send_unauthenticated_request(
        self, url: str, payload: Dict[str, Any], timeout: int = 10
    ) -> requests.Response:
        """
        Send request without authentication.
        """
        headers = {"Content-Type": "application/json"}

        return requests.post(
            url,
            headers=headers,
            json=payload,
            verify=VERIFY_SSL,
            timeout=timeout,
            allow_redirects=False,
        )

    def parse_streaming_response(self, response: requests.Response) -> List[Dict]:
        """
        Parse SSE streaming response and return list of chunks.
        """
        chunks = []
        for line in response.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                data = line[6:]  # Remove "data: " prefix
                if data != "[DONE]":
                    try:
                        chunk = json.loads(data)
                        chunks.append(chunk)
                    except json.JSONDecodeError:
                        pass
        return chunks
