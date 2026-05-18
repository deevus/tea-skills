#!/usr/bin/env python3
"""Private Gitea/Forgejo HTTP Adapter for bundled tea-skills actions."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Callable, Mapping
from urllib import parse, request
from urllib.error import HTTPError, URLError

try:
    from .vendor import yaml as vendored_yaml
except ImportError:
    from vendor import yaml as vendored_yaml


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
class TeaLogin:
    name: str
    token: str
    base_url: str
    default: bool = False


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


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)


def read_tea_logins(path: Path | None = None) -> list[TeaLogin]:
    cfg_path = path or config_path()
    try:
        text = cfg_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise TeaConfigError(f"tea config not found at {cfg_path}; run tea login first") from exc

    try:
        data = vendored_yaml.safe_load(text)
    except vendored_yaml.YAMLError as exc:
        raise TeaConfigError(f"failed to parse tea config at {cfg_path}: {exc}") from exc

    raw_logins = data.get("logins") if isinstance(data, dict) else None
    if not isinstance(raw_logins, list) or not raw_logins:
        raise TeaConfigError(f"tea config at {cfg_path} does not contain logins")

    logins: list[TeaLogin] = []
    for index, raw_login in enumerate(raw_logins, start=1):
        if not isinstance(raw_login, dict):
            raise TeaConfigError(f"tea config login #{index} is not a mapping")
        name = raw_login.get("name")
        token = raw_login.get("token")
        url = raw_login.get("url")
        if not name:
            raise TeaConfigError(f"tea config login #{index} does not contain a name")
        if not token:
            raise TeaConfigError(f"tea config login {name!r} does not contain a token")
        if not url:
            raise TeaConfigError(f"tea config login {name!r} does not contain a url")
        logins.append(
            TeaLogin(
                name=str(name),
                token=str(token),
                base_url=str(url).rstrip("/"),
                default=_truthy(raw_login.get("default", False)),
            )
        )
    return logins


def _available_login_names(logins: list[TeaLogin]) -> str:
    return ", ".join(login.name for login in logins) or "none"


def _login_config(login: TeaLogin) -> TeaConfig:
    return TeaConfig(token=login.token, base_url=login.base_url)


def _select_login_by_name(logins: list[TeaLogin], name: str) -> TeaLogin:
    for login in logins:
        if login.name == name:
            return login
    raise TeaConfigError(f"unknown tea login {name!r}; available logins: {_available_login_names(logins)}")


def _select_login_by_remote_host(logins: list[TeaLogin], remote_url: str) -> TeaLogin:
    host = remote_host(remote_url)
    if not host:
        raise TeaConfigError(f"cannot determine host from git remote URL: {remote_url}")
    matches = [login for login in logins if parse.urlparse(login.base_url).hostname == host]
    if not matches:
        raise TeaConfigError(
            f"git remote host {host} does not match any tea login; "
            f"available logins: {_available_login_names(logins)}. Use --login <name> or run tea login add."
        )
    if len(matches) > 1:
        raise TeaConfigError(
            f"git remote host {host} matches multiple tea logins: {_available_login_names(matches)}. "
            "Use --login <name>."
        )
    return matches[0]


def _remote_urls_from_git() -> dict[str, str]:
    try:
        completed = subprocess.run(
            ["git", "remote", "-v"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError:
        return {}
    if completed.returncode != 0:
        return {}

    urls: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        columns = line.split()
        if len(columns) < 3 or columns[2] != "(fetch)":
            continue
        urls.setdefault(columns[0], columns[1])
    return urls


def _select_login_by_configured_remotes(logins: list[TeaLogin]) -> TeaLogin | None:
    login_hosts = defaultdict(list)
    for login in logins:
        host = parse.urlparse(login.base_url).hostname
        if host:
            login_hosts[host].append(login)

    matches: dict[str, tuple[str, TeaLogin]] = {}
    ambiguous_same_host: dict[str, list[TeaLogin]] = {}
    for remote_name, remote_url in _remote_urls_from_git().items():
        host = remote_host(remote_url)
        if not host or host not in login_hosts:
            continue
        host_logins = login_hosts[host]
        if len(host_logins) > 1:
            ambiguous_same_host[host] = host_logins
            continue
        matches[host] = (remote_name, host_logins[0])

    if ambiguous_same_host:
        host, host_logins = next(iter(ambiguous_same_host.items()))
        raise TeaConfigError(
            f"configured git remote host {host} matches multiple tea logins: "
            f"{_available_login_names(host_logins)}. Use --login <name>."
        )
    if len(matches) > 1:
        details = ", ".join(f"{login.name} for remote {remote}" for remote, login in matches.values())
        raise TeaConfigError(
            f"multiple tea logins match configured git remotes: {details}. Use --login <name> or --remote <name>."
        )
    if len(matches) == 1:
        return next(iter(matches.values()))[1]
    return None


def _select_default_login(logins: list[TeaLogin]) -> TeaLogin:
    for login in logins:
        if login.default:
            return login
    return logins[0]


def read_tea_config(
    path: Path | None = None,
    *,
    login: str | None = None,
    remote_url: str | None = None,
) -> TeaConfig:
    logins = read_tea_logins(path)
    if login:
        return _login_config(_select_login_by_name(logins, login))
    if remote_url:
        return _login_config(_select_login_by_remote_host(logins, remote_url))

    matched = _select_login_by_configured_remotes(logins)
    if matched:
        return _login_config(matched)
    return _login_config(_select_default_login(logins))


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


def _remote_list(remotes: list[tuple[str, str]]) -> str:
    if not remotes:
        return "none"
    return "; ".join(f"{name}: {url}" for name, url in remotes)


def _repo_example(remotes: list[tuple[str, str]]) -> str | None:
    for _, remote_url in remotes:
        try:
            owner, repo = parse_repo_remote(remote_url)
        except RepoContextError:
            continue
        return f"--repo {owner}/{repo}"
    return None


def _corrective_examples(remotes: list[tuple[str, str]]) -> str:
    examples: list[str] = []
    if remotes:
        examples.append(f"--remote {remotes[0][0]}")
    repo_example = _repo_example(remotes)
    if repo_example:
        examples.append(repo_example)
    examples.append("--login <name>")
    return ", ".join(examples)


def _ambiguous_matching_remotes_error(base_host: str, matches: list[tuple[str, str]]) -> str:
    return (
        f"multiple git remotes match tea backend host {base_host}: {_remote_list(matches)}. "
        f"Rerun with one of: {_corrective_examples(matches)}."
    )


def _no_matching_remotes_error(base_host: str, remotes: list[tuple[str, str]]) -> str:
    return (
        f"no git remotes match tea backend host {base_host}; configured fetch remotes: {_remote_list(remotes)}. "
        f"Rerun with one of: {_corrective_examples(remotes)}."
    )


def _repo_context_from_matching_remote(base_url: str) -> RepoContext:
    base_host = parse.urlparse(base_url).hostname
    if not base_host:
        raise RepoContextError(f"cannot determine host from tea base URL: {base_url}")

    try:
        completed = subprocess.run(
            ["git", "remote", "-v"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise RepoContextError(f"failed to list git remotes: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or "failed to list git remotes"
        raise RepoContextError(detail)

    remotes: list[tuple[str, str]] = []
    matches: list[tuple[str, str]] = []
    for line in completed.stdout.splitlines():
        columns = line.split()
        if len(columns) < 3 or columns[2] != "(fetch)":
            continue
        remote_name = columns[0]
        remote_url = columns[1]
        remotes.append((remote_name, remote_url))
        if remote_host(remote_url) == base_host:
            matches.append((remote_name, remote_url))

    if len(matches) == 1:
        owner, repo = parse_repo_remote(matches[0][1])
        return RepoContext(owner=owner, repo=repo)
    if len(matches) > 1:
        raise RepoContextError(_ambiguous_matching_remotes_error(base_host, matches))
    raise RepoContextError(_no_matching_remotes_error(base_host, remotes))


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
