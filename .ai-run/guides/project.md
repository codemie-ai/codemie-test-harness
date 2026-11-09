# Project Context

## Project Identity

| Field | Value | Source |
|---|---|---|
| Project name | CodeMie Test Harness | `README.md` |
| Repository/package | codemie-ai/codemie-test-harness; PyPI package `codemie-test-harness` | `CONTRIBUTING.md`, `pyproject.toml` |
| Project code/key | `EPMCDME-NNNNN` (placeholder form) | user decision |

## Machine-readable twin

[testing/config.json](testing/config.json) holds the same facts for tools: disciplines, adapters, `git_conventions`, `test_command_templates` and `code_repos`. The `sdk` entry describes the public SDK repository. Its `local_path` is the directory name of a clone of that repository next to this one, and its `setup` and `verify` commands run from the root of that clone. The `consume.*` commands run from this repository. `test_command_templates` is a known copy of the commands in `testing/qa-strategy.md`; the strategy file is the home.

## Work Item Tracker

| Field | Value |
|---|---|
| Provider | Jira |
| Key/prefix | `EPMCDME-NNNNN` (placeholder) |

> Adapter configuration belongs exclusively in `## Ticket Adapter`. Do not duplicate adapter status or instructions in the Work Item Tracker table.

The repository is public. Never write a real ticket key, a tracker host or a personal e-mail in a tracked file. This file is the only place where the placeholder form appears.

## Ticket Adapter

**Status**: configured
**Adapter**: Invoke the `codemie-jira-assistant` skill via the Skill tool.
**Lookup**: Invoke the `codemie-jira-assistant` skill with the ticket key and a request for summary, description, acceptance criteria, and links.
**Create**: Invoke the `codemie-jira-assistant` skill with the complete ticket payload or approved story file as the argument.
**Output**: Ticket key and URL returned by the skill.
**Comment**: Invoke the `codemie-jira-assistant` skill with a request to add a comment to the ticket, passing the comment body as the argument.

## Source Control And Review

| Field | Value |
|---|---|
| Provider | GitHub |
| Repository remote | `https://github.com/codemie-ai/codemie-test-harness.git` |
| Default target branch | main |
| Review artifact type | PR |

## MR Adapter

**Status**: configured
**Adapter**: `gh` CLI
**Instructions**: Use `gh pr create --repo codemie-ai/codemie-test-harness --base main`. Read `gh pr view` and `gh pr checks` for status. Load `standards/git-workflow.md` for the title format and the rule on ticket keys.

## Complexity Scoring

**Status**: not configured
**Field**: not configured
**Format**: not configured
