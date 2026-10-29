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

import logging
from typing import TypeVar, Type, Optional, Any, Union, Dict, List

import requests
from codemie_sdk.utils.http import ApiRequestHandler
from codemie_sdk.utils.http import log_request
from pydantic import BaseModel

T = TypeVar("T", bound=Union[BaseModel, List[BaseModel], dict])

logger = logging.getLogger(__name__)


class RequestHandler(ApiRequestHandler):
    """Handles HTTP requests with consistent error handling and response parsing."""

    @log_request
    def post(
        self,
        endpoint: str,
        response_model: Type[T] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        wrap_response: bool = True,
    ) -> Union[T, requests.Response]:
        """Makes a POST request and parses the response.

        Args:
            endpoint: API endpoint path
            response_model: Pydantic model class or List[Model] for response
            json_data: JSON request body
            params: Query parameters
            stream: Whether to return streaming response
            wrap_response: Whether response is wrapped in 'data' field

        Returns:
            Parsed response object/list or streaming response
        """
        if json_data:
            logger.debug(f"Request body: {json_data}")
        if params:
            logger.debug(f"Request params: {params}")

        response = requests.post(
            url=f"{self._base_url}{endpoint}",
            headers=self._get_headers(),
            json=json_data,
            params=params,
            verify=self._verify_ssl,
            stream=stream,
        )

        if stream:
            return response

        return self._parse_response(response, response_model, wrap_response)

    @log_request
    def get(
        self,
        endpoint: str,
        response_model: Type[T] = None,
        params: Optional[Dict[str, Any]] = None,
        wrap_response: bool = True,
    ) -> Union[T, requests.Response]:
        """Makes a GET request and parses the response.

        Args:
            endpoint: API endpoint path
            response_model: Pydantic model class or List[Model] for response
            params: Query parameters
            wrap_response: Whether response is wrapped in 'data' field

        Returns:
            Parsed response object or list of objects
        """
        if params:
            logger.debug(f"Request params: {params}")
        response = requests.get(
            url=f"{self._base_url}{endpoint}",
            headers=self._get_headers(),
            params=params,
            verify=self._verify_ssl,
        )

        if response_model:
            return self._parse_response(response, response_model, wrap_response)

        return response

    @log_request
    def put(
        self,
        endpoint: str,
        json_data: Dict[str, Any],
        response_model: Type[T] = None,
        params: Optional[Dict[str, Any]] = None,
        wrap_response: bool = True,
    ) -> Union[T, requests.Response]:
        """Makes a PUT request and parses the response.

        Args:
            endpoint: API endpoint path
            response_model: Pydantic model class or List[Model] for response
            json_data: JSON request body
            params: Query parameters
            wrap_response: Whether response is wrapped in 'data' field

        Returns:
            Parsed response object or list of objects
        """
        logger.debug(f"Request body: {json_data}")
        response = requests.put(
            url=f"{self._base_url}{endpoint}",
            headers=self._get_headers(),
            json=json_data,
            params=params,
            verify=self._verify_ssl,
        )

        if response_model:
            return self._parse_response(response, response_model, wrap_response)

        return response

    @log_request
    def delete(
        self,
        endpoint: str,
    ) -> requests.Response:
        """Makes a DELETE request and parses the response.

        Args:
            endpoint: API endpoint path

        Returns:
            response object
        """
        response = requests.delete(
            url=f"{self._base_url}{endpoint}",
            headers=self._get_headers(),
            verify=self._verify_ssl,
        )

        return response
