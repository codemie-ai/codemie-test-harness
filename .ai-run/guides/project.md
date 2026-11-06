# Project Context

## Project Identity

| Field | Value | Source |
|---|---|---|
| Project name | codemie-test-harness | pyproject.toml::tool.poetry.name |
| Repository/package | codemie-ai/codemie-test-harness | .github/workflows/publish.yml::codemie-test-harness |
| Project code/key | none | user decision |

## Work Item Tracker

| Field | Value |
|---|---|
| Provider | Jira |
| Key/prefix | EPMCDME |

## Ticket Adapter

**Status**: configured
**Adapter**: skill codemie-jira-assistant
**Lookup**: invoke skill codemie-jira-assistant: get issue <KEY>
**Create**: invoke skill codemie-jira-assistant: create issue in EPMCDME
**Output**: skill reply with the issue summary, description and acceptance criteria
**Comment**: invoke skill codemie-jira-assistant: add comment to <KEY>

## Source Control And Review

| Field | Value |
|---|---|
| Provider | GitHub |
| Repository remote | https://github.com/codemie-ai/codemie-test-harness.git |
| Default target branch | main |
| Review artifact type | PR |

## MR Adapter

**Status**: configured
**Adapter**: gh CLI
**Instructions**: Push the branch to the fork and open the pull request against main of codemie-ai/codemie-test-harness with gh (CONTRIBUTING.md steps 1-5)

## Complexity Scoring

**Status**: not configured
**Field**: not configured
**Format**: not configured
