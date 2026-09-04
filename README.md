# Multi-Repository MCP Server

A developer-focused [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that helps AI coding agents safely explore and understand projects spread across multiple repositories.

The server provides structured, read-only access to source code, Git history, repository state, Jira context, and explicitly allowlisted verification commands.

It is designed to give AI coding tools useful project context without giving them unrestricted shell access or requiring repositories to be combined into a single workspace.

## Features

### Multi-repository support

Configure multiple local Git repositories and access them through short aliases.

```yaml
repositories:
  backend:
    path: ../my-backend

  frontend:
    path: ../my-frontend
```

The MCP server can then inspect and reason across those repositories as one project.

### Code search

Search across one repository or all configured repositories.

Useful for:

- finding symbols and references
- tracing functionality across services
- investigating shared concepts
- locating configuration and tests

Search results are bounded to prevent unnecessarily large responses.

### Safe file inspection

Read source files through MCP tools with configurable limits.

Files can also be read from another Git branch, tag, or commit without checking out that ref or modifying the working tree.

### Git inspection

Read-only Git tools provide access to information such as:

- repository status
- changed files
- local and remote-tracking branches
- commit history
- individual commits
- branch comparisons
- working-tree diff summaries
- bounded file diffs
- files stored at another Git ref

This makes it possible for an AI agent to investigate work across branches without switching branches or modifying the repository.

### Jira integration

Optional read-only Jira integration allows the agent to retrieve project context directly from Jira.

Supported operations include:

- retrieving an issue
- searching issues with JQL
- reading issue comments

Credentials are loaded from environment variables and are never stored in repository configuration.

### Allowlisted verification

Repositories can define explicitly permitted verification commands.

For example:

```yaml
repositories:
  backend:
    path: ../my-backend

    verification:
      tests:
        - uv
        - run
        - pytest
```

Only configured commands can be executed through the verification tool.

This allows an agent to run known-safe checks without exposing a general-purpose shell tool.

## Safety model

The server is intentionally designed around bounded and mostly read-only operations.

Repository tools can inspect source code and Git state, but they do not provide operations for:

- committing
- pushing
- merging
- deleting branches
- deploying
- modifying databases
- executing arbitrary shell commands

Verification commands must be explicitly configured per repository.

File paths are resolved against configured repository roots to prevent access outside those repositories.

## Project structure

```text
multi-repo-mcp/
├── .env.example
├── .gitignore
├── repositories.example.yaml
├── pyproject.toml
├── server.py
├── uv.lock
└── src/
    ├── __init__.py
    ├── config.py
    ├── files.py
    ├── git.py
    ├── jira.py
    ├── repositories.py
    ├── search.py
    ├── tools.py
    └── verification.py
```

## Requirements

- Python 3.12+
- Git
- [uv](https://docs.astral.sh/uv/)
- [ripgrep](https://github.com/BurntSushi/ripgrep) for code search

Jira integration additionally requires access to a Jira instance and an API token.

## Installation

Clone the repository:

```bash
git clone https://github.com/csillaposa/multi-repo-mcp.git
cd YOUR_REPOSITORY
```

Install the dependencies:

```bash
uv sync
```

## Repository configuration

Copy the example configuration:

```bash
cp repositories.example.yaml repositories.yaml
```

On PowerShell:

```powershell
Copy-Item repositories.example.yaml repositories.yaml
```

Then configure your local repositories:

```yaml
repositories:
  backend:
    path: ../my-backend
    enabled: true

  frontend:
    path: ../my-frontend
    enabled: true
```

`repositories.yaml` is intentionally ignored by Git so local repository paths and project-specific configuration are not committed.

## Jira configuration

Jira support is optional.

Copy the example environment file:

```bash
cp .env.example .env
```

On PowerShell:

```powershell
Copy-Item .env.example .env
```

Configure:

```text
JIRA_BASE_URL=https://your-company.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token
```

`.env` is ignored by Git.

Never commit Jira API tokens or other credentials.

## Running the server

Start the MCP server directly:

```bash
uv run python server.py
```

For development and inspection with the MCP development tools:

```bash
uv run mcp dev server.py
```

## Using with Codex

The server can be registered as a local MCP server with Codex.

For example:

```powershell
codex mcp add multi-repo-mcp -- uv --directory C:\path\to\multi-repo-mcp run python server.py
```

Verify the registration:

```powershell
codex mcp list
```

Once connected, Codex can use the MCP tools to retrieve repository and Jira context during coding and investigation tasks.

## Example use cases

The server is particularly useful for tasks such as:

- investigating behavior spread across multiple repositories
- comparing implementations between branches
- tracing an API contract across services
- reviewing changes without checking out another branch
- combining Jira requirements with source-code investigation
- understanding an unfamiliar project
- performing cross-repository architecture reviews
- gathering focused context before making a code change

The goal is not to replace Git, Jira, or normal development tools.

Instead, the MCP server provides a controlled interface through which an AI coding agent can retrieve the context it needs.

## Development status

This project is under active development.

The current focus is on improving safe, efficient project exploration for AI-assisted software development while keeping repository access explicit and bounded.
