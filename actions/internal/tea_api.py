#!/usr/bin/env python3
"""Private Gitea/Forgejo HTTP Adapter for bundled tea-skills actions."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Callable, Mapping
from urllib import parse, request
from urllib.error import HTTPError, URLError


class TeaConfigError(RuntimeError):
    """Raised when tea CLI configuration cannot be discovered or parsed."""


class RepoContextError(RuntimeError):
    """Raised when repository owner/name cannot be derived from git."""


class ApiError(RuntimeError):
    """Raised for non-2xx API responses or transport failures."""

    def __init__(self, method: str, url: str, status: int | None, body: str):
        self.method = method
        self.url = url
        self.status = status
        self.body = body
        status_text = f"HTTP {status}" if status is not None else "transport error"
        detail = f": {body}" if body else ""
        super().__init__(f"{method} {url} failed ({status_text}){detail}")


@dataclass(frozen=True)
class TeaConfig:
    token: str
    base_url: str


@dataclass(frozen=True)
class RepoContext:
    owner: str
    repo: str


class BytesBody:
    """Small file-like wrapper used by tests for HTTPError bodies."""

    def __init__(self, data: bytes):
        self._data = data

    def read(self) -> bytes:
        return self._data


    def close(self) -> None:
        pass


class FakeHttpResponse:
    """Small context-manager response used by tests."""

    def __init__(self, status: int, payload: Any):
        self.status = status
        self._payload = payload

    def __enter__(self) -> "FakeHttpResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def read(self) -> bytes:
        if self._payload is None:
            return b""
        return json.dumps(self._payload).encode("utf-8")


def config_path() -> Path:
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home) / "tea" / "config.yml"
    return Path.home() / ".config" / "tea" / "config.yml"


def _first_yaml_scalar(text: str, key: str) -> str | None:
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*:\s*(.+?)\s*$")
    for line in text.splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1).strip().strip('"').strip("'")
    return None


def read_tea_config(path: Path | None = None) -> TeaConfig:
    cfg_path = path or config_path()
    try:
        text = cfg_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise TeaConfigError(f"tea config not found at {cfg_path}; run tea login first") from exc

    token = _first_yaml_scalar(text, "token")
    base_url = _first_yaml_scalar(text, "url")
    if not token:
        raise TeaConfigError(f"tea config at {cfg_path} does not contain a token")
    if not base_url:
        raise TeaConfigError(f"tea config at {cfg_path} does not contain a url")
    return TeaConfig(token=token, base_url=base_url.rstrip("/"))


def parse_repo_remote(remote_url: str) -> tuple[str, str]:
    remote = remote_url.strip()
    if not remote:
        raise RepoContextError("git remote origin is empty")

    if "://" in remote:
        path = parse.urlparse(remote).path
    elif ":" in remote and not remote.startswith("/"):
        path = remote.split(":", 1)[1]
    else:
        path = remote

    parts = [part for part in path.strip("/").split("/") if part]
    if len(parts) < 2:
        raise RepoContextError(f"cannot parse owner/repo from git remote: {remote_url}")
    owner = parts[-2]
    repo = parts[-1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not owner or not repo:
        raise RepoContextError(f"cannot parse owner/repo from git remote: {remote_url}")
    return owner, repo


def discover_repo_context() -> RepoContext:
    completed = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise RepoContextError(completed.stderr.strip() or "failed to read git remote origin")
    owner, repo = parse_repo_remote(completed.stdout)
    return RepoContext(owner=owner, repo=repo)


class GiteaAdapter:
    def __init__(
        self,
        config: TeaConfig | None = None,
        repo: RepoContext | None = None,
        opener: Callable[[request.Request], Any] | None = None,
    ):
        self.config = config or read_tea_config()
        self.repo = repo or discover_repo_context()
        self._opener = opener or request.urlopen

    @property
    def api_root(self) -> str:
        return f"{self.config.base_url}/api/v1"

    @property
    def repo_root(self) -> str:
        owner = parse.quote(self.repo.owner, safe="")
        repo = parse.quote(self.repo.repo, safe="")
        return f"{self.api_root}/repos/{owner}/{repo}"

    @property
    def org_root(self) -> str:
        owner = parse.quote(self.repo.owner, safe="")
        return f"{self.api_root}/orgs/{owner}"

    def repo_url(self, endpoint: str, query: Mapping[str, Any] | None = None) -> str:
        return self._url(self.repo_root, endpoint, query)

    def org_url(self, endpoint: str, query: Mapping[str, Any] | None = None) -> str:
        return self._url(self.org_root, endpoint, query)

    def _url(self, root: str, endpoint: str, query: Mapping[str, Any] | None = None) -> str:
        clean_endpoint = endpoint.strip("/")
        url = f"{root}/{clean_endpoint}" if clean_endpoint else root
        if query:
            url = f"{url}?{parse.urlencode(query)}"
        return url

    def get_repo(self, endpoint: str, query: Mapping[str, Any] | None = None) -> Any:
        return self.request_json("GET", self.repo_url(endpoint, query))

    def post_repo(self, endpoint: str, body: Mapping[str, Any] | None = None) -> Any:
        return self.request_json("POST", self.repo_url(endpoint), body)

    def patch_repo(self, endpoint: str, body: Mapping[str, Any]) -> Any:
        return self.request_json("PATCH", self.repo_url(endpoint), body)

    def delete_repo(self, endpoint: str, body: Mapping[str, Any] | None = None) -> Any:
        return self.request_json("DELETE", self.repo_url(endpoint), body)

    def get_org(self, endpoint: str, query: Mapping[str, Any] | None = None) -> Any:
        return self.request_json("GET", self.org_url(endpoint, query))

    def post_org(self, endpoint: str, body: Mapping[str, Any] | None = None) -> Any:
        return self.request_json("POST", self.org_url(endpoint), body)

    def edit_issue_comment(self, comment_id: int, body: str) -> Any:
        return self.patch_repo(f"issues/comments/{comment_id}", {"body": body})

    def lock_issue(self, issue: int, reason: str = "resolved") -> None:
        self.post_repo(f"issues/{issue}/lock", {"lock_reason": reason})

    def unlock_issue(self, issue: int) -> None:
        self.delete_repo(f"issues/{issue}/lock")

    def pin_issue(self, issue: int) -> None:
        self.post_repo(f"issues/{issue}/pin", {})

    def unpin_issue(self, issue: int) -> None:
        self.delete_repo(f"issues/{issue}/pin")

    def add_issue_reaction(self, issue: int, reaction: str) -> Any:
        return self.post_repo(f"issues/{issue}/reactions", {"content": reaction})

    def list_issue_reactions(self, issue: int) -> list[dict[str, Any]]:
        result = self.get_repo(f"issues/{issue}/reactions")
        return result if isinstance(result, list) else []

    def add_issue_dependency(self, issue: int, depends_on: int) -> str:
        body = {"index": depends_on, "owner": self.repo.owner, "repo": self.repo.repo}
        try:
            self.post_repo(f"issues/{issue}/dependencies", body)
        except ApiError as exc:
            if exc.status == 409:
                return "exists"
            raise
        return "added"

    def remove_issue_dependency(self, issue: int, depends_on: int) -> None:
        body = {"index": depends_on, "owner": self.repo.owner, "repo": self.repo.repo}
        self.delete_repo(f"issues/{issue}/dependencies", body)

    def list_issue_dependencies(self, issue: int) -> list[dict[str, Any]]:
        result = self.get_repo(f"issues/{issue}/dependencies")
        return result if isinstance(result, list) else []

    def list_open_issues(self) -> list[dict[str, Any]]:
        result = self.get_repo("issues", {"state": "open"})
        return result if isinstance(result, list) else []

    def list_all_issues(self) -> list[dict[str, Any]]:
        result = self.get_repo("issues", {"state": "all"})
        return result if isinstance(result, list) else []

    def all_issue_dependencies(self) -> list[tuple[int, list[dict[str, Any]]]]:
        rows: list[tuple[int, list[dict[str, Any]]]] = []
        for issue in self.list_open_issues():
            number = int(issue.get("number") or issue.get("index"))
            deps = self.list_issue_dependencies(number)
            if deps:
                rows.append((number, deps))
        return rows

    def ready_issues(self) -> list[dict[str, Any]]:
        ready: list[dict[str, Any]] = []
        for issue in self.list_open_issues():
            number = int(issue.get("number") or issue.get("index"))
            deps = self.list_issue_dependencies(number)
            open_blockers = [dep for dep in deps if dep.get("state") == "open"]
            if not open_blockers:
                ready.append(issue)
        return ready

    def dependency_graph_edges(self) -> list[tuple[int, int]]:
        edges: list[tuple[int, int]] = []
        for issue in self.list_all_issues():
            number = int(issue.get("number") or issue.get("index"))
            for dep in self.list_issue_dependencies(number):
                dep_number = dep.get("number") or dep.get("index")
                if dep_number is not None:
                    edges.append((number, int(dep_number)))
        return edges


    def find_milestone_id_by_name(self, name: str) -> int:
        result = self.get_repo("milestones", {"name": name})
        if not isinstance(result, list) or not result:
            raise ApiError("GET", self.repo_url("milestones", {"name": name}), 404, f"Milestone '{name}' not found")
        milestone_id = result[0].get("id")
        if milestone_id is None:
            raise ApiError("GET", self.repo_url("milestones", {"name": name}), 404, f"Milestone '{name}' has no id")
        return int(milestone_id)

    def edit_milestone(
        self,
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
        milestone_id = self.find_milestone_id_by_name(name)
        return self.patch_repo(f"milestones/{milestone_id}", body)

    def list_org_labels(self) -> list[dict[str, Any]]:
        result = self.get_org("labels")
        return result if isinstance(result, list) else []

    def create_org_label(self, name: str, color: str, description: str = "") -> Any:
        return self.post_org("labels", {"name": name, "color": color, "description": description})

    def enable_pull_request_automerge(self, pr: int, style: str = "squash", message: str = "") -> None:
        body: dict[str, Any] = {"Do": style, "merge_when_checks_succeed": True}
        if message:
            body["merge_message_field"] = message
        self.post_repo(f"pulls/{pr}/merge", body)

    def cancel_pull_request_automerge(self, pr: int) -> None:
        self.delete_repo(f"pulls/{pr}/merge")


    def request_json(self, method: str, url: str, body: Mapping[str, Any] | None = None) -> Any:
        data = None
        headers = {"Authorization": f"token {self.config.token}", "Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = request.Request(url=url, data=data, headers=headers, method=method)
        try:
            with self._opener(req) as response:
                raw = response.read()
        except HTTPError as exc:
            raw_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            exc.close()
            raise ApiError(method, url, exc.code, raw_body) from exc
        except URLError as exc:
            raise ApiError(method, url, None, str(exc.reason)) from exc

        if not raw:
            return None
        text = raw.decode("utf-8")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text


def default_adapter() -> GiteaAdapter:
    return GiteaAdapter()
