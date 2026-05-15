"""Pull-request-domain Forgejo operations for bundled actions."""

from __future__ import annotations

from typing import Any, Mapping

try:
    from .repo_scope import RepositoryScope
except ImportError:
    from repo_scope import RepositoryScope


def find_by_branch(
    repo: RepositoryScope,
    head: str,
    base: str | None = None,
    state: str = "open",
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {"state": state}
    if base is not None:
        query["base_branch"] = base
    result = repo.get("pulls", query)
    pull_requests = result if isinstance(result, list) else []
    matches = [pull for pull in pull_requests if _head_matches(pull, head)]
    if base is not None:
        matches = [pull for pull in matches if _base_matches(pull, base)]
    return [_record(repo, pull) for pull in matches]


def _head_matches(pull: Mapping[str, Any], head: str) -> bool:
    pull_head = pull.get("head") if isinstance(pull.get("head"), Mapping) else {}
    if ":" in head:
        return pull_head.get("label") == head
    return pull_head.get("ref") == head


def _base_matches(pull: Mapping[str, Any], base: str) -> bool:
    pull_base = pull.get("base") if isinstance(pull.get("base"), Mapping) else {}
    if pull_base.get("ref") == base:
        return True
    label = pull_base.get("label")
    return isinstance(label, str) and label.split(":", 1)[-1] == base


def _record(repo: RepositoryScope, pull: Mapping[str, Any]) -> dict[str, Any]:
    head = pull.get("head") if isinstance(pull.get("head"), Mapping) else {}
    base = pull.get("base") if isinstance(pull.get("base"), Mapping) else {}
    number = int(pull.get("number") or pull.get("index"))
    return {
        "number": number,
        "url": str(pull.get("html_url") or pull.get("url") or f"{repo.web_url}/pulls/{number}"),
        "title": str(pull.get("title") or ""),
        "state": str(pull.get("state") or ""),
        "head": _branch_record(head, default_owner=repo.owner),
        "base": _branch_record(base, default_owner=repo.owner),
    }


def _branch_record(branch_data: Mapping[str, Any], default_owner: str) -> dict[str, str]:
    label = str(branch_data.get("label") or "")
    ref = str(branch_data.get("ref") or "")
    if ":" in label:
        owner, branch = label.split(":", 1)
        return {"owner": owner, "branch": branch}
    return {"owner": default_owner, "branch": ref or label}


def enable_automerge(repo: RepositoryScope, pr: int, style: str = "squash", message: str = "") -> None:
    body: dict[str, Any] = {"Do": style, "merge_when_checks_succeed": True}
    if message:
        body["merge_message_field"] = message
    repo.post(f"pulls/{pr}/merge", body)


def cancel_automerge(repo: RepositoryScope, pr: int) -> None:
    repo.delete(f"pulls/{pr}/merge")
