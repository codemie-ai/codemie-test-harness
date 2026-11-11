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

"""Test data for the assistants-requests analytics tests (/v1/analytics/assistants-requests)."""

# Rows of a request made a moment ago fall in this window.
REQUESTS_TIME_PERIOD = "last_24_hours"

# Analytics documents and ledger costs are written asynchronously after the chat reply.
REQUESTS_INDEX_TIMEOUT_S = 180
REQUESTS_POLL_INTERVAL_S = 5

# Both endpoints are paged; the largest page the API serves.
MAX_PER_PAGE = 1000

# The ledger figure and the chats total are the same value; allow only float noise.
COST_TOLERANCE = 1e-6

# A valid ClientSource value that no request made by the harness carries.
UNUSED_CLIENT_SOURCE = "chrome_extension"

CORRELATION_COLUMNS = (
    "request_id",
    "timestamp",
    "conversation_id",
    "assistant_id",
    "assistant_name",
    "user_id",
    "project",
    "llm_model",
    "client_source",
)

REQUEST_METRIC_COLUMNS = (
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "cache_read_input_tokens",
    "money_spent",
    "cached_tokens_money_spent",
    "execution_time",
    "status",
)

# Only the request status is stored per request; error message and class are not.
ERROR_DETAIL_COLUMN_FRAGMENT = "error"
SUCCESS_STATUS = "success"

FIRST_PROMPT = "What is 1+1? Answer with the number only."
SECOND_PROMPT = "Add 5 to the previous result. Answer with the number only."
