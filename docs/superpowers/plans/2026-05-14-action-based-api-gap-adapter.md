# Action-Based API Gap Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the sourced bash API-gap scripts with action-specific Python executables under `actions/`, backed by a private stdlib-only Gitea/Forgejo HTTP Adapter.

**Architecture:** `actions/internal/tea_api.py` owns config discovery, repo context, URL/query encoding, JSON, HTTP, and domain API helpers. User-facing files under `actions/<domain>/<action>` are thin Python executables for specific missing `tea` CLI capabilities. README files are the routing Interface: they document normal `tea` commands first and bundled actions second.

**Tech Stack:** Python 3 standard library (`argparse`, `json`, `os`, `pathlib`, `subprocess`, `urllib`), `unittest`, existing `tea` CLI for documented non-gap workflows.

---

## File Structure

Create:
- `actions/README.md` — global action routing rules.
- `actions/internal/README.md` — private Adapter contract.
- `actions/internal/tea_api.py` — private HTTP Adapter and domain helper functions.
- `actions/issues/README.md` — issue `tea` commands and issue gap actions.
- `actions/issues/comment-edit` — edit an existing issue comment.
- `actions/issues/lock` — lock an issue.
- `actions/issues/unlock` — unlock an issue.
- `actions/issues/pin` — pin an issue.
- `actions/issues/unpin` — unpin an issue.
- `actions/issues/reaction-add` — add an issue reaction.
- `actions/issues/reaction-list` — list issue reactions.
- `actions/issues/dependency-add` — add dependency, “A depends on B”.
- `actions/issues/dependency-remove` — remove dependency.
- `actions/issues/dependency-list` — list one issue’s dependencies.
- `actions/issues/dependency-all` — list dependencies for all open issues.
- `actions/issues/dependency-ready` — list open issues with no open blockers.
- `actions/issues/dependency-graph` — print text dependency graph.
- `actions/pull-requests/README.md` — pull request `tea` commands and PR gap actions.
- `actions/pull-requests/set-automerge` — enable or cancel auto-merge configuration.
- `actions/milestones/README.md` — milestone `tea` commands and edit action.
- `actions/milestones/edit` — edit milestone title/deadline/description.
- `actions/org-labels/README.md` — repo label `tea` commands and org label actions.
- `actions/org-labels/list` — list org labels.
- `actions/org-labels/create` — create org label.
- `tests/test_tea_api.py` — stdlib unit tests for Adapter behavior.
- `tests/test_action_contracts.py` — stdlib tests for executable layout and docs references.

Modify:
- `README.md` — replace Scripts section with Actions section.
- `AGENTS.md` and `CLAUDE.md` — update project guidance from scripts/bash to actions/Python.
- `skills/create-pull/SKILL.md` — remove draft script, route WIP PR creation to `tea pulls create`.
- `skills/review-pull/SKILL.md` — remove raw `_api_*` examples and reviewer script; route to `tea`.
- `skills/merge-pull/SKILL.md` — route auto-merge action to `actions/pull-requests/README.md`; route ready/WIP title to `tea pulls edit`.
- `skills/issue-moderation/SKILL.md` — reference `actions/issues/README.md`.
- `skills/issue-comments/SKILL.md` — reference `actions/issues/README.md`.
- `skills/issue-dependencies/SKILL.md` — reference `actions/issues/README.md`.
- `skills/label-schemes/SKILL.md` — reference `actions/org-labels/README.md`.
- `skills/milestones/SKILL.md` — reference `actions/milestones/README.md`.
- `skills/using-the-tea-api/SKILL.md` — replace public helper docs with internal-action routing guidance or remove public `_api_*` contract.

Remove:
- `scripts/tea-api`
- `scripts/tea-dep`
- `scripts/tea-issue-comment`
- `scripts/tea-issue-lock`
- `scripts/tea-issue-pin`
- `scripts/tea-issue-react`
- `scripts/tea-label-org`
- `scripts/tea-milestone-edit`
- `scripts/tea-pr-automerge`
- `scripts/tea-pr-draft`
- `scripts/tea-pr-reviewers`

---

### Task 1: Create the private Adapter core with tests

**Files:**
- Create: `actions/internal/tea_api.py`
- Create: `actions/internal/README.md`
- Create: `tests/test_tea_api.py`

- [ ] **Step 1: Write failing Adapter core tests**

Create `tests/test_tea_api.py` with this complete content:

```python
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError

from actions.internal import tea_api


class TeaApiCoreTests(unittest.TestCase):
    def test_config_path_prefers_xdg_config_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            xdg = Path(tmp) / "xdg"
            expected = xdg / "tea" / "config.yml"
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(xdg)}):
                self.assertEqual(tea_api.config_path(), expected)

    def test_config_path_falls_back_to_home_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            with mock.patch.dict(os.environ, {}, clear=True):
                with mock.patch.object(Path, "home", return_value=home):
                    self.assertEqual(tea_api.config_path(), home / ".config" / "tea" / "config.yml")

    def test_read_config_extracts_first_token_and_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.yml"
            config.write_text(
                "logins:\n"
                "  - name: main\n"
                "    url: https://forge.example\n"
                "    token: abc123\n",
                encoding="utf-8",
            )
            result = tea_api.read_tea_config(config)
            self.assertEqual(result.token, "abc123")
            self.assertEqual(result.base_url, "https://forge.example")

    def test_read_config_errors_when_token_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.yml"
            config.write_text("url: https://forge.example\n", encoding="utf-8")
            with self.assertRaisesRegex(tea_api.TeaConfigError, "token"):
                tea_api.read_tea_config(config)

    def test_parse_repo_remote_supports_https(self):
        self.assertEqual(
            tea_api.parse_repo_remote("https://forge.example/owner/repo.git"),
            ("owner", "repo"),
        )

    def test_parse_repo_remote_supports_ssh_scp_style(self):
        self.assertEqual(
            tea_api.parse_repo_remote("git@forge.example:owner/repo.git"),
            ("owner", "repo"),
        )

    def test_build_url_encodes_query_values(self):
        config = tea_api.TeaConfig(token="t", base_url="https://forge.example")
        context = tea_api.RepoContext(owner="alice", repo="project")
        adapter = tea_api.GiteaAdapter(config=config, repo=context, opener=lambda request: None)
        url = adapter.repo_url("milestones", {"name": "v1.0 alpha"})
        self.assertEqual(
            url,
            "https://forge.example/api/v1/repos/alice/project/milestones?name=v1.0+alpha",
        )

    def test_request_json_encodes_body_and_headers(self):
        captured = {}

        def opener(request):
            captured["url"] = request.full_url
            captured["method"] = request.get_method()
            captured["headers"] = dict(request.header_items())
            captured["data"] = request.data
            return tea_api.FakeHttpResponse(201, {"id": 1})

        config = tea_api.TeaConfig(token="secret", base_url="https://forge.example")
        context = tea_api.RepoContext(owner="alice", repo="project")
        adapter = tea_api.GiteaAdapter(config=config, repo=context, opener=opener)
        result = adapter.post_repo("issues/1/reactions", {"content": "+1"})

        self.assertEqual(result, {"id": 1})
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["headers"]["Authorization"], "token secret")
        self.assertEqual(captured["headers"]["Content-type"], "application/json")
        self.assertEqual(json.loads(captured["data"].decode("utf-8")), {"content": "+1"})

    def test_http_error_includes_status_and_body(self):
        def opener(request):
            raise HTTPError(
                request.full_url,
                409,
                "Conflict",
                hdrs=None,
                fp=tea_api.BytesBody(b'{"message":"already exists"}'),
            )

        config = tea_api.TeaConfig(token="secret", base_url="https://forge.example")
        context = tea_api.RepoContext(owner="alice", repo="project")
        adapter = tea_api.GiteaAdapter(config=config, repo=context, opener=opener)

        with self.assertRaises(tea_api.ApiError) as raised:
            adapter.post_repo("issues/1/dependencies", {"index": 2})

        self.assertEqual(raised.exception.status, 409)
        self.assertIn("POST", str(raised.exception))
        self.assertIn("already exists", str(raised.exception))

    def test_repo_context_uses_git_remote_origin(self):
        completed = subprocess.CompletedProcess(
            args=["git"], returncode=0, stdout="git@forge.example:owner/repo.git\n", stderr=""
        )
        with mock.patch("subprocess.run", return_value=completed):
            self.assertEqual(tea_api.discover_repo_context(), tea_api.RepoContext("owner", "repo"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_tea_api -v
```

Expected: FAIL with an import error because `actions/internal/tea_api.py` does not exist.

- [ ] **Step 3: Implement the Adapter core**

Create `actions/internal/tea_api.py` with this complete content:

```python
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
```

- [ ] **Step 4: Create internal README**

Create `actions/internal/README.md`:

```markdown
# Internal action support

`tea_api.py` is a private Python Module used by bundled actions. It is not a user-facing command Interface.

Responsibilities:

- discover tea config from `$XDG_CONFIG_HOME/tea/config.yml` or `~/.config/tea/config.yml`
- derive repo owner/name from `git remote get-url origin`
- build repo and org API URLs
- encode query strings and JSON bodies safely
- send authenticated Gitea/Forgejo HTTP requests with Python stdlib only
- expose domain helper functions for action executables

Users and agents should use documented commands in the domain README files instead of importing this Module directly.
```

- [ ] **Step 5: Run tests to verify Adapter core passes**

Run:

```bash
python3 -m unittest tests.test_tea_api -v
```

Expected: PASS for all core tests.

- [ ] **Step 6: Commit Adapter core**

Run:

```bash
git add actions/internal/tea_api.py actions/internal/README.md tests/test_tea_api.py
git commit -m "feat: add private tea api adapter core"
```

Expected: commit succeeds.

---

### Task 2: Add issue domain helpers and action executables

**Files:**
- Modify: `actions/internal/tea_api.py`
- Create: `actions/issues/README.md`
- Create: `actions/issues/comment-edit`
- Create: `actions/issues/lock`
- Create: `actions/issues/unlock`
- Create: `actions/issues/pin`
- Create: `actions/issues/unpin`
- Create: `actions/issues/reaction-add`
- Create: `actions/issues/reaction-list`
- Create: `actions/issues/dependency-add`
- Create: `actions/issues/dependency-remove`
- Create: `actions/issues/dependency-list`
- Create: `actions/issues/dependency-all`
- Create: `actions/issues/dependency-ready`
- Create: `actions/issues/dependency-graph`
- Modify: `tests/test_tea_api.py`

- [ ] **Step 1: Add failing issue helper tests**

Append these tests inside `TeaApiCoreTests` in `tests/test_tea_api.py`, before the `if __name__ == "__main__"` block:

```python
    def test_edit_issue_comment_sends_body(self):
        calls = []
        adapter = tea_api.GiteaAdapter(
            tea_api.TeaConfig("t", "https://forge.example"),
            tea_api.RepoContext("owner", "repo"),
            opener=lambda request: calls.append(request) or tea_api.FakeHttpResponse(200, {"id": 12}),
        )
        result = adapter.edit_issue_comment(12, "updated text")
        self.assertEqual(result["id"], 12)
        self.assertEqual(calls[0].get_method(), "PATCH")
        self.assertTrue(calls[0].full_url.endswith("/issues/comments/12"))
        self.assertEqual(json.loads(calls[0].data.decode("utf-8")), {"body": "updated text"})

    def test_issue_dependency_add_handles_conflict(self):
        def opener(request):
            raise HTTPError(request.full_url, 409, "Conflict", hdrs=None, fp=tea_api.BytesBody(b"exists"))

        adapter = tea_api.GiteaAdapter(
            tea_api.TeaConfig("t", "https://forge.example"),
            tea_api.RepoContext("owner", "repo"),
            opener=opener,
        )
        self.assertEqual(adapter.add_issue_dependency(25, 26), "exists")

    def test_ready_issues_filters_open_blockers(self):
        responses = {
            "issues": [
                {"number": 1, "state": "open", "title": "Ready"},
                {"number": 2, "state": "open", "title": "Blocked"},
            ],
            "issues/1/dependencies": [],
            "issues/2/dependencies": [{"number": 99, "state": "open", "title": "Blocker"}],
        }

        def opener(request):
            endpoint = request.full_url.split("/repos/owner/repo/", 1)[1].split("?", 1)[0]
            return tea_api.FakeHttpResponse(200, responses[endpoint])

        adapter = tea_api.GiteaAdapter(
            tea_api.TeaConfig("t", "https://forge.example"),
            tea_api.RepoContext("owner", "repo"),
            opener=opener,
        )
        self.assertEqual(adapter.ready_issues(), [{"number": 1, "state": "open", "title": "Ready"}])
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_tea_api -v
```

Expected: FAIL with missing methods such as `edit_issue_comment` and `add_issue_dependency`.

- [ ] **Step 3: Add issue helper methods to Adapter**

Insert these methods inside `class GiteaAdapter` in `actions/internal/tea_api.py`, immediately before `def request_json`:

```python
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
```

- [ ] **Step 4: Create issue actions README**

Create `actions/issues/README.md`:

```markdown
# Issue actions

Prefer the `tea` CLI for normal issue workflows:

```bash
tea issues list -o simple
tea issues 42 --comments
tea issues create --title "Fix login" --description "Details"
tea issues edit 42 --title "New title"
tea issues close 42
tea issues reopen 42
tea comment 42 "This is a comment"
```

Use bundled actions only for Gitea/Forgejo issue features that `tea` does not expose cleanly.

## Comment edit

```bash
actions/issues/comment-edit <comment-id> <body>
```

Edits an existing issue comment. Add and list comments with `tea comment` and `tea issues <issue> --comments`.

## Locking

```bash
actions/issues/lock <issue> [reason]
actions/issues/unlock <issue>
```

Default lock reason is `resolved`.

## Pinning

```bash
actions/issues/pin <issue>
actions/issues/unpin <issue>
```

## Reactions

```bash
actions/issues/reaction-add <issue> <reaction>
actions/issues/reaction-list <issue>
```

Common reactions: `+1`, `-1`, `laugh`, `confused`, `heart`, `hooray`, `rocket`, `eyes`.

## Dependencies

“A depends on B” means B blocks A.

```bash
actions/issues/dependency-add <issue> <depends-on>
actions/issues/dependency-remove <issue> <depends-on>
actions/issues/dependency-list <issue>
actions/issues/dependency-all
actions/issues/dependency-ready
actions/issues/dependency-graph
```
```

- [ ] **Step 5: Create issue action executables**

Create each file with the exact content shown below.

`actions/issues/comment-edit`:

```python
#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Edit a Gitea/Forgejo issue comment.")
    parser.add_argument("comment_id", type=int)
    parser.add_argument("body")
    args = parser.parse_args(argv)
    try:
        comment = default_adapter().edit_issue_comment(args.comment_id, args.body)
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Comment #{comment.get('id', args.comment_id)} updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

`actions/issues/lock`:

```python
#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Lock a Gitea/Forgejo issue.")
    parser.add_argument("issue", type=int)
    parser.add_argument("reason", nargs="?", default="resolved")
    args = parser.parse_args(argv)
    try:
        default_adapter().lock_issue(args.issue, args.reason)
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Locked #{args.issue} ({args.reason})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

`actions/issues/unlock`:

```python
#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Unlock a Gitea/Forgejo issue.")
    parser.add_argument("issue", type=int)
    args = parser.parse_args(argv)
    try:
        default_adapter().unlock_issue(args.issue)
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Unlocked #{args.issue}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

`actions/issues/pin`:

```python
#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Pin a Gitea/Forgejo issue.")
    parser.add_argument("issue", type=int)
    args = parser.parse_args(argv)
    try:
        default_adapter().pin_issue(args.issue)
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Pinned #{args.issue}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

`actions/issues/unpin`:

```python
#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Unpin a Gitea/Forgejo issue.")
    parser.add_argument("issue", type=int)
    args = parser.parse_args(argv)
    try:
        default_adapter().unpin_issue(args.issue)
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Unpinned #{args.issue}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

`actions/issues/reaction-add`:

```python
#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Add a reaction to a Gitea/Forgejo issue.")
    parser.add_argument("issue", type=int)
    parser.add_argument("reaction")
    args = parser.parse_args(argv)
    try:
        reaction = default_adapter().add_issue_reaction(args.issue, args.reaction)
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Added {reaction.get('content', args.reaction)} to #{args.issue}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

`actions/issues/reaction-list`:

```python
#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="List reactions on a Gitea/Forgejo issue.")
    parser.add_argument("issue", type=int)
    args = parser.parse_args(argv)
    try:
        reactions = default_adapter().list_issue_reactions(args.issue)
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for reaction in reactions:
        user = reaction.get("user", {}).get("login", "unknown")
        print(f"{user}: {reaction.get('content', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

`actions/issues/dependency-add`:

```python
#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Add an issue dependency. A depends on B; B blocks A.")
    parser.add_argument("issue", type=int)
    parser.add_argument("depends_on", type=int)
    args = parser.parse_args(argv)
    try:
        result = default_adapter().add_issue_dependency(args.issue, args.depends_on)
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if result == "exists":
        print(f"Already exists: #{args.issue} depends on #{args.depends_on}")
    else:
        print(f"Added: #{args.issue} depends on #{args.depends_on}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

`actions/issues/dependency-remove`:

```python
#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Remove an issue dependency.")
    parser.add_argument("issue", type=int)
    parser.add_argument("depends_on", type=int)
    args = parser.parse_args(argv)
    try:
        default_adapter().remove_issue_dependency(args.issue, args.depends_on)
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Removed: #{args.issue} no longer depends on #{args.depends_on}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

`actions/issues/dependency-list`:

```python
#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="List dependencies for one issue.")
    parser.add_argument("issue", type=int)
    args = parser.parse_args(argv)
    try:
        deps = default_adapter().list_issue_dependencies(args.issue)
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not deps:
        print(f"Issue #{args.issue} has no dependencies")
    else:
        print(f"Issue #{args.issue} depends on:")
        for dep in deps:
            print(f"  #{dep.get('number')} [{dep.get('state')}] {dep.get('title')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

`actions/issues/dependency-all`:

```python
#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter


def main(argv: list[str]) -> int:
    if argv:
        print("usage: dependency-all", file=sys.stderr)
        return 2
    try:
        rows = default_adapter().all_issue_dependencies()
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not rows:
        print("No dependencies found for open issues")
    for issue, deps in rows:
        numbers = " ".join(f"#{dep.get('number')}" for dep in deps)
        print(f"#{issue} depends on: {numbers}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

`actions/issues/dependency-ready`:

```python
#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter


def main(argv: list[str]) -> int:
    if argv:
        print("usage: dependency-ready", file=sys.stderr)
        return 2
    try:
        issues = default_adapter().ready_issues()
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("Issues with no open blockers:")
    for issue in issues:
        number = issue.get("number") or issue.get("index")
        print(f"  #{number} {issue.get('title')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

`actions/issues/dependency-graph`:

```python
#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter


def main(argv: list[str]) -> int:
    if argv:
        print("usage: dependency-graph", file=sys.stderr)
        return 2
    try:
        edges = default_adapter().dependency_graph_edges()
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("Dependency graph (A -> B means A depends on B):")
    print("---")
    for issue, depends_on in edges:
        print(f"  #{issue} -> #{depends_on}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 6: Make issue actions executable**

Run:

```bash
chmod +x actions/issues/comment-edit actions/issues/lock actions/issues/unlock actions/issues/pin actions/issues/unpin actions/issues/reaction-add actions/issues/reaction-list actions/issues/dependency-add actions/issues/dependency-remove actions/issues/dependency-list actions/issues/dependency-all actions/issues/dependency-ready actions/issues/dependency-graph
```

Expected: command succeeds.

- [ ] **Step 7: Run tests and action help checks**

Run:

```bash
python3 -m unittest tests.test_tea_api -v
for action in actions/issues/comment-edit actions/issues/lock actions/issues/unlock actions/issues/pin actions/issues/unpin actions/issues/reaction-add actions/issues/reaction-list actions/issues/dependency-add actions/issues/dependency-remove actions/issues/dependency-list; do "$action" --help >/dev/null; done
```

Expected: tests PASS; help checks exit 0.

- [ ] **Step 8: Commit issue actions**

Run:

```bash
git add actions/internal/tea_api.py actions/issues tests/test_tea_api.py
git commit -m "feat: add issue api gap actions"
```

Expected: commit succeeds.

---

### Task 3: Add pull request, milestone, and org-label actions

**Files:**
- Modify: `actions/internal/tea_api.py`
- Create: `actions/pull-requests/README.md`
- Create: `actions/pull-requests/set-automerge`
- Create: `actions/milestones/README.md`
- Create: `actions/milestones/edit`
- Create: `actions/org-labels/README.md`
- Create: `actions/org-labels/list`
- Create: `actions/org-labels/create`
- Modify: `tests/test_tea_api.py`

- [ ] **Step 1: Add failing tests for remaining domain helpers**

Append these tests inside `TeaApiCoreTests` in `tests/test_tea_api.py`, before the `if __name__ == "__main__"` block:

```python
    def test_find_milestone_id_by_name_uses_query_encoding(self):
        captured = {}

        def opener(request):
            captured["url"] = request.full_url
            return tea_api.FakeHttpResponse(200, [{"id": 7, "title": "v1.0 alpha"}])

        adapter = tea_api.GiteaAdapter(
            tea_api.TeaConfig("t", "https://forge.example"),
            tea_api.RepoContext("owner", "repo"),
            opener=opener,
        )
        self.assertEqual(adapter.find_milestone_id_by_name("v1.0 alpha"), 7)
        self.assertTrue(captured["url"].endswith("/milestones?name=v1.0+alpha"))

    def test_edit_milestone_sends_due_on_timestamp(self):
        bodies = []

        def opener(request):
            if request.get_method() == "GET":
                return tea_api.FakeHttpResponse(200, [{"id": 7}])
            bodies.append(json.loads(request.data.decode("utf-8")))
            return tea_api.FakeHttpResponse(200, {"id": 7})

        adapter = tea_api.GiteaAdapter(
            tea_api.TeaConfig("t", "https://forge.example"),
            tea_api.RepoContext("owner", "repo"),
            opener=opener,
        )
        adapter.edit_milestone("v1", due_date="2026-06-01")
        self.assertEqual(bodies[-1], {"due_on": "2026-06-01T00:00:00Z"})

    def test_create_org_label_posts_to_org_scope(self):
        captured = {}

        def opener(request):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return tea_api.FakeHttpResponse(201, {"name": "org:team-a"})

        adapter = tea_api.GiteaAdapter(
            tea_api.TeaConfig("t", "https://forge.example"),
            tea_api.RepoContext("owner", "repo"),
            opener=opener,
        )
        adapter.create_org_label("org:team-a", "#0052cc", "Owned by Team A")
        self.assertEqual(captured["url"], "https://forge.example/api/v1/orgs/owner/labels")
        self.assertEqual(captured["body"]["description"], "Owned by Team A")

    def test_set_automerge_enable_sends_merge_when_checks_succeed(self):
        captured = {}

        def opener(request):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return tea_api.FakeHttpResponse(200, {})

        adapter = tea_api.GiteaAdapter(
            tea_api.TeaConfig("t", "https://forge.example"),
            tea_api.RepoContext("owner", "repo"),
            opener=opener,
        )
        adapter.enable_pull_request_automerge(15, "squash", "feat: add auth")
        self.assertEqual(
            captured["body"],
            {"Do": "squash", "merge_when_checks_succeed": True, "merge_message_field": "feat: add auth"},
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_tea_api -v
```

Expected: FAIL with missing methods such as `edit_milestone`, `create_org_label`, and `enable_pull_request_automerge`.

- [ ] **Step 3: Add remaining helper methods to Adapter**

Insert these methods inside `class GiteaAdapter` in `actions/internal/tea_api.py`, immediately before `def request_json`:

```python
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
```

- [ ] **Step 4: Create remaining domain READMEs**

Create `actions/pull-requests/README.md`:

```markdown
# Pull request actions

Prefer the `tea` CLI for normal pull request workflows:

```bash
tea pulls create --title "WIP: Feature" --head feature-branch
tea pulls edit 15 --title "Feature"
tea pulls edit 15 --add-reviewers user1,user2
tea pulls edit 15 --remove-reviewers user1
tea pulls review 15
tea pulls approve 15 "Looks good"
tea pulls reject 15 "Please fix the failing test"
tea pulls merge 15 --style squash
tea pulls review-comments 15
tea pulls resolve 123
tea pulls unresolve 123
```

Use bundled actions only for pull request features that `tea` does not expose cleanly.

## Set auto-merge

```bash
actions/pull-requests/set-automerge <pr> --enable [--style squash|merge|rebase] [--message "message"]
actions/pull-requests/set-automerge <pr> --cancel
```

This configures auto-merge. It does not merge the pull request immediately.
```

Create `actions/milestones/README.md`:

```markdown
# Milestone actions

Prefer the `tea` CLI for normal milestone workflows:

```bash
tea milestones list -o simple
tea milestones create --title "v1.0" --description "First stable release"
tea milestones close "v1.0"
tea milestones reopen "v1.0"
tea milestones delete "v1.0"
tea milestones issues add "v1.0" 42
tea milestones issues remove "v1.0" 42
```

Use bundled actions only for milestone features that `tea` does not expose cleanly.

## Edit milestone

```bash
actions/milestones/edit <milestone-name> [--title <title>] [--deadline YYYY-MM-DD] [--description <text>]
```

Milestones are identified by name in `tea`, but by ID in the Gitea/Forgejo API. This action looks up the ID before editing.
```

Create `actions/org-labels/README.md`:

```markdown
# Organization label actions

Use `tea labels` for repository labels:

```bash
tea labels list -o simple
tea labels create --name "type:bug" --color "#d73a4a"
tea labels update --id 5 --description "Updated description"
tea labels delete 5
```

Use bundled actions for organization-level labels.

## List organization labels

```bash
actions/org-labels/list
```

## Create organization label

```bash
actions/org-labels/create <name> <color> [description]
```
```

- [ ] **Step 5: Create remaining action executables**

Create `actions/pull-requests/set-automerge`:

```python
#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Enable or cancel pull request auto-merge.")
    parser.add_argument("pr", type=int)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--enable", action="store_true")
    mode.add_argument("--cancel", action="store_true")
    parser.add_argument("--style", choices=["merge", "squash", "rebase"], default="squash")
    parser.add_argument("--message", default="")
    args = parser.parse_args(argv)
    try:
        adapter = default_adapter()
        if args.enable:
            adapter.enable_pull_request_automerge(args.pr, args.style, args.message)
            print(f"Auto-merge enabled on PR #{args.pr} ({args.style})")
        else:
            adapter.cancel_pull_request_automerge(args.pr)
            print(f"Auto-merge cancelled on PR #{args.pr}")
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

Create `actions/milestones/edit`:

```python
#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Edit a Gitea/Forgejo milestone.")
    parser.add_argument("name")
    parser.add_argument("--title")
    parser.add_argument("--deadline")
    parser.add_argument("--description")
    args = parser.parse_args(argv)
    if args.title is None and args.deadline is None and args.description is None:
        parser.error("provide at least one of --title, --deadline, or --description")
    try:
        default_adapter().edit_milestone(args.name, args.title, args.deadline, args.description)
    except (ApiError, TeaConfigError, RepoContextError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Milestone '{args.name}' updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

Create `actions/org-labels/list`:

```python
#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter


def main(argv: list[str]) -> int:
    if argv:
        print("usage: list", file=sys.stderr)
        return 2
    try:
        labels = default_adapter().list_org_labels()
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for label in labels:
        print(f"{label.get('name')} {label.get('color')} {label.get('description') or ''}".rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

Create `actions/org-labels/create`:

```python
#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Create a Gitea/Forgejo organization label.")
    parser.add_argument("name")
    parser.add_argument("color")
    parser.add_argument("description", nargs="?", default="")
    args = parser.parse_args(argv)
    try:
        label = default_adapter().create_org_label(args.name, args.color, args.description)
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Created org label: {label.get('name', args.name)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 6: Make remaining actions executable**

Run:

```bash
chmod +x actions/pull-requests/set-automerge actions/milestones/edit actions/org-labels/list actions/org-labels/create
```

Expected: command succeeds.

- [ ] **Step 7: Run tests and help checks**

Run:

```bash
python3 -m unittest tests.test_tea_api -v
actions/pull-requests/set-automerge --help >/dev/null
actions/milestones/edit --help >/dev/null
actions/org-labels/create --help >/dev/null
```

Expected: tests PASS; help checks exit 0.

- [ ] **Step 8: Commit remaining actions**

Run:

```bash
git add actions/internal/tea_api.py actions/pull-requests actions/milestones actions/org-labels tests/test_tea_api.py
git commit -m "feat: add pull request milestone and org label actions"
```

Expected: commit succeeds.

---

### Task 4: Add action contract tests and top-level action documentation

**Files:**
- Create: `actions/README.md`
- Create: `tests/test_action_contracts.py`
- Modify: `README.md`

- [ ] **Step 1: Write failing action contract tests**

Create `tests/test_action_contracts.py`:

```python
import os
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


EXPECTED_ACTIONS = [
    "actions/issues/comment-edit",
    "actions/issues/lock",
    "actions/issues/unlock",
    "actions/issues/pin",
    "actions/issues/unpin",
    "actions/issues/reaction-add",
    "actions/issues/reaction-list",
    "actions/issues/dependency-add",
    "actions/issues/dependency-remove",
    "actions/issues/dependency-list",
    "actions/issues/dependency-all",
    "actions/issues/dependency-ready",
    "actions/issues/dependency-graph",
    "actions/pull-requests/set-automerge",
    "actions/milestones/edit",
    "actions/org-labels/list",
    "actions/org-labels/create",
]


REMOVED_SCRIPTS = [
    "scripts/tea-api",
    "scripts/tea-dep",
    "scripts/tea-issue-comment",
    "scripts/tea-issue-lock",
    "scripts/tea-issue-pin",
    "scripts/tea-issue-react",
    "scripts/tea-label-org",
    "scripts/tea-milestone-edit",
    "scripts/tea-pr-automerge",
    "scripts/tea-pr-draft",
    "scripts/tea-pr-reviewers",
]


class ActionContractTests(unittest.TestCase):
    def test_expected_actions_exist_and_are_executable(self):
        for relative in EXPECTED_ACTIONS:
            path = ROOT / relative
            with self.subTest(action=relative):
                self.assertTrue(path.exists(), f"{relative} should exist")
                self.assertTrue(os.access(path, os.X_OK), f"{relative} should be executable")

    def test_removed_scripts_do_not_exist(self):
        for relative in REMOVED_SCRIPTS:
            with self.subTest(script=relative):
                self.assertFalse((ROOT / relative).exists(), f"{relative} should be removed")

    def test_domain_readmes_exist(self):
        for relative in [
            "actions/README.md",
            "actions/issues/README.md",
            "actions/pull-requests/README.md",
            "actions/milestones/README.md",
            "actions/org-labels/README.md",
            "actions/internal/README.md",
        ]:
            with self.subTest(readme=relative):
                self.assertTrue((ROOT / relative).exists(), f"{relative} should exist")

    def test_no_action_uses_curl_or_jq(self):
        for relative in EXPECTED_ACTIONS:
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(action=relative):
                self.assertNotIn("curl", text)
                self.assertNotIn("jq", text)
```

- [ ] **Step 2: Run contract tests to verify they fail before scripts are removed**

Run:

```bash
python3 -m unittest tests.test_action_contracts -v
```

Expected: FAIL because old `scripts/tea-*` files still exist and `actions/README.md` is missing.

- [ ] **Step 3: Create top-level actions README**

Create `actions/README.md`:

```markdown
# Bundled actions

Bundled actions fill known Gitea/Forgejo gaps in the `tea` CLI. Prefer `tea` whenever it supports the workflow.

Action paths are relative to this installed plugin root. When executing an action for another repository, use the absolute action path while keeping the working directory in the target repository.

Example:

```bash
/path/to/tea-skills/actions/issues/dependency-ready
```

The action derives owner and repo from the target repository's `origin` remote.

## Domains

- [`issues/`](issues/README.md) — issue comment edit, moderation, reactions, dependencies
- [`pull-requests/`](pull-requests/README.md) — pull request auto-merge configuration
- [`milestones/`](milestones/README.md) — milestone edit
- [`org-labels/`](org-labels/README.md) — organization-level labels

## Private internals

`actions/internal/` contains private Python support code. Do not invoke it directly. Use domain actions and README files instead.
```

- [ ] **Step 4: Update top-level README**

Replace the `## Scripts` section through the end of the prerequisites list in `README.md` with:

```markdown
## Actions

Bundled actions cover API-only operations: features Gitea/Forgejo supports but the `tea` CLI does not expose cleanly. Actions supplement `tea`; they do not replace it.

See [`actions/README.md`](actions/README.md) and the domain README files for exact commands and arguments.

| Domain | Reference |
|---|---|
| Issues | `actions/issues/README.md` |
| Pull Requests | `actions/pull-requests/README.md` |
| Milestones | `actions/milestones/README.md` |
| Organization Labels | `actions/org-labels/README.md` |

### Bundled action invocation

Skill docs use `actions/<domain>/<action>` as a bundled plugin resource path. It refers to this plugin's `actions/` directory inside the installed plugin, not to an `actions/` directory in the user's current repository.

When executing from another project, resolve the action to the installed plugin root and run that absolute path while keeping the working directory in the target repository:

```bash
/path/to/tea-skills/actions/issues/dependency-ready
```

Do not require users to `cd` into this plugin or add `actions/` to `PATH`. Actions intentionally run from the target repository because the private Adapter derives owner and repo from that repository's git remote.

## Prerequisites

- [tea CLI](https://gitea.com/gitea/tea) configured with `tea login`
- Python 3
```

In the `## Structure` tree in `README.md`, replace the `scripts/` block with:

```markdown
├── actions/
│   ├── README.md
│   ├── internal/
│   │   ├── README.md
│   │   └── tea_api.py
│   ├── issues/
│   ├── pull-requests/
│   ├── milestones/
│   └── org-labels/
```

- [ ] **Step 5: Remove old scripts**

Run:

```bash
rm -rf scripts
```

Expected: `scripts/` no longer exists.

- [ ] **Step 6: Run contract tests**

Run:

```bash
python3 -m unittest tests.test_action_contracts -v
```

Expected: PASS.

- [ ] **Step 7: Commit action documentation and script removal**

Run:

```bash
git add README.md actions tests/test_action_contracts.py
git rm -r scripts
git commit -m "docs: document bundled actions"
```

Expected: commit succeeds.

---

### Task 5: Update skills and project guidance to reference actions

**Files:**
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `skills/create-pull/SKILL.md`
- Modify: `skills/review-pull/SKILL.md`
- Modify: `skills/merge-pull/SKILL.md`
- Modify: `skills/issue-moderation/SKILL.md`
- Modify: `skills/issue-comments/SKILL.md`
- Modify: `skills/issue-dependencies/SKILL.md`
- Modify: `skills/label-schemes/SKILL.md`
- Modify: `skills/milestones/SKILL.md`
- Modify: `skills/using-the-tea-api/SKILL.md`

- [ ] **Step 1: Write failing documentation scan**

Run:

```bash
rg -n "scripts/|tea-api|_api_|tea-pr-draft|tea-pr-reviewers|tea-pr-automerge|tea-dep|tea-issue-|tea-label-org|tea-milestone-edit" README.md AGENTS.md CLAUDE.md skills
```

Expected: matches appear. These matches are the stale docs to replace.

- [ ] **Step 2: Update project guidance**

In both `AGENTS.md` and `CLAUDE.md`, replace the current “Scripts for API Gaps” section with:

```markdown
### Actions for API Gaps

`actions/` contains bundled Python actions for Gitea/Forgejo features the tea CLI lacks. Skill docs refer to them as `actions/<domain>/<action>` following the bundled-resource convention: resolve that path relative to this installed plugin, then execute the absolute action path while keeping the working directory in the target repository. Do not require users to `cd` into the plugin root or put `actions/` on `PATH`.

Actions are action-specific and organized by domain folders. Domain README files document normal `tea` CLI commands first and bundled actions second. Prefer `tea` wherever it supports the workflow.

Private HTTP support lives in `actions/internal/tea_api.py`. It is stdlib-only Python and is not a user-facing Interface.
```

In both files, replace key conventions that mention scripts with:

```markdown
- Skills prefer `-o simple` for listing output; `--output json` only when parsing is necessary
- Issue dependencies use the semantic "A depends on B" (B blocks A), managed through bundled actions under `actions/issues/` since tea CLI has no dependency support
- In skill docs, `actions/<domain>/<action>` means the bundled plugin action path, not a path in the user's repo
- Labels are referenced by **name** in `tea issues` but by **ID** in `tea labels update/delete`
- Milestones are referenced by **name** in CLI but by **ID** in the API-backed milestone edit action
- All API-backed actions derive repo context from the git remote URL automatically
```

Replace “Adding a New Script” with:

```markdown
## Adding a New Action

1. Confirm the workflow cannot be handled cleanly by `tea`; if `tea` supports it, document the `tea` command instead.
2. Create an executable Python file under `actions/<domain>/<action>` with `#!/usr/bin/env python3`.
3. Use `actions/internal/tea_api.py` for API access; do not shell out to `curl` or `jq`.
4. Add or update the domain `actions/<domain>/README.md` with purpose, usage, arguments, and `tea` alternatives.
5. Make it executable: `chmod +x actions/<domain>/<action>`.
```

- [ ] **Step 3: Update issue skills**

In `skills/issue-moderation/SKILL.md`, replace the command sections with:

```markdown
Features not available in the tea CLI. For exact bundled action commands and arguments, see `actions/issues/README.md`.
```

In `skills/issue-comments/SKILL.md`, replace the Edit Comment API block with:

```markdown
## Edit Comment

The tea CLI can't edit comments. For the bundled action, see `actions/issues/README.md`.

The comment ID can be found in the JSON output of `tea issues <num> --comments` or via Forgejo/Gitea UI/API details.
```

In `skills/issue-dependencies/SKILL.md`, replace command examples and cross-repo direct API helper text with:

```markdown
"A depends on B" means B must be done first. B *blocks* A. The tea CLI has no dependency support. For bundled actions and exact arguments, see `actions/issues/README.md`.

Cross-repo dependencies are not supported by the bundled actions in this version.
```

- [ ] **Step 4: Update pull request skills**

In `skills/create-pull/SKILL.md`, replace the Draft PR section with:

```markdown
## WIP PR Convention

Use the normal tea CLI and prefix the title with `WIP:` when a Forgejo/Gitea workflow treats WIP titles as draft-like pull requests.

```bash
tea pulls create --title "WIP: Feature" --head feature-branch
tea pulls create --title "WIP: Feature" --head feature-branch --base develop
```
```

In `skills/review-pull/SKILL.md`, replace the Request Reviewers section with:

```markdown
## Request Reviewers

```bash
tea pulls edit 15 --add-reviewers user1,user2
tea pulls edit 15 --remove-reviewers user1
```
```

In `skills/review-pull/SKILL.md`, replace the Diff / Patch / Files and Reviews with Inline Comments API sections with:

```markdown
## Diff / Patch / Review Comments

```bash
tea pulls 15 --fields diff,patch
tea pulls review-comments 15
tea pulls resolve 123
tea pulls unresolve 123
```

For interactive inline review, use:

```bash
tea pulls review 15
```
```

In `skills/merge-pull/SKILL.md`, replace Auto-Merge and Mark Draft Ready sections with:

```markdown
## Auto-Merge

The tea CLI does not expose auto-merge configuration. For the bundled action, see `actions/pull-requests/README.md`.

## Mark WIP Ready

If this repository uses `WIP:` titles as draft-like pull requests, remove the prefix with tea:

```bash
tea pulls edit 15 --title "Feature"
```
```

- [ ] **Step 5: Update label, milestone, and API skills**

In `skills/label-schemes/SKILL.md`, replace the Organization-Level Labels command block with:

```markdown
## Organization-Level Labels

For organization-level label actions, see `actions/org-labels/README.md`.
```

In `skills/milestones/SKILL.md`, replace the Edit API command block with:

```markdown
## Edit

The tea CLI doesn't have a milestone edit command. For the bundled action, see `actions/milestones/README.md`.
```

Replace the body of `skills/using-the-tea-api/SKILL.md` after the frontmatter with:

```markdown
# Using the Tea API

Direct use of the internal Gitea/Forgejo HTTP Adapter is not a user-facing workflow.

Prefer the `tea` CLI for supported operations. For known CLI gaps, use the bundled action README files:

- `actions/issues/README.md`
- `actions/pull-requests/README.md`
- `actions/milestones/README.md`
- `actions/org-labels/README.md`

The private Adapter lives at `actions/internal/tea_api.py` and is used by bundled actions. Do not source or invoke it directly from user workflows.

The full Swagger docs remain available at `$BASE_URL/api/swagger` on your Gitea/Forgejo instance for manual investigation.
```

- [ ] **Step 6: Run documentation scan until stale references are gone**

Run:

```bash
rg -n "scripts/|tea-api|_api_|tea-pr-draft|tea-pr-reviewers|tea-pr-automerge|tea-dep|tea-issue-|tea-label-org|tea-milestone-edit" README.md AGENTS.md CLAUDE.md skills || true
```

Expected: no output.

- [ ] **Step 7: Commit skill documentation updates**

Run:

```bash
git add AGENTS.md CLAUDE.md skills
git commit -m "docs: route skills to bundled actions"
```

Expected: commit succeeds.

---

### Task 6: Final verification and integration-test handoff

**Files:**
- Modify: none unless verification exposes a bug.

- [ ] **Step 1: Run full unit tests**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: PASS.

- [ ] **Step 2: Run executable help smoke tests**

Run:

```bash
for action in \
  actions/issues/comment-edit \
  actions/issues/lock \
  actions/issues/unlock \
  actions/issues/pin \
  actions/issues/unpin \
  actions/issues/reaction-add \
  actions/issues/reaction-list \
  actions/issues/dependency-add \
  actions/issues/dependency-remove \
  actions/issues/dependency-list \
  actions/pull-requests/set-automerge \
  actions/milestones/edit \
  actions/org-labels/create; do
  "$action" --help >/dev/null
done
```

Expected: command exits 0.

- [ ] **Step 3: Run no-curl/no-jq scan**

Run:

```bash
rg -n "curl|jq|source .*tea-api|_api_" actions tests README.md AGENTS.md CLAUDE.md skills || true
```

Expected: no stale shell/API-helper matches. Matches in prose are acceptable only if they explicitly say the old helper is gone; prefer no matches.

- [ ] **Step 4: Check git status**

Run:

```bash
git status --short
```

Expected: clean working tree.

- [ ] **Step 5: Record integration-test checklist for the next operator**

Add this section to the final response or handoff, not to a committed file:

```markdown
Integration test checklist:

1. In a disposable Forgejo/Gitea repo, run `actions/issues/lock <issue>` then `actions/issues/unlock <issue>`.
2. Run `actions/issues/dependency-add <issue> <blocker>`, `actions/issues/dependency-list <issue>`, then `actions/issues/dependency-remove <issue> <blocker>`.
3. Run `actions/milestones/edit <milestone> --description "temporary integration test"`, then restore the description.
4. Run `actions/org-labels/list`; only run `actions/org-labels/create` against a disposable org or with explicit approval for a temporary label.
5. If a suitable PR exists, run `actions/pull-requests/set-automerge <pr> --enable --style squash`, then `actions/pull-requests/set-automerge <pr> --cancel`.
```

- [ ] **Step 6: Commit any verification fixes**

If Step 1, 2, or 3 required code or docs fixes, commit them:

```bash
git add actions tests README.md AGENTS.md CLAUDE.md skills
git commit -m "fix: address action migration verification"
```

Expected: skip this commit when the working tree is already clean.
