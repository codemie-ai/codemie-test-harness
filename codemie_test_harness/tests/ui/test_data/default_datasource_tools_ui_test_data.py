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

"""Labels the assistant and workflow forms show for the datasource default tools."""

# Label of the knowledge base search tool, the one default tool the forms list by name.
SEARCH_KB_LABEL = "Search Knowledge Base"

# Toolkit group that holds the default tools in the Available Tools section.
CODEBASE_TOOLS_GROUP = "Codebase Tools"

# Tool names the saved assistant must not keep in its toolkits: the frontend carries
# their state only in disabled_context_tools.
DEFAULT_TOOL_NAMES = ["get_repository_file_tree", "search_code_repo", "search_kb"]
