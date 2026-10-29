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

from enum import Enum


class Toolkit(str, Enum):
    """Enum for toolkits."""

    GIT = "Git"
    VCS = "VCS"
    CODEBASE_TOOLS = "Codebase Tools"
    CODE_EXPLORATION = "CodeExplorationToolkit"
    CLOUD = "Cloud"
    RESEARCH = "Research"
    AZURE_DEVOPS_TEST_PLAN = "Azure DevOps Test Plan"
    AZURE_DEVOPS_WORK_ITEM = "Azure DevOps Work Item"
    AZURE_DEVOPS_WIKI = "Azure DevOps Wiki"
    NOTIFICATION = "Notification"
    PROJECT_MANAGEMENT = "Project Management"
    FILE_MANAGEMENT = "FileSystem"
    OPEN_API = "OpenAPI"
    DATA_MANAGEMENT = "Data Management"
    SERVICENOW = "IT Service Management"
    ACCESS_MANAGEMENT = "Access Management"
    REPORT_PORTAL = "Report Portal"
    AGENT_WORKSPACE = "AgentWorkspace"
    XWIKI = "XWiki"


class GitTool(str, Enum):
    """Enum for Git tool names."""

    LIST_BRANCHES_IN_REPO = "list_branches_in_repo"
    CREATE_BRANCH = "create_branch"
    SET_ACTIVE_BRANCH = "set_active_branch"
    CREATE_FILE = "create_file"
    UPDATE_FILE = "update_file"
    UPDATE_FILE_DIFF = "update_file_diff"
    DELETE_FILE = "delete_file"
    CREATE_PULL_REQUEST = "create_pull_request"
    GET_PR_CHANGES = "get_pr_changes"
    CREATE_PR_CHANGES_COMMENT = "create_pr_changes_comment"


class CodeBaseTool(str, Enum):
    """Enum for CodeBase tool names."""

    SONAR = "Sonar"
    SONAR_CLOUD = "Sonar Cloud"
    GET_REPOSITORY_FILE_TREE_V2 = "get_repository_file_tree_v2"
    SEARCH_CODE_REPO_V2 = "search_code_repo_v2"
    READ_FILES_CONTENT = "read_files_content"
    READ_FILES_CONTENT_SUMMARY = "read_files_content_summary"
    SEARCH_CODE_REPO_BY_PATH = "search_code_repo_by_path"


class VcsTool(str, Enum):
    """Enum for VCS tool names."""

    GITLAB = "gitlab"
    GITHUB = "github"
    AZURE_DEVOPS_GIT = "azure_devops_git"


class CloudTool(str, Enum):
    """Enum for Cloud tool names."""

    AWS = "AWS"
    GCP = "GCP"
    AZURE = "Azure"
    KUBERNETES = "Kubernetes"


class AzureDevOpsWikiTool(str, Enum):
    """Enum for Azure DevOps Wiki tool names."""

    GET_WIKI = "get_wiki"
    GET_WIKI_PAGE_BY_PATH = "get_wiki_page_by_path"
    GET_WIKI_PAGE_BY_ID = "get_wiki_page_by_id"
    DELETE_WIKI_PAGE_BY_PATH = "delete_page_by_path"
    DELETE_WIKI_PAGE_BY_ID = "delete_page_by_id"
    MODIFY_WIKI_PAGE = "modify_wiki_page"
    RENAME_WIKI_PAGE = "rename_wiki_page"
    CREATE_WIKI_PAGE = "create_wiki_page"
    GET_WIKI_PAGE_COMMENTS_BY_ID = "get_wiki_page_comments_by_id"
    GET_WIKI_PAGE_COMMENTS_BY_PATH = "get_wiki_page_comments_by_path"
    ADD_WIKI_ATTACHMENT = "add_attachment_to_wiki_page"
    MOVE_WIKI_PAGE = "move_wiki_page"
    GET_WIKI_PAGE_STATS_BY_ID = "get_wiki_page_stats_by_id"
    GET_WIKI_PAGE_STATS_BY_PATH = "get_wiki_page_stats_by_path"
    LIST_WIKIS = "list_wikis"
    LIST_PAGES = "list_pages"
    SEARCH_WIKI_PAGES = "search_wiki_pages"
    ADD_WIKI_COMMENT_BY_ID = "add_wiki_comment_by_id"
    ADD_WIKI_COMMENT_BY_PATH = "add_wiki_comment_by_path"


class XWikiTool(str, Enum):
    """Enum for xWiki tool names."""

    LIST_WIKIS = "xwiki_list_wikis"
    GET_WIKI = "xwiki_get_wiki"
    LIST_SPACES = "xwiki_list_spaces"
    GET_SPACE = "xwiki_get_space"
    LIST_PAGES = "xwiki_list_pages"
    LIST_WIKI_PAGES = "xwiki_list_wiki_pages"
    LIST_PAGE_CHILDREN = "xwiki_list_page_children"
    GET_PAGE = "xwiki_get_page"
    CREATE_PAGE = "xwiki_create_page"
    MODIFY_PAGE = "xwiki_modify_page"
    DELETE_PAGE = "xwiki_delete_page"
    LIST_WIKI_TAGS = "xwiki_list_wiki_tags"
    LIST_PAGE_TAGS = "xwiki_list_page_tags"
    SET_PAGE_TAGS = "xwiki_set_page_tags"
    LIST_PAGE_COMMENTS = "xwiki_list_page_comments"
    GET_PAGE_COMMENT = "xwiki_get_page_comment"
    CREATE_PAGE_COMMENT = "xwiki_create_page_comment"
    LIST_PAGE_ATTACHMENTS = "xwiki_list_page_attachments"
    GET_PAGE_ATTACHMENT = "xwiki_get_page_attachment"
    READ_PAGE_ATTACHMENT_CONTENT = "xwiki_read_attachment_content"
    CREATE_PAGE_ATTACHMENT = "xwiki_create_page_attachment"
    DELETE_PAGE_ATTACHMENT = "xwiki_delete_page_attachment"
    SEARCH_WIKI = "xwiki_search_wiki"
    SEARCH_SPACE = "xwiki_search_space"


class AzureDevOpsTestPlanTool(str, Enum):
    """Enum for Azure DevOps Test Plan tool names."""

    CREATE_TEST_PLAN = "create_test_plan"
    DELETE_TEST_PLAN = "delete_test_plan"
    GET_TEST_PLAN = "get_test_plan"
    CREATE_TEST_SUITE = "create_test_suite"
    DELETE_TEST_SUITE = "delete_test_suite"
    GET_TEST_SUITE = "get_test_suite"
    ADD_TEST_CASE = "add_test_case"
    GET_TEST_CASE = "get_test_case"
    GET_TEST_CASES = "get_test_cases"


class AzureDevOpsWorkItemTool(str, Enum):
    """Enum for Azure DevOps Work Item tool names."""

    GET_WORK_ITEM = "get_work_item"
    GET_COMMENTS = "get_comments"
    GET_RELATION_TYPES = "get_relation_types"
    SEARCH_WORK_ITEMS = "search_work_items"
    CREATE_WORK_ITEM = "create_work_item"
    UPDATE_WORK_ITEM = "update_work_item"
    LINK_WORK_ITEMS = "link_work_items"
    REMOVE_WORK_ITEM_RELATION = "remove_work_item_relation"
    MOVE_WORK_ITEM = "move_work_item"
    CREATE_COMMENT = "create_comment"
    GET_WORK_ITEM_ATTACHMENT_CONTENT = "get_work_item_attachment_content"


class ResearchToolName(str, Enum):
    """Enum for Research tool names."""

    GOOGLE_SEARCH = "google_search_tool_json"
    GOOGLE_PLACES = "google_places"
    GOOGLE_PLACES_FIND_NEAR = "google_places_find_near"
    WIKIPEDIA = "wikipedia"
    TAVILY_SEARCH = "tavily_search_results_json"
    WEB_SCRAPPER = "web_scrapper"


class NotificationTool(str, Enum):
    """Enum for Notification tool names."""

    EMAIL = "Email"
    TELEGRAM = "Telegram"


class ProjectManagementTool(str, Enum):
    """Enum for Project Management tool names."""

    JIRA = "generic_jira_tool"
    CONFLUENCE = "generic_confluence_tool"


class FileManagementTool(str, Enum):
    """Enum for File Management tool names."""

    READ_FILE = "read_file_from_file_system"
    WRITE_FILE = "write_file_to_file_system"
    LIST_DIRECTORY = "list_directory_from_file_system"
    RUN_COMMAND_LINE = "run_command_line_tool"
    CODE_EXECUTOR = "code_executor"
    GENERATE_IMAGE = "generate_image_tool"
    DIFF_UPDATE = "diff_update_file_tool"
    FILESYSTEM_EDITOR = "str_replace_editor"


class OpenApiTool(str, Enum):
    """Enum for Open API tool names."""

    INVOKE_EXTERNAL_API = "open_api"
    GET_OPEN_API_SPEC = "open_api_spec"


class DataManagementTool(str, Enum):
    """Enum for Data Management tool names."""

    ELASTIC = "elastic"
    SQL = "sql"


class ServiceNowTool(str, Enum):
    """Enum for ServiceNow tool names."""

    SERVICE_NOW = "servicenow_table_tool"


class AccessManagementTool(str, Enum):
    """Enum for Access Management tool names."""

    KEYCLOAK = "keycloak"


class ReportPortalTool(str, Enum):
    """Enum for Report Portal tool names."""

    GET_EXTENDED_LAUNCH_DATA_AS_RAW = "get_extended_launch_data_as_raw"
    GET_LAUNCH_DETAILS = "get_launch_details"
    GET_ALL_LAUNCHES = "get_all_launches"
    FIND_TEST_ITEM_BY_ID = "find_test_item_by_id"
    GET_TEST_ITEMS_FOR_LAUNCH = "get_test_items_for_launch"
    GET_LOGS_FOR_TEST_ITEM = "get_logs_for_test_item"
    GET_USER_INFORMATION = "get_user_information"
    GET_DASHBOARD_DATA = "get_dashboard_data"


class McpServerTime(str, Enum):
    """Enum for Time MCP Server tool names."""

    GET_CURRENT_TIME = "get_current_time"
    CONVERT_TIME = "convert_time"


class CliMcpServer(str, Enum):
    """Enum for Cli MCP Server tool names."""

    RUN_COMMAND = "run command"


class McpServerFetch(str, Enum):
    """Enum for MCP Server Fetch tool names."""

    FETCH = "fetch"


class McpServerSqlite(str, Enum):
    """Enum for SQLite MCP Server tool names."""

    LIST_TABLES = "list_tables"
    DESCRIBE_TABLE = "describe_table"
    READ_QUERY = "read_query"
    CREATE_TABLE = "create_table"
    WRITE_QUERY = "write_query"


class McpServerFilesystem(str, Enum):
    """Enum for Filesystem MCP Server tool names."""

    READ_FILE = "read_file"
    READ_TEXT_FILE = "read_text_file"
    READ_MEDIA_FILE = "read_media_file"
    READ_MULTIPLE_FILES = "read_multiple_files"
    WRITE_FILE = "write_file"
    EDIT_FILE = "edit_file"
    CREATE_DIRECTORY = "create_directory"
    LIST_DIRECTORY = "list_directory"
    LIST_DIRECTORY_WITH_SIZES = "list_directory_with_sizes"
    DIRECTORY_TREE = "directory_tree"
    MOVE_FILE = "move_file"
    SEARCH_FILES = "search_files"
    GET_FILE_INFO = "get_file_info"
    LIST_ALLOWED_DIRECTORIES = "list_allowed_directories"


class McpServerGit(str, Enum):
    """Enum for Git MCP Server tool names."""

    GIT_STATUS = "git_status"
    GIT_DIFF = "git_diff"
    GIT_DIFF_UNSTAGED = "git_diff_unstaged"
    GIT_DIFF_STAGED = "git_diff_staged"
    GIT_COMMIT = "git_commit"
    GIT_ADD = "git_add"
    GIT_RESET = "git_reset"
    GIT_LOG = "git_log"
    GIT_SHOW = "git_show"
    CREATE_BRANCH = "create_branch"
    CHECKOUT_BRANCH = "checkout_branch"
    LIST_BRANCHES = "list_branches"


class McpServerGithub(str, Enum):
    """Enum for GitHub MCP Server tool names."""

    CREATE_OR_UPDATE_FILE = "create_or_update_file"
    SEARCH_REPOSITORIES = "search_repositories"
    CREATE_REPOSITORY = "create_repository"
    GET_FILE_CONTENTS = "get_file_contents"
    PUSH_FILES = "push_files"
    CREATE_ISSUE = "create_issue"
    CREATE_PULL_REQUEST = "create_pull_request"
    FORK_REPOSITORY = "fork_repository"
    CREATE_BRANCH = "create_branch"
    LIST_COMMITS = "list_commits"
    LIST_ISSUES = "list_issues"
    UPDATE_ISSUE = "update_issue"
    ADD_ISSUE_COMMENT = "add_issue_comment"
    SEARCH_CODE = "search_code"
    SEARCH_ISSUES = "search_issues"
    SEARCH_USERS = "search_users"
    GET_ISSUE = "get_issue"
    GET_PULL_REQUEST = "get_pull_request"
    LIST_PULL_REQUESTS = "list_pull_requests"
    CREATE_PULL_REQUEST_REVIEW = "create_pull_request_review"
    MERGE_PULL_REQUEST = "merge_pull_request"
    GET_PULL_REQUEST_FILES = "get_pull_request_files"
    GET_PULL_REQUEST_STATUS = "get_pull_request_status"
    UPDATE_PULL_REQUEST_BRANCH = "update_pull_request_branch"
    GET_PULL_REQUEST_COMMENTS = "get_pull_request_comments"
    GET_PULL_REQUEST_REVIEWS = "get_pull_request_reviews"


class McpServerPostgresql(str, Enum):
    """Enum for PostgreSQL MCP Server tool names."""

    QUERY = "query"


class McpServerPlaywright(str, Enum):
    """Enum for Playwright MCP Server tool names."""

    BROWSER_NAVIGATE = "browser_navigate"
    BROWSER_SCREENSHOT = "browser_take_screenshot"


class McpServerPuppeteer(str, Enum):
    """Enum for Puppeteer MCP Server tool names."""

    PUPPETEER_NAVIGATE = "puppeteer_navigate"
    PUPPETEER_SCREENSHOT = "puppeteer_screenshot"
    PUPPETEER_CLICK = "puppeteer_click"
    PUPPETEER_FILL = "puppeteer_fill"
    PUPPETEER_SELECT = "puppeteer_select"
    PUPPETEER_HOVER = "puppeteer_hover"
    PUPPETEER_EVALUATE = "puppeteer_evaluate"


class BuiltinSubagentTool(str, Enum):
    """Enum for built-in subagent tool names."""

    GENERAL_PURPOSE_SUBAGENT = "GENERAL_PURPOSE_SUBAGENT"


class Default(str, Enum):
    """Enum for tools that attached automatically e.g. on added datasource or file uploaded."""

    GET_REPOSITORY_FILE_TREE = "get_repository_file_tree"
    SEARCH_KB = "search_kb"
    FILE_ANALYSIS = "file_analysis"
    DOCX_TOOL = "docx_tool"
    EXCEL_TOOL = "excel_tool"
    CSV_TOOL = "csv tool"
    PPTX_TOOL = "pptx_tool"
    PDF_TOOL = "pdf_tool"


class CodeExplorationTools(str, Enum):
    """Enum for CodeExplorationToolkit tool names — the AICE combined provider's
    tool surface.
    """

    SEARCH_SEMANTIC = "knowledge_graph_search_semantic"
    SEARCH_KEYWORD = "knowledge_graph_search_keyword"
    SEARCH_NODES_BY_NAME = "knowledge_graph_search_nodes_by_name"
    BROWSE_HIERARCHY = "knowledge_graph_browse_hierarchy"
    READ_NODE_CONTENT = "knowledge_graph_read_node_content"
    READ_NODE_SUMMARY = "knowledge_graph_read_node_summary"
    DESCRIBE_NODE = "knowledge_graph_describe_node"
    DESCRIBE_WORKSPACE = "knowledge_graph_describe_workspace"
    DESCRIBE_DATA_MODEL = "knowledge_graph_describe_data_model"
    TRACE_CALLS = "knowledge_graph_trace_calls"
    TRACE_DEPENDENCIES = "knowledge_graph_trace_dependencies"
    RUN_CYPHER = "knowledge_graph_run_cypher"
    RUN_PYTHON = "knowledge_graph_run_python"
    READ_RESOURCE = "read_resource"


class AgentWorkspaceTool(str, Enum):
    """Enum for Agent Workspace tool names."""

    LIST_WORKSPACE_FILES = "list_workspace_files"
    READ_WORKSPACE_FILE = "read_workspace_file"
    WRITE_WORKSPACE_FILE = "write_workspace_file"
    EDIT_WORKSPACE_FILE = "edit_workspace_file"
    DELETE_WORKSPACE_FILE = "delete_workspace_file"
    GREP_WORKSPACE_FILES = "grep_workspace_files"
    EXECUTE_WORKSPACE_SCRIPT = "execute_workspace_script"
    GENERATE_WORKSPACE_IMAGE = "generate_workspace_image_v2"
    INSPECT_WORKSPACE_IMAGE = "inspect_workspace_image"
