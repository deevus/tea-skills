"""Milestone-domain Forgejo operations for bundled actions."""

from __future__ import annotations

from typing import Any

try:
    from .repo_scope import RepositoryScope
    from .tea_api import ApiError
except ImportError:
    from repo_scope import RepositoryScope
    from tea_api import ApiError


def find_id_by_name(repo: RepositoryScope, name: str) -> int:
    result = repo.get("milestones", {"name": name})
    if not isinstance(result, list) or not result:
        raise ApiError("GET", repo.url("milestones", {"name": name}), 404, f"Milestone '{name}' not found")
    milestone_id = result[0].get("id")
    if milestone_id is None:
        raise ApiError("GET", repo.url("milestones", {"name": name}), 404, f"Milestone '{name}' has no id")
    return int(milestone_id)


def edit(
    repo: RepositoryScope,
    name: str,
    title: str | None = None,
    due_date: str | None = None,
    description: str | None = None,
) -> Any:
    body: dict[str, Any] = {}
    if title is not None:
        body["title"] = title
    if due_date is not None:
        body["due_on"] = f"{due_date}T00:00:00Z"
    if description is not None:
        body["description"] = description
    if not body:
        raise ValueError("provide at least one milestone edit field")
    milestone_id = find_id_by_name(repo, name)
    return repo.patch(f"milestones/{milestone_id}", body)
