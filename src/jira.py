import os
from typing import Any

import httpx


DEFAULT_TIMEOUT_SECONDS = 20.0
MAX_SEARCH_RESULTS = 100
MAX_COMMENTS = 100

DEFAULT_ISSUE_FIELDS = [
    "summary",
    "description",
    "status",
    "issuetype",
    "priority",
    "assignee",
    "reporter",
    "labels",
    "components",
    "fixVersions",
    "parent",
    "subtasks",
    "created",
    "updated",
]


def _get_jira_settings() -> tuple[str, str, str]:
    """Read Jira connection settings from environment variables."""
    base_url = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
    email = os.environ.get("JIRA_EMAIL", "")
    api_token = os.environ.get("JIRA_API_TOKEN", "")

    missing = [
        name
        for name, value in (
            ("JIRA_BASE_URL", base_url),
            ("JIRA_EMAIL", email),
            ("JIRA_API_TOKEN", api_token),
        )
        if not value
    ]

    if missing:
        raise ValueError(
            "Missing Jira environment variable(s): "
            + ", ".join(missing)
        )

    return base_url, email, api_token


def _jira_client() -> httpx.Client:
    """Create an authenticated Jira Cloud REST API client."""
    base_url, email, api_token = _get_jira_settings()

    return httpx.Client(
        base_url=base_url,
        auth=(email, api_token),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout=DEFAULT_TIMEOUT_SECONDS,
        follow_redirects=True,
    )


def _raise_for_jira_error(response: httpx.Response) -> None:
    """Raise a concise error that includes Jira's response body when useful."""
    if response.is_success:
        return

    detail = response.text.strip()

    if len(detail) > 2000:
        detail = detail[:2000] + "... [truncated]"

    raise RuntimeError(
        f"Jira API request failed with HTTP {response.status_code}: "
        f"{detail or response.reason_phrase}"
    )


def _adf_to_text(value: Any) -> str:
    """
    Convert Jira Atlassian Document Format (ADF) into readable plain text.
    """
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, list):
        return "".join(_adf_to_text(item) for item in value)

    if not isinstance(value, dict):
        return str(value)

    node_type = value.get("type")
    text = value.get("text", "")
    content = value.get("content", [])

    if node_type == "text":
        return text

    if node_type == "hardBreak":
        return "\n"

    rendered = "".join(_adf_to_text(item) for item in content)

    if node_type in {
        "paragraph",
        "heading",
        "blockquote",
        "codeBlock",
        "listItem",
    }:
        return rendered.rstrip() + "\n"

    return rendered


def _user_summary(user: Any) -> dict[str, Any] | None:
    if not isinstance(user, dict):
        return None

    return {
        "account_id": user.get("accountId"),
        "display_name": user.get("displayName"),
        "email_address": user.get("emailAddress"),
        "active": user.get("active"),
    }


def _named_items(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []

    names: list[str] = []

    for item in items:
        if not isinstance(item, dict):
            continue

        name = item.get("name")

        if isinstance(name, str):
            names.append(name)

    return names


def _issue_summary(issue: dict[str, Any]) -> dict[str, Any]:
    fields = issue.get("fields") or {}

    status = fields.get("status") or {}
    issue_type = fields.get("issuetype") or {}
    priority = fields.get("priority") or {}
    parent = fields.get("parent") or {}

    subtasks = []
    for subtask in fields.get("subtasks") or []:
        if not isinstance(subtask, dict):
            continue

        subtask_fields = subtask.get("fields") or {}
        subtask_status = subtask_fields.get("status") or {}

        subtasks.append(
            {
                "key": subtask.get("key"),
                "summary": subtask_fields.get("summary"),
                "status": subtask_status.get("name"),
            }
        )

    return {
        "id": issue.get("id"),
        "key": issue.get("key"),
        "summary": fields.get("summary"),
        "description": _adf_to_text(fields.get("description")).strip(),
        "status": status.get("name"),
        "issue_type": issue_type.get("name"),
        "priority": priority.get("name"),
        "assignee": _user_summary(fields.get("assignee")),
        "reporter": _user_summary(fields.get("reporter")),
        "labels": fields.get("labels") or [],
        "components": _named_items(fields.get("components")),
        "fix_versions": _named_items(fields.get("fixVersions")),
        "parent": (
            {
                "key": parent.get("key"),
                "summary": (parent.get("fields") or {}).get("summary"),
            }
            if parent
            else None
        ),
        "subtasks": subtasks,
        "created": fields.get("created"),
        "updated": fields.get("updated"),
    }


def get_jira_issue_data(issue_key: str) -> dict[str, Any]:
    """Fetch one Jira issue by key or ID."""
    if not issue_key.strip():
        raise ValueError("issue_key must not be empty")

    with _jira_client() as client:
        response = client.get(
            f"/rest/api/3/issue/{issue_key.strip()}",
            params={"fields": ",".join(DEFAULT_ISSUE_FIELDS)},
        )

    _raise_for_jira_error(response)
    return _issue_summary(response.json())


def search_jira_data(
    jql: str,
    max_results: int = 25,
) -> dict[str, Any]:
    """Search Jira using JQL enhanced search."""
    if not jql.strip():
        raise ValueError("jql must not be empty")

    if max_results < 1 or max_results > MAX_SEARCH_RESULTS:
        raise ValueError(
            f"max_results must be between 1 and {MAX_SEARCH_RESULTS}"
        )

    with _jira_client() as client:
        response = client.post(
            "/rest/api/3/search/jql",
            json={
                "jql": jql,
                "maxResults": max_results,
                "fields": DEFAULT_ISSUE_FIELDS,
            },
        )

    _raise_for_jira_error(response)

    payload = response.json()
    issues = payload.get("issues") or []

    return {
        "jql": jql,
        "returned": len(issues),
        "is_last": payload.get("isLast"),
        "next_page_token": payload.get("nextPageToken"),
        "issues": [
            _issue_summary(issue)
            for issue in issues
            if isinstance(issue, dict)
        ],
    }


def get_jira_issue_comments_data(
    issue_key: str,
    max_results: int = 50,
) -> dict[str, Any]:
    """Fetch comments for one Jira issue."""
    if not issue_key.strip():
        raise ValueError("issue_key must not be empty")

    if max_results < 1 or max_results > MAX_COMMENTS:
        raise ValueError(
            f"max_results must be between 1 and {MAX_COMMENTS}"
        )

    with _jira_client() as client:
        response = client.get(
            f"/rest/api/3/issue/{issue_key.strip()}/comment",
            params={
                "startAt": 0,
                "maxResults": max_results,
                "orderBy": "created",
            },
        )

    _raise_for_jira_error(response)

    payload = response.json()
    comments = []

    for comment in payload.get("comments") or []:
        if not isinstance(comment, dict):
            continue

        comments.append(
            {
                "id": comment.get("id"),
                "author": _user_summary(comment.get("author")),
                "created": comment.get("created"),
                "updated": comment.get("updated"),
                "body": _adf_to_text(comment.get("body")).strip(),
            }
        )

    return {
        "issue_key": issue_key,
        "start_at": payload.get("startAt"),
        "max_results": payload.get("maxResults"),
        "total": payload.get("total"),
        "returned": len(comments),
        "comments": comments,
    }
