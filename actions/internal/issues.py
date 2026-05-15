"""Issue-domain Forgejo operations for bundled actions."""

from __future__ import annotations

from typing import Any

try:
    from .repo_scope import RepositoryScope
    from .tea_api import ApiError
except ImportError:
    from repo_scope import RepositoryScope
    from tea_api import ApiError


def edit_comment(repo: RepositoryScope, comment_id: int, body: str) -> Any:
    return repo.patch(f"issues/comments/{comment_id}", {"body": body})


def lock(repo: RepositoryScope, issue: int, reason: str = "resolved") -> None:
    repo.post(f"issues/{issue}/lock", {"lock_reason": reason})


def unlock(repo: RepositoryScope, issue: int) -> None:
    repo.delete(f"issues/{issue}/lock")


def pin(repo: RepositoryScope, issue: int) -> None:
    repo.post(f"issues/{issue}/pin", {})


def unpin(repo: RepositoryScope, issue: int) -> None:
    repo.delete(f"issues/{issue}/pin")


def add_reaction(repo: RepositoryScope, issue: int, reaction: str) -> Any:
    return repo.post(f"issues/{issue}/reactions", {"content": reaction})


def list_reactions(repo: RepositoryScope, issue: int) -> list[dict[str, Any]]:
    result = repo.get(f"issues/{issue}/reactions")
    return result if isinstance(result, list) else []


def add_dependency(repo: RepositoryScope, issue: int, depends_on: int) -> str:
    body = {"index": depends_on, "owner": repo.owner, "repo": repo.name}
    try:
        repo.post(f"issues/{issue}/dependencies", body)
    except ApiError as exc:
        if exc.status == 409:
            return "exists"
        raise
    return "added"


def remove_dependency(repo: RepositoryScope, issue: int, depends_on: int) -> None:
    body = {"index": depends_on, "owner": repo.owner, "repo": repo.name}
    repo.delete(f"issues/{issue}/dependencies", body)


def list_dependencies(repo: RepositoryScope, issue: int) -> list[dict[str, Any]]:
    result = repo.get(f"issues/{issue}/dependencies")
    return result if isinstance(result, list) else []


def list_open(repo: RepositoryScope) -> list[dict[str, Any]]:
    result = repo.get("issues", {"state": "open"})
    return result if isinstance(result, list) else []


def list_all(repo: RepositoryScope) -> list[dict[str, Any]]:
    result = repo.get("issues", {"state": "all"})
    return result if isinstance(result, list) else []


def all_dependencies(repo: RepositoryScope) -> list[tuple[int, list[dict[str, Any]]]]:
    rows: list[tuple[int, list[dict[str, Any]]]] = []
    for issue in list_open(repo):
        number = int(issue.get("number") or issue.get("index"))
        deps = list_dependencies(repo, number)
        if deps:
            rows.append((number, deps))
    return rows


def ready(repo: RepositoryScope) -> list[dict[str, Any]]:
    ready_issues: list[dict[str, Any]] = []
    for issue in list_open(repo):
        number = int(issue.get("number") or issue.get("index"))
        deps = list_dependencies(repo, number)
        open_blockers = [dep for dep in deps if dep.get("state") == "open"]
        if not open_blockers:
            ready_issues.append(issue)
    return ready_issues


def dependency_graph_edges(repo: RepositoryScope) -> list[tuple[int, int]]:
    edges: list[tuple[int, int]] = []
    for issue in list_all(repo):
        number = int(issue.get("number") or issue.get("index"))
        for dep in list_dependencies(repo, number):
            dep_number = dep.get("number") or dep.get("index")
            if dep_number is not None:
                edges.append((number, int(dep_number)))
    return edges
