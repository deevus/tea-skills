from __future__ import annotations

import json
import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from tests.e2e.tea_suite.repository_scope_args import without_repository_scope_args

DEFAULT_FIXTURE_PACK = Path(__file__).resolve().parent / "fixtures" / "tea" / "fixture-pack-v1"
DEFAULT_STATE: dict[str, Any] = {"next_issue_number": 1, "issues": []}

_ISSUES_ALIASES = {"issues", "issue", "i"}
_CREATE_ALIASES = {"create", "c"}
_LIST_ALIASES = {"list", "ls", "l"}
_SHOW_ALIASES = {"show", "s"}


@dataclass(frozen=True)
class MockTea:
    root: Path
    bin_dir: Path
    executable: Path
    state_path: Path
    fixture_pack_dir: Path

    def env_with_path(self, base_env: Mapping[str, str] | None = None) -> dict[str, str]:
        env = dict(base_env or {})
        existing_path = env.get("PATH", os.environ.get("PATH", ""))
        env["PATH"] = str(self.bin_dir) if not existing_path else f"{self.bin_dir}{os.pathsep}{existing_path}"
        env["TEA_SKILLS_MOCK_TEA_STATE"] = str(self.state_path)
        env["TEA_SKILLS_MOCK_TEA_FIXTURES"] = str(self.fixture_pack_dir)
        return env

    def load_state(self) -> dict[str, Any]:
        return load_mock_tea_state(self.state_path)


class MockTeaUsageError(ValueError):
    pass


def create_mock_tea(root: Path, fixture_pack_dir: Path = DEFAULT_FIXTURE_PACK) -> MockTea:
    root = root.resolve()
    fixture_pack_dir = fixture_pack_dir.resolve()
    bin_dir = root / "bin"
    state_path = root / "state.json"
    executable = bin_dir / "tea"

    bin_dir.mkdir(parents=True, exist_ok=True)
    save_mock_tea_state(state_path, dict(DEFAULT_STATE))

    module_root = Path(__file__).resolve().parents[3]
    executable.write_text(
        f"""#!{sys.executable}
from __future__ import annotations

import sys

sys.path.insert(0, {str(module_root)!r})
from tests.e2e.tea_suite.mock_tea import main

raise SystemExit(main(sys.argv[1:]))
""",
        encoding="utf-8",
    )
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    return MockTea(
        root=root,
        bin_dir=bin_dir,
        executable=executable,
        state_path=state_path,
        fixture_pack_dir=fixture_pack_dir,
    )


def load_mock_tea_state(state_path: Path) -> dict[str, Any]:
    return json.loads(Path(state_path).read_text(encoding="utf-8"))


def save_mock_tea_state(state_path: Path, state: dict[str, Any]) -> None:
    Path(state_path).write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    state_path = Path(os.environ["TEA_SKILLS_MOCK_TEA_STATE"])
    fixture_pack_dir = Path(os.environ.get("TEA_SKILLS_MOCK_TEA_FIXTURES", str(DEFAULT_FIXTURE_PACK)))

    try:
        stdout, stderr, exit_code = run_mock_tea(
            args, state_path=state_path, fixture_pack_dir=fixture_pack_dir, cwd=Path.cwd()
        )
    except MockTeaUsageError as error:
        stdout, stderr, exit_code = "", f"mock tea: {error}\n", 2

    if stdout:
        sys.stdout.write(stdout)
    if stderr:
        sys.stderr.write(stderr)
    return exit_code


def run_mock_tea(
    argv: list[str],
    *,
    state_path: Path,
    fixture_pack_dir: Path,
    cwd: Path,
) -> tuple[str, str, int]:
    if not argv:
        return "mock tea\n", "", 0

    if argv[0] == "logins":
        return _render(fixture_pack_dir, "logins.stdout.txt"), "", 0

    if argv[0] == "login":
        return _run_login(argv[1:], fixture_pack_dir=fixture_pack_dir)

    if argv[0] in _ISSUES_ALIASES:
        return _run_issues(argv[1:], state_path=state_path, fixture_pack_dir=fixture_pack_dir, cwd=cwd)

    return "", f"mock tea: unsupported command: {' '.join(argv)}\n", 2


def _run_login(argv: list[str], *, fixture_pack_dir: Path) -> tuple[str, str, int]:
    if not argv or argv[0] != "list":
        return "", f"mock tea: unsupported login command: {' '.join(argv)}\n", 2

    output = _flag_value(argv[1:], "-o", "--output")
    if output == "csv":
        return _render(fixture_pack_dir, "login/list.csv.stdout.txt"), "", 0
    return _render(fixture_pack_dir, "logins.stdout.txt"), "", 0


def _run_issues(
    argv: list[str],
    *,
    state_path: Path,
    fixture_pack_dir: Path,
    cwd: Path,
) -> tuple[str, str, int]:
    argv = without_repository_scope_args(argv)

    if not argv:
        return _issues_list(state_path=state_path, fixture_pack_dir=fixture_pack_dir)

    command = argv[0]
    rest = argv[1:]
    if command in _CREATE_ALIASES:
        return _issues_create(rest, state_path=state_path, fixture_pack_dir=fixture_pack_dir, cwd=cwd)
    if command in _LIST_ALIASES:
        return _issues_list(state_path=state_path, fixture_pack_dir=fixture_pack_dir)
    if command in _SHOW_ALIASES:
        return _issues_show(rest, state_path=state_path, fixture_pack_dir=fixture_pack_dir)
    if command.isdigit():
        return _issues_show([command] + rest, state_path=state_path, fixture_pack_dir=fixture_pack_dir)

    for index, token in enumerate(argv):
        if token in _CREATE_ALIASES:
            reordered = argv[:index] + argv[index + 1 :]
            return _issues_create(reordered, state_path=state_path, fixture_pack_dir=fixture_pack_dir, cwd=cwd)

    return "", f"mock tea: unsupported issues command: {' '.join(argv)}\n", 2


def _issues_create(
    argv: list[str],
    *,
    state_path: Path,
    fixture_pack_dir: Path,
    cwd: Path,
) -> tuple[str, str, int]:
    title = _flag_value(argv, "--title", "-t")
    body = _flag_value(argv, "--description", "-d") or ""
    body_path = _flag_value(argv, "--body")
    if body_path:
        candidate = (cwd / body_path).resolve()
        try:
            candidate.relative_to(cwd.resolve())
        except ValueError as error:
            raise MockTeaUsageError(f"body path escapes workspace: {body_path}") from error
        if candidate.exists():
            body = candidate.read_text(encoding="utf-8")
        elif not body:
            body = body_path

    if not title:
        raise MockTeaUsageError("issues create requires --title")

    state = load_mock_tea_state(state_path)
    number = int(state["next_issue_number"])
    issue = {"number": number, "title": title, "body": body, "state": "open"}
    state["next_issue_number"] = number + 1
    state["issues"].append(issue)
    save_mock_tea_state(state_path, state)

    return _render(fixture_pack_dir, "issues/create.success.stdout.txt", issue), "", 0


def _issues_list(*, state_path: Path, fixture_pack_dir: Path) -> tuple[str, str, int]:
    state = load_mock_tea_state(state_path)
    issues = state.get("issues", [])
    if not issues:
        return _render(fixture_pack_dir, "issues/list.empty.simple.stdout.txt"), "", 0
    issues_simple = "".join(f"#{issue['number']} {issue['title']} {issue['state']}\n" for issue in issues)
    return _render(fixture_pack_dir, "issues/list.simple.stdout.txt", {"issues_simple": issues_simple}), "", 0


def _issues_show(argv: list[str], *, state_path: Path, fixture_pack_dir: Path) -> tuple[str, str, int]:
    if not argv or not argv[0].isdigit():
        raise MockTeaUsageError("issues show requires an issue number")
    number = int(argv[0])
    state = load_mock_tea_state(state_path)
    for issue in state.get("issues", []):
        if issue.get("number") == number:
            return _render(fixture_pack_dir, "issues/show.stdout.txt", issue), "", 0
    return "", f"mock tea: issue not found: {number}\n", 1


def _flag_value(argv: list[str], *names: str) -> str | None:
    for index, token in enumerate(argv):
        for name in names:
            if token == name and index + 1 < len(argv):
                return argv[index + 1]
            prefix = f"{name}="
            if token.startswith(prefix):
                return token[len(prefix) :]
    return None


def _render(fixture_pack_dir: Path, relative_path: str, context: Mapping[str, Any] | None = None) -> str:
    template = (fixture_pack_dir / relative_path).read_text(encoding="utf-8")
    return template.format(**dict(context or {}))


__all__ = ["MockTea", "create_mock_tea", "load_mock_tea_state", "main", "run_mock_tea"]
