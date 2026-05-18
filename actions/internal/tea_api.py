#!/usr/bin/env python3
"""Private Gitea/Forgejo HTTP Adapter for bundled tea-skills actions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
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


def remote_host(remote_url: str) -> str | None:
    """Return the hostname from an HTTP(S), ssh://, or scp-style git remote URL."""
    remote = remote_url.strip()
    if not remote:
        return None

    if "://" in remote:
        return parse.urlparse(remote).hostname
    if ":" in remote and not remote.startswith("/"):
        location = remote.split(":", 1)[0]
        if "@" in location:
            location = location.rsplit("@", 1)[1]
        return location or None
    return None


def _repo_context_from_matching_remote(base_url: str) -> RepoContext | None:
    base_host = parse.urlparse(base_url).hostname
    if not base_host:
        return None

    try:
        completed = subprocess.run(
            ["git", "remote", "-v"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None

    seen_urls: set[str] = set()
    for line in completed.stdout.splitlines():
        columns = line.split()
        if len(columns) < 3 or columns[2] != "(fetch)":
            continue
        remote_url = columns[1]
        if remote_url in seen_urls:
            continue
        seen_urls.add(remote_url)
        if remote_host(remote_url) == base_host:
            owner, repo = parse_repo_remote(remote_url)
            return RepoContext(owner=owner, repo=repo)
    return None


def discover_repo_context(base_url: str | None = None) -> RepoContext:
    if base_url:
        matched = _repo_context_from_matching_remote(base_url)
        if matched:
            return matched

    try:
        completed = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise RepoContextError(f"failed to read git remote origin: {exc}") from exc
    if completed.returncode != 0:
        raise RepoContextError(completed.stderr.strip() or "failed to read git remote origin")
    owner, repo = parse_repo_remote(completed.stdout)
    return RepoContext(owner=owner, repo=repo)


class GiteaAdapter:
    def __init__(
        self,
        config: TeaConfig | None = None,
        opener: Callable[[request.Request], Any] | None = None,
    ):
        self.config = config or read_tea_config()
        self._opener = opener or request.urlopen

    @property
    def api_root(self) -> str:
        return f"{self.config.base_url}/api/v1"

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


def action_name_from_path(path: Path) -> str:
    """Return a stable actions/... path for an action executable."""
    resolved = Path(path)
    parts = resolved.parts
    if "actions" in parts:
        index = len(parts) - 1 - list(reversed(parts)).index("actions")
        return "/".join(parts[index:])
    return str(resolved)


def audit_action(
    action: str,
    argv: list[str],
    exit_code: int,
    phase: str = "finish",
    error: str | None = None,
) -> None:
    """Append an action audit event when TEA_SKILLS_AUDIT_LOG is set."""
    log_path = os.environ.get("TEA_SKILLS_AUDIT_LOG")
    if not log_path or os.environ.get("TEA_SKILLS_AUDIT_DISABLE") == "1":
        return

    event: dict[str, Any] = {
        "source": "tea-skills-action",
        "action": action,
        "argv": list(argv),
        "cwd": os.getcwd(),
        "pid": os.getpid(),
        "phase": phase,
        "exit_code": exit_code,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if error:
        event["error"] = error

    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


def run_action(action_file: Path, argv: list[str], main: Callable[[list[str]], int]) -> int:
    """Run an action main function and record its audited finish event."""
    action = action_name_from_path(action_file)
    try:
        exit_code = int(main(argv))
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        audit_action(action=action, argv=argv, exit_code=code)
        raise
    except Exception as exc:
        audit_action(
            action=action,
            argv=argv,
            exit_code=1,
            error=f"{exc.__class__.__name__}: {exc}",
        )
        raise
    audit_action(action=action, argv=argv, exit_code=exit_code)
    return exit_code
