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

from pathlib import Path
from rich.console import Console

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}
CLI_NAME = "CodeMie Test Harness"
CONSOLE = Console()

CONFIG_DIR = Path.home() / ".codemie"
CONFIG_FILE = CONFIG_DIR / "test-harness.json"

# Keys (env and config)
KEY_AUTH_SERVER_URL = "AUTH_SERVER_URL"
KEY_AUTH_CLIENT_ID = "AUTH_CLIENT_ID"
KEY_AUTH_CLIENT_SECRET = "AUTH_CLIENT_SECRET"
KEY_AUTH_PASSWORD = "AUTH_PASSWORD"
KEY_AUTH_USERNAME = "AUTH_USERNAME"
KEY_AUTH_REALM_NAME = "AUTH_REALM_NAME"
KEY_CODEMIE_API_DOMAIN = "CODEMIE_API_DOMAIN"
KEY_MARKS = "PYTEST_MARKS"
KEY_XDIST_N = "PYTEST_N"
KEY_RERUNS = "PYTEST_RERUNS"
KEY_COUNT = "PYTEST_COUNT"
KEY_TIMEOUT = "TEST_TIMEOUT"

# === COMPLETE INTEGRATION CREDENTIALS KEYS ===
# Version Control Systems (GitLab, GitHub)
KEY_GIT_ENV = "GIT_ENV"  # e.g. gitlab or github
# GitLab
KEY_GITLAB_URL = "GITLAB_URL"
KEY_GITLAB_TOKEN = "GITLAB_TOKEN"
KEY_GITLAB_PROJECT = "GITLAB_PROJECT"
KEY_GITLAB_PROJECT_ID = "GITLAB_PROJECT_ID"
# GitHub
KEY_GITHUB_URL = "GITHUB_URL"
KEY_GITHUB_TOKEN = "GITHUB_TOKEN"
KEY_GITHUB_PROJECT = "GITHUB_PROJECT"

# Project Management (JIRA, Confluence)
# JIRA Server
KEY_JIRA_URL = "JIRA_URL"
KEY_JIRA_TOKEN = "JIRA_TOKEN"
# JIRA Cloud
KEY_JIRA_CLOUD_URL = "JIRA_CLOUD_URL"
KEY_JIRA_CLOUD_EMAIL = "JIRA_CLOUD_EMAIL"
KEY_JIRA_CLOUD_TOKEN = "JIRA_CLOUD_TOKEN"
# Confluence Server
KEY_CONFLUENCE_URL = "CONFLUENCE_URL"
KEY_CONFLUENCE_TOKEN = "CONFLUENCE_TOKEN"
# Confluence Cloud
KEY_CONFLUENCE_CLOUD_URL = "CONFLUENCE_CLOUD_URL"
KEY_CONFLUENCE_CLOUD_EMAIL = "CONFLUENCE_CLOUD_EMAIL"
KEY_CONFLUENCE_CLOUD_TOKEN = "CONFLUENCE_CLOUD_TOKEN"
# xWiki
KEY_XWIKI_URL = "XWIKI_URL"
KEY_XWIKI_TOKEN = "XWIKI_TOKEN"
KEY_XWIKI_SPACE = "XWIKI_SPACE"

# Cloud Providers (AWS, Azure, GCP)
# AWS
KEY_AWS_ACCESS_KEY = "AWS_ACCESS_KEY"
KEY_AWS_SECRET_KEY = "AWS_SECRET_KEY"
KEY_AWS_ACCESS_KEY_ID = "AWS_ACCESS_KEY_ID"
KEY_AWS_SECRET_ACCESS_KEY = "AWS_SECRET_ACCESS_KEY"
KEY_AWS_REGION = "AWS_REGION"
KEY_AWS_SESSION_TOKEN = "AWS_SESSION_TOKEN"
KEY_AWS_PROFILE = "AWS_PROFILE"
# Azure
KEY_AZURE_CLIENT_ID = "AZURE_CLIENT_ID"
KEY_AZURE_CLIENT_SECRET = "AZURE_CLIENT_SECRET"
KEY_AZURE_TENANT_ID = "AZURE_TENANT_ID"
KEY_AZURE_SUBSCRIPTION_ID = "AZURE_SUBSCRIPTION_ID"
# GCP
KEY_GCP_SA_KEY_BASE64 = "GCP_SA_KEY_BASE64"

# Development Tools (Azure DevOps, ServiceNow, Keycloak, SonarQube)
# Azure DevOps
KEY_AZURE_DEVOPS_URL = "AZURE_DEVOPS_URL"
KEY_AZURE_DEVOPS_TOKEN = "AZURE_DEVOPS_TOKEN"
KEY_AZURE_DEVOPS_PROJECT_NAME = "AZURE_DEVOPS_PROJECT_NAME"
KEY_AZURE_DEVOPS_ORGANIZATION_NAME = "AZURE_DEVOPS_ORGANIZATION_NAME"
KEY_AZURE_DEVOPS_WIKI_NAME = "AZURE_DEVOPS_WIKI_NAME"
KEY_AZURE_DEVOPS_WORK_ITEMS_WIQL = "AZURE_DEVOPS_WORK_ITEMS_WIQL"
# ServiceNow
KEY_SERVICENOW_URL = "SERVICENOW_URL"
KEY_SERVICENOW_TOKEN = "SERVICENOW_TOKEN"
# Keycloak
KEY_KEYCLOAK_URL = "KEYCLOAK_URL"
KEY_KEYCLOAK_REALM = "KEYCLOAK_REALM"
KEY_KEYCLOAK_CLIENT_ID = "KEYCLOAK_CLIENT_ID"
KEY_KEYCLOAK_CLIENT_SECRET = "KEYCLOAK_CLIENT_SECRET"
# SonarQube Server
KEY_SONAR_URL = "SONAR_URL"
KEY_SONAR_TOKEN = "SONAR_TOKEN"
KEY_SONAR_PROJECT_KEY = "SONAR_PROJECT_KEY"
# SonarCloud
KEY_SONAR_CLOUD_URL = "SONAR_CLOUD_URL"
KEY_SONAR_CLOUD_TOKEN = "SONAR_CLOUD_TOKEN"
KEY_SONAR_CLOUD_PROJECT_KEY = "SONAR_CLOUD_PROJECT_KEY"

# Notifications (Email/Gmail, OAuth, Telegram)
# Email/Gmail
KEY_GMAIL_URL = "GMAIL_URL"
KEY_GMAIL_USER_EMAIL = "GMAIL_USER_EMAIL"
KEY_GMAIL_PASSWORD = "GMAIL_PASSWORD"
# OAuth
KEY_OAUTH_URL = "OAUTH_URL"
KEY_OAUTH_CLIENT_ID = "OAUTH_CLIENT_ID"
KEY_OAUTH_CLIENT_SECRET = "OAUTH_CLIENT_SECRET"
KEY_OAUTH_REFRESH_TOKEN = "OAUTH_REFRESH_TOKEN"
# Telegram
KEY_TELEGRAM_TOKEN = "TELEGRAM_TOKEN"
KEY_TELEGRAM_CHAT_ID = "TELEGRAM_CHAT_ID"

# Research Tools (Kubernetes, Report Portal, Elasticsearch)
# Kubernetes
KEY_KUBERNETES_URL = "KUBERNETES_URL"
KEY_KUBERNETES_TOKEN = "KUBERNETES_TOKEN"
# Report Portal
KEY_REPORT_PORTAL_URL = "REPORT_PORTAL_URL"
KEY_REPORT_PORTAL_API_KEY = "REPORT_PORTAL_API_KEY"
KEY_REPORT_PORTAL_PROJECT = "REPORT_PORTAL_PROJECT"
# Elasticsearch
KEY_ELASTICSEARCH_URL = "ELASTICSEARCH_URL"
KEY_ELASTICSEARCH_API_KEY_ID = "ELASTICSEARCH_API_KEY_ID"
KEY_ELASTICSEARCH_API_KEY = "ELASTICSEARCH_API_KEY"

# Data Management (SQL databases, LiteLLM)
# LiteLLM
KEY_LITE_LLM_API_KEY = "LITE_LLM_API_KEY"
# MySQL
KEY_MYSQL_DIALECT = "MYSQL_DIALECT"
KEY_MYSQL_URL = "MYSQL_URL"
KEY_MYSQL_PORT = "MYSQL_PORT"
KEY_MYSQL_DATABASE_NAME = "MYSQL_DATABASE_NAME"
KEY_MYSQL_USERNAME = "MYSQL_USERNAME"
KEY_MYSQL_PASSWORD = "MYSQL_PASSWORD"
# PostgreSQL
KEY_POSTGRES_DIALECT = "POSTGRES_DIALECT"
KEY_POSTGRES_URL = "POSTGRES_URL"
KEY_POSTGRES_PORT = "POSTGRES_PORT"
KEY_POSTGRES_DATABASE_NAME = "POSTGRES_DATABASE_NAME"
KEY_POSTGRES_USERNAME = "POSTGRES_USERNAME"
KEY_POSTGRES_PASSWORD = "POSTGRES_PASSWORD"
# MSSQL
KEY_MSSQL_DIALECT = "SANDBOX_MSSQL_DIALECT"
KEY_MSSQL_URL = "SANDBOX_MSSQL_URL"
KEY_MSSQL_PORT = "SANDBOX_MSSQL_PORT"
KEY_MSSQL_DATABASE_NAME = "SANDBOX_MSSQL_DATABASE_NAME"
KEY_MSSQL_USERNAME = "SANDBOX_MSSQL_USERNAME"
KEY_MSSQL_PASSWORD = "SANDBOX_MSSQL_PASSWORD"

# Opt-in secret store (read by tests/utils/aws_parameters_store.py)
KEY_HARNESS_SECRET_STORE = "HARNESS_SECRET_STORE"
KEY_AWS_PS_REGION = "AWS_PS_REGION"
KEY_AWS_PS_PATH_PREFIX = "AWS_PS_PATH_PREFIX"
KEY_AWS_PS_ROLE_ARN = "AWS_PS_ROLE_ARN"
KEY_AWS_PS_DOTENV_PATH = "AWS_PS_DOTENV_PATH"

# Names used by earlier versions of `config`; still accepted and mapped to the current name.
KEY_ALIASES = {
    "SMTP_USERNAME": KEY_GMAIL_USER_EMAIL,
    "SMTP_PASSWORD": KEY_GMAIL_PASSWORD,
    "MSSQL_DIALECT": KEY_MSSQL_DIALECT,
    "MSSQL_URL": KEY_MSSQL_URL,
    "MSSQL_PORT": KEY_MSSQL_PORT,
    "MSSQL_DATABASE_NAME": KEY_MSSQL_DATABASE_NAME,
    "MSSQL_USERNAME": KEY_MSSQL_USERNAME,
    "MSSQL_PASSWORD": KEY_MSSQL_PASSWORD,
}

DEFAULT_MARKS = "smoke"
DEFAULT_XDIST_N = 8
DEFAULT_RERUNS = 2
DEFAULT_TIMEOUT = 300

# Test Suite Presets
# Each suite has: (marks_expression, workers, reruns, description)
TEST_SUITES = {
    "smoke": {
        "marks": "smoke",
        "workers": 8,
        "reruns": 2,
        "description": "All smoke tests (API + UI) for local development",
        "pytest_args": ["--ui-headless"],
    },
    "smoke-api": {
        "marks": "smoke and api",
        "workers": 8,
        "reruns": 2,
        "description": "API-only smoke tests - fast backend validation",
    },
    "smoke-ui": {
        "marks": "smoke and ui",
        "workers": 4,
        "reruns": 2,
        "description": "UI-only smoke tests - critical user paths",
        "pytest_args": ["--ui-headless"],
    },
    "sanity-ui": {
        "marks": "ui and sanity",
        "workers": 4,
        "reruns": 2,
        "description": "UI sanity suite - stable UI tests without external service credentials",
        "pytest_args": ["--ui-headless"],
    },
    "sanity-api": {
        "marks": "api and sanity",
        "workers": 8,
        "reruns": 2,
        "description": "API sanity suite - stable API tests without external service credentials",
    },
    "sanity": {
        "marks": "sanity",
        "workers": 8,
        "reruns": 2,
        "description": "Sanity check for DevOps CI/CD pipelines",
    },
    "api": {
        "marks": "api",
        "workers": 8,
        "reruns": 2,
        "description": "Full API regression suite",
    },
    "ui": {
        "marks": "ui",
        "workers": 4,
        "reruns": 2,
        "description": "Full UI regression suite with Playwright",
        "pytest_args": ["--ui-headless"],
    },
    "opensource": {
        "marks": "not enterprise and api",
        "workers": 8,
        "reruns": 2,
        "description": "API tests for non-enterprise (open-source) features",
    },
    "enterprise": {
        "marks": "enterprise and api",
        "workers": 8,
        "reruns": 2,
        "description": "API tests for enterprise-only features",
    },
    "codemie_claude": {
        "marks": "codemie_claude",
        "workers": 0,
        "reruns": 0,
        "description": "Tests for codemie-claude CLI with file creation",
    },
    "codemie_gemini": {
        "marks": "codemie_gemini",
        "workers": 0,
        "reruns": 0,
        "description": "Tests for codemie-gemini CLI with task execution and session metrics",
    },
    "budget": {
        "marks": "budget and api",
        "workers": 4,
        "reruns": 2,
        "description": "Budget and spending tests",
    },
}

AUTH_KEYS = [
    KEY_AUTH_SERVER_URL,
    KEY_AUTH_CLIENT_ID,
    KEY_AUTH_CLIENT_SECRET,
    KEY_AUTH_USERNAME,
    KEY_AUTH_PASSWORD,
    KEY_AUTH_REALM_NAME,
    KEY_CODEMIE_API_DOMAIN,
]

# === CREDENTIAL CATEGORIES ===
VERSION_CONTROL_KEYS = [
    KEY_GIT_ENV,
    KEY_GITLAB_URL,
    KEY_GITLAB_TOKEN,
    KEY_GITLAB_PROJECT,
    KEY_GITLAB_PROJECT_ID,
    KEY_GITHUB_URL,
    KEY_GITHUB_TOKEN,
    KEY_GITHUB_PROJECT,
]

PROJECT_MANAGEMENT_KEYS = [
    # JIRA Server
    KEY_JIRA_URL,
    KEY_JIRA_TOKEN,
    # JIRA Cloud
    KEY_JIRA_CLOUD_URL,
    KEY_JIRA_CLOUD_EMAIL,
    KEY_JIRA_CLOUD_TOKEN,
    # Confluence Server
    KEY_CONFLUENCE_URL,
    KEY_CONFLUENCE_TOKEN,
    # Confluence Cloud
    KEY_CONFLUENCE_CLOUD_URL,
    KEY_CONFLUENCE_CLOUD_EMAIL,
    KEY_CONFLUENCE_CLOUD_TOKEN,
    # xWiki
    KEY_XWIKI_URL,
    KEY_XWIKI_TOKEN,
    KEY_XWIKI_SPACE,
]

CLOUD_PROVIDERS_KEYS = [
    # AWS
    KEY_AWS_ACCESS_KEY,
    KEY_AWS_SECRET_KEY,
    KEY_AWS_ACCESS_KEY_ID,
    KEY_AWS_SECRET_ACCESS_KEY,
    KEY_AWS_REGION,
    KEY_AWS_SESSION_TOKEN,
    KEY_AWS_PROFILE,
    # Azure
    KEY_AZURE_CLIENT_ID,
    KEY_AZURE_CLIENT_SECRET,
    KEY_AZURE_TENANT_ID,
    KEY_AZURE_SUBSCRIPTION_ID,
    # GCP
    KEY_GCP_SA_KEY_BASE64,
]

DEVELOPMENT_TOOLS_KEYS = [
    # Azure DevOps
    KEY_AZURE_DEVOPS_URL,
    KEY_AZURE_DEVOPS_TOKEN,
    KEY_AZURE_DEVOPS_PROJECT_NAME,
    KEY_AZURE_DEVOPS_ORGANIZATION_NAME,
    KEY_AZURE_DEVOPS_WIKI_NAME,
    KEY_AZURE_DEVOPS_WORK_ITEMS_WIQL,
    # ServiceNow
    KEY_SERVICENOW_URL,
    KEY_SERVICENOW_TOKEN,
    # Keycloak
    KEY_KEYCLOAK_URL,
    KEY_KEYCLOAK_REALM,
    KEY_KEYCLOAK_CLIENT_ID,
    KEY_KEYCLOAK_CLIENT_SECRET,
    # SonarQube Server
    KEY_SONAR_URL,
    KEY_SONAR_TOKEN,
    KEY_SONAR_PROJECT_KEY,
    # SonarCloud
    KEY_SONAR_CLOUD_URL,
    KEY_SONAR_CLOUD_TOKEN,
    KEY_SONAR_CLOUD_PROJECT_KEY,
]

NOTIFICATIONS_KEYS = [
    # Email/Gmail
    KEY_GMAIL_URL,
    KEY_GMAIL_USER_EMAIL,
    KEY_GMAIL_PASSWORD,
    # OAuth
    KEY_OAUTH_URL,
    KEY_OAUTH_CLIENT_ID,
    KEY_OAUTH_CLIENT_SECRET,
    KEY_OAUTH_REFRESH_TOKEN,
    # Telegram
    KEY_TELEGRAM_TOKEN,
    KEY_TELEGRAM_CHAT_ID,
]

RESEARCH_TOOLS_KEYS = [
    # Kubernetes
    KEY_KUBERNETES_URL,
    KEY_KUBERNETES_TOKEN,
    # Report Portal
    KEY_REPORT_PORTAL_URL,
    KEY_REPORT_PORTAL_API_KEY,
    KEY_REPORT_PORTAL_PROJECT,
    # Elasticsearch
    KEY_ELASTICSEARCH_URL,
    KEY_ELASTICSEARCH_API_KEY_ID,
    KEY_ELASTICSEARCH_API_KEY,
]

DATA_MANAGEMENT_KEYS = [
    # LiteLLM
    KEY_LITE_LLM_API_KEY,
    # MySQL
    KEY_MYSQL_DIALECT,
    KEY_MYSQL_URL,
    KEY_MYSQL_PORT,
    KEY_MYSQL_DATABASE_NAME,
    KEY_MYSQL_USERNAME,
    KEY_MYSQL_PASSWORD,
    # PostgreSQL
    KEY_POSTGRES_DIALECT,
    KEY_POSTGRES_URL,
    KEY_POSTGRES_PORT,
    KEY_POSTGRES_DATABASE_NAME,
    KEY_POSTGRES_USERNAME,
    KEY_POSTGRES_PASSWORD,
    # MSSQL
    KEY_MSSQL_DIALECT,
    KEY_MSSQL_URL,
    KEY_MSSQL_PORT,
    KEY_MSSQL_DATABASE_NAME,
    KEY_MSSQL_USERNAME,
    KEY_MSSQL_PASSWORD,
]

SECRET_STORE_KEYS = [
    KEY_HARNESS_SECRET_STORE,
    KEY_AWS_PS_REGION,
    KEY_AWS_PS_PATH_PREFIX,
    KEY_AWS_PS_ROLE_ARN,
    KEY_AWS_PS_DOTENV_PATH,
    # Store credentials, read only when the store is enabled
    KEY_AWS_ACCESS_KEY,
    KEY_AWS_SECRET_KEY,
    KEY_AWS_SESSION_TOKEN,
    KEY_AWS_PROFILE,
]

# Combined lists for backwards compatibility
INTEGRATION_KEYS = (
    VERSION_CONTROL_KEYS
    + PROJECT_MANAGEMENT_KEYS
    + CLOUD_PROVIDERS_KEYS
    + DEVELOPMENT_TOOLS_KEYS
    + NOTIFICATIONS_KEYS
    + RESEARCH_TOOLS_KEYS
    + DATA_MANAGEMENT_KEYS
    + SECRET_STORE_KEYS
)

# Category mapping for CLI
CREDENTIAL_CATEGORIES = {
    "version-control": {
        "name": "Version Control Systems",
        "description": "GitLab, GitHub, and other version control platforms",
        "keys": VERSION_CONTROL_KEYS,
    },
    "code-base": {
        "name": "Code Base",
        "description": "SonarQube and code analysis tools",
        "keys": [
            KEY_SONAR_URL,
            KEY_SONAR_TOKEN,
            KEY_SONAR_PROJECT_KEY,
            KEY_SONAR_CLOUD_URL,
            KEY_SONAR_CLOUD_TOKEN,
            KEY_SONAR_CLOUD_PROJECT_KEY,
        ],
    },
    "project-management": {
        "name": "Project Management",
        "description": "JIRA, Confluence, and project management tools",
        "keys": PROJECT_MANAGEMENT_KEYS,
    },
    "cloud": {
        "name": "Cloud",
        "description": "AWS, GCP cloud services and Kubernetes configurations",
        "keys": [
            # AWS
            KEY_AWS_ACCESS_KEY_ID,
            KEY_AWS_SECRET_ACCESS_KEY,
            KEY_AWS_REGION,
            KEY_AWS_SESSION_TOKEN,
            KEY_AWS_PROFILE,
            # GCP
            KEY_GCP_SA_KEY_BASE64,
            # Kubernetes
            KEY_KUBERNETES_URL,
            KEY_KUBERNETES_TOKEN,
            # Azure Cloud
            KEY_AZURE_CLIENT_ID,
            KEY_AZURE_CLIENT_SECRET,
            KEY_AZURE_TENANT_ID,
            KEY_AZURE_SUBSCRIPTION_ID,
        ],
    },
    "azure-devops": {
        "name": "Azure DevOps",
        "description": "Azure DevOps and Azure cloud platform services",
        "keys": [
            # Azure DevOps
            KEY_AZURE_DEVOPS_URL,
            KEY_AZURE_DEVOPS_TOKEN,
            KEY_AZURE_DEVOPS_PROJECT_NAME,
            KEY_AZURE_DEVOPS_ORGANIZATION_NAME,
            KEY_AZURE_DEVOPS_WIKI_NAME,
            KEY_AZURE_DEVOPS_WORK_ITEMS_WIQL,
        ],
    },
    "access-management": {
        "name": "Access Management",
        "description": "Keycloak and identity management systems",
        "keys": [
            KEY_KEYCLOAK_URL,
            KEY_KEYCLOAK_REALM,
            KEY_KEYCLOAK_CLIENT_ID,
            KEY_KEYCLOAK_CLIENT_SECRET,
        ],
    },
    "notification-systems": {
        "name": "Notification Systems",
        "description": "Email, OAuth, Telegram, and communication platforms",
        "keys": NOTIFICATIONS_KEYS,
    },
    "data-management": {
        "name": "Data Management",
        "description": "SQL databases, Elasticsearch, and data storage systems",
        "keys": DATA_MANAGEMENT_KEYS
        + [
            KEY_ELASTICSEARCH_URL,
            KEY_ELASTICSEARCH_API_KEY_ID,
            KEY_ELASTICSEARCH_API_KEY,
        ],
    },
    "it-service-management": {
        "name": "IT Service Management",
        "description": "ServiceNow and IT service management platforms",
        "keys": [
            KEY_SERVICENOW_URL,
            KEY_SERVICENOW_TOKEN,
        ],
    },
    "secret-store": {
        "name": "Secret Store",
        "description": "Opt-in AWS Parameter Store (HARNESS_SECRET_STORE=aws-parameter-store)",
        "keys": SECRET_STORE_KEYS,
    },
    "quality-assurance": {
        "name": "Quality Assurance",
        "description": "Report Portal and quality assurance tools",
        "keys": [
            KEY_REPORT_PORTAL_URL,
            KEY_REPORT_PORTAL_API_KEY,
            KEY_REPORT_PORTAL_PROJECT,
        ],
    },
}

# Sensitive fields that should be masked in input/output
SENSITIVE_KEYS = {
    KEY_AUTH_CLIENT_SECRET,
    KEY_AUTH_PASSWORD,
    KEY_GITLAB_TOKEN,
    KEY_GITHUB_TOKEN,
    KEY_JIRA_TOKEN,
    KEY_JIRA_CLOUD_TOKEN,
    KEY_CONFLUENCE_TOKEN,
    KEY_CONFLUENCE_CLOUD_TOKEN,
    KEY_XWIKI_TOKEN,
    KEY_AWS_SECRET_KEY,
    KEY_AWS_SECRET_ACCESS_KEY,
    KEY_AWS_SESSION_TOKEN,
    KEY_AZURE_CLIENT_SECRET,
    KEY_GCP_SA_KEY_BASE64,
    KEY_AZURE_DEVOPS_TOKEN,
    KEY_SERVICENOW_TOKEN,
    KEY_KEYCLOAK_CLIENT_SECRET,
    KEY_SONAR_TOKEN,
    KEY_SONAR_CLOUD_TOKEN,
    KEY_GMAIL_PASSWORD,
    KEY_OAUTH_CLIENT_SECRET,
    KEY_OAUTH_REFRESH_TOKEN,
    KEY_TELEGRAM_TOKEN,
    KEY_KUBERNETES_TOKEN,
    KEY_REPORT_PORTAL_API_KEY,
    KEY_ELASTICSEARCH_API_KEY,
    KEY_LITE_LLM_API_KEY,
    KEY_MYSQL_PASSWORD,
    KEY_POSTGRES_PASSWORD,
    KEY_MSSQL_PASSWORD,
}


def is_sensitive_key(key: str) -> bool:
    """Check if a credential key contains sensitive information."""
    return key in SENSITIVE_KEYS


def mask_sensitive_value(value: str, show_real: bool = False) -> str:
    """Mask sensitive credential values for display.

    Args:
        value: The value to potentially mask
        show_real: If True, return the real value instead of masking
    """
    if show_real:
        return value

    if not value or len(value) < 4:
        return "*" * len(value) if value else ""
    return value[:2] + "*" * (len(value) - 4) + value[-2:]
