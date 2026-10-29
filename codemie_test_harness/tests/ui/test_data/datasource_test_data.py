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
Test Data for Data Source UI – used for parametrized testing and test validation
"""

from enum import Enum


# ==================== ENUMS ====================
class DataSourceFilterType(str, Enum):
    CODE = "Code"
    CONFLUENCE = "Confluence"
    JIRA = "Jira"
    X_RAY = "X-ray"
    FILE = "File"
    GOOGLE = "Google Docs"
    PROVIDER = "Provider"
    ADO_WIKI = "Azure Devops Wiki"
    ADO_WORK_ITEM = "Azure Devops Work Item"
    SHAREPOINT = "SharePoint"
    BEDROCK = "Bedrock"
    XWIKI = "xWiki"

    def __str__(self):
        return self.value


class DataSourceType(str, Enum):
    GIT = "Git"
    CONFLUENCE = "Confluence"
    JIRA = "Jira"
    FILE = "File"
    GOOGLE = "Google Docs"
    ADO = "Azure Devops Wiki"

    def __str__(self):
        return self.value


class DataSourceFilterStatus(str, Enum):
    COMPLETED = "Completed"
    FAILED = "Failed"
    IN_PROGRESS = "In Progress"

    def __str__(self):
        return self.value


class DataSourceStatus(str, Enum):
    COMPLETED = "Completed"
    ERROR = "Error"
    FETCHING = "Fetching"

    def __str__(self):
        return self.value


class SummarizationMethod(str, Enum):
    WHOLE_CODEBASE = "Whole Codebase"
    PER_FILE = "Summarization per file"
    PER_CHUNKS = "Summarization per chunks"

    def __str__(self):
        return self.value


class EmbeddingModel(str, Enum):
    ADA = "Text Embedding Ada"
    GECKO = "Text Embedding Gecko"
    TITAN_V2 = "Titan Embed Text v2.0"

    def __str__(self):
        return self.value


class DataSourceColumnName(str, Enum):
    NAME = "Name"
    PROJECT = "Project"
    TYPE = "Type"
    CREATED_BY = "Created By"
    CREATED = "Created"
    UPDATED = "Updated"
    SHARED = "Shared"
    STATUS = "Status"
    ACTIONS = "Actions"

    def __str__(self):
        return self.value


# ==================== CONSTANTS ====================

DATA_SOURCE_FILTER_TYPES_LIST = [t for t in DataSourceFilterType]
DATA_SOURCE_TYPES_LIST = [t for t in DataSourceType]
DATA_SOURCE_FILTER_STATUSES_LIST = [s for s in DataSourceFilterStatus]
DATA_SOURCE_STATUSES_LIST = [s for s in DataSourceStatus]
DATAS_SOURCE_COLUMN_LIST = [c for c in DataSourceColumnName]
SUMMARIZATION_METHODS_LIST = [m for m in SummarizationMethod]
EMBEDDING_MODELS_LIST = [m for m in EmbeddingModel]

PROJECT_LABEL = "Project"
STATUS_LABEL = "Status"

MAIN_TITLE_DATASOURCE = "Data Sources"
MAIN_SUBTITLE_DATASOURCE = "Connect and manage your data sources in one place"
TITLE_CREATE_DATASOURCE = "New DataSource"
SUBTITLE_CREATE_DATASOURCE = "Start indexing your data source"
TITLE_VIEW_DATASOURCE = "View DataSource"
SUBTITLE_VIEW_DATASOURCE = "View your data source datails"
UPDATE_TITLE_DATASOURCE = "Update DataSource"
UPDATE_SUBTITLE_DATASOURCE = "Update your data source and start re-indexing"

ADO_INSTRUCTIONS = """
    The page path should not include "/Overview/Wiki" and must
     start from the page level. For example, if your Azure DevOps breadcrumbs
      show "ProjectName/WikiName/Overview/Wiki/Page1/Page2", use "/Page1/*" as the path. 
      Build the path using breadcrumb values, not the page URL.
    """

FILE_INSTRUCTIONS = "Supported formats: PPTX, DOCX, XLSX, XLSB, PDF, CSV, ZIP, JPEG, PNG, JPG, GIF (ZIP contents are indexed as separate documents after upload; other unrecognized formats as plain text). Maximum files: 10. Max file size: 100Mb (images: 10Mb)."
GOOGLE_EXAMPLE = "Google documents must follow a specific format for LLM routing: View Format Example"
GOOGLE_DETAILED_EXAMPLE = "For detailed instructions, refer to the Guide"

EMPTY_NAME_ERROR = "Data source name is required"
EMPTY_DESCRIPTION_ERROR = "Description is required"
EMPTY_REPO_LINK_ERROR = "Repo Link is required"
EMPTY_BRANCH_ERROR = "Branch is required"
EMPTY_CQL_ERROR = "CQL is required"
EMPTY_JQL_ERROR = "JQL is required"
EMPTY_FILE_ERROR = "At least one file is required"
EMPTY_GOOGLE_LINK_ERROR = "Google Docs link is required"
EMPTY_INTEGRATION_ERROR = "Integration is required for this data source type"

FULL_REINDEX_STARTED = (
    "Full reindexing of datasource  has been started in the background"
)

# ==================== CLONE DATA SOURCE ====================

CLONE_ACTION = "Clone"
CLONE_PAGE_TITLE = "Clone Data Source"
CLONE_SIDEBAR_TITLE = "Clone DataSource"
CLONE_SIDEBAR_SUBTITLE = "Create a new data source based on an existing one"
CLONE_DATA_SOURCE_NOT_FOUND = "Data source not found"
