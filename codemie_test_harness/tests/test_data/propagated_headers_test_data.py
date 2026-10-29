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

"""Test data for workflow header propagation tests.

Notes on header casing:
  The backend normalizes all header names to lowercase before storing them in
  the context store.  Test assertions must therefore use lowercase key names
  (e.g. "x-custom-header") even though the values are sent in mixed case.

Notes on sensitive-header test data:
  MIXED_HEADERS_WITH_SENSITIVE only contains X-* headers (both allowed and
  sensitive).  Non-X-* sensitive headers such as Authorization and Cookie are
  intentionally excluded because:
    a) passing them via the SDK headers= parameter overrides the SDK's own
       bearer-token, causing authentication failure;
    b) they are not X-*-prefixed, so they would not appear in propagated_headers
       regardless of the sensitive-header denylist.

Note on TC-04 (CRLF injection):
  TC-04 has been removed. The requests HTTP library (>=2.x) rejects CRLF in
  header values at the client level before the request is sent, so server-side
  CRLF-stripping cannot be exercised via standard E2E tests.
"""

# Header sets for TC-01 parametrized variants
SINGLE_CUSTOM_HEADER = {"X-Custom-Header": "test-value"}
MULTIPLE_CUSTOM_HEADERS = {"X-Custom-Header": "val1", "X-Request-Id": "req-123"}

# Sensitive + allowed mix for TC-03
# Only X-* headers are included so authentication is not disrupted.
# x-api-key and x-auth-token are on the backend sensitive-header denylist.
MIXED_HEADERS_WITH_SENSITIVE = {
    "X-Custom-Header": "allowed-value",
    "x-api-key": "secret-key",
    "x-auth-token": "sensitive-token",
}
# TC-06 first-turn header (inline dict anti-pattern prevented by moving here)
TC06_FIRST_HEADERS = {"X-Custom-Header": "tc06-value"}

# Non-X-* headers for TC-05
NON_X_HEADERS = {"Content-Type": "application/json", "Accept": "*/*"}
