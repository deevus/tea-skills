# Mock Tea Dokimasia E2E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the live Forgejo/real-`tea` agent E2E with an env-gated AI E2E that runs against a versioned, stateful mock `tea` executable through Dokimasia.

**Architecture:** Keep Dokimasia generic by using its existing PATH spy around a project-owned mock executable: the test prepends mock `tea` to PATH, then `cmd.spy("tea")` wraps that mock rather than the host `tea`. Keep all `tea` behavior, local state, and fixture pack semantics in `tests/e2e/tea_suite/`, with text output fixtures under a versioned `fixture-pack-v1/` directory.

**Tech Stack:** Python 3.10+, pytest, Dokimasia `doki_factory`/`cmd.spy`, uv dependency groups with committed `uv.lock`, JSON local state, plain text fixture templates.

---

## File Structure

- Modify `pyproject.toml`
  - Add an `e2e` dependency group for pytest and Dokimasia from `git+https://github.com/deevus/dokimasia.git`. Skill actions remain dependency-free; this dependency group is contributor/test-only.
- Create `uv.lock`
  - Commit uv's resolved lockfile so E2E test dependencies are reproducible.
- Create `tests/e2e/tea_suite/mock_tea.py`
  - Owns `MockTea` dataclass, `create_mock_tea(...)`, state loading, fixture rendering, and the mock `tea` CLI entrypoint used by generated executable wrappers.
- Create `tests/e2e/tea_suite/fixtures/tea/fixture-pack-v1/manifest.json`
  - Documents fixture pack version and output compatibility.
- Create text fixtures under `tests/e2e/tea_suite/fixtures/tea/fixture-pack-v1/`
  - Stores maintainable stdout/stderr templates in git.
- Modify `tests/e2e/test_agent_e2e.py`
  - Replace real Forgejo provision/cleanup and `require_executable("tea")` with local workspace + mock `tea` setup.
  - Keep `TEA_SKILLS_E2E=1` gating because the test still performs AI inference.
- Modify `tests/e2e/test_harness_unit.py`
  - Remove tests for live Forgejo provision/API verification from the E2E harness.
  - Add unit tests for mock `tea` generation, command behavior, state mutation, and matcher compatibility.
- Modify `tests/e2e/README.md`
  - Describe mock-`tea` E2E, fixture pack maintenance, and env flag usage.
- Delete `tests/e2e/tea_suite/provision.py`
  - No live Forgejo provisioning remains in this E2E harness.
- Delete `tests/e2e/tea_suite/verify_forgejo.py`
  - Mock state replaces remote Forgejo state verification.

## Task 0: Add explicit E2E test dependencies

**Files:**
- Modify: `pyproject.toml`
- Create: `uv.lock`

- [ ] **Step 1: Add an e2e dependency group to `pyproject.toml`**

Replace `pyproject.toml` with:

```toml
[dependency-groups]
e2e = [
    "dokimasia @ git+https://github.com/deevus/dokimasia.git",
    "pytest",
]

[tool.ruff]
line-length = 120
target-version = "py310"
```

- [ ] **Step 2: Generate `uv.lock`**

Run:

```bash
uv lock
```

Expected: PASS and `uv.lock` exists.

- [ ] **Step 3: Verify the dependency group can run tests**

Run:

```bash
uv run --group e2e pytest tests/e2e/test_harness_unit.py -v
```

Expected: current tests run with Dokimasia and pytest resolved from `uv.lock`. Failures caused by missing mock-tea implementation are acceptable until later tasks; dependency resolution failures are not acceptable.

- [ ] **Step 4: Commit dependency metadata**

```bash
git add pyproject.toml uv.lock
git commit -m "test: add locked e2e test dependencies"
```

## Task 1: Add mock tea unit tests and fixture pack files

**Files:**
- Modify: `tests/e2e/test_harness_unit.py`
- Create: `tests/e2e/tea_suite/fixtures/tea/fixture-pack-v1/manifest.json`
- Create: `tests/e2e/tea_suite/fixtures/tea/fixture-pack-v1/logins.stdout.txt`
- Create: `tests/e2e/tea_suite/fixtures/tea/fixture-pack-v1/issues/create.success.stdout.txt`
- Create: `tests/e2e/tea_suite/fixtures/tea/fixture-pack-v1/issues/list.empty.simple.stdout.txt`
- Create: `tests/e2e/tea_suite/fixtures/tea/fixture-pack-v1/issues/list.simple.stdout.txt`
- Create: `tests/e2e/tea_suite/fixtures/tea/fixture-pack-v1/issues/show.stdout.txt`

- [ ] **Step 1: Add failing mock tea unit tests**

Append these imports near the top of `tests/e2e/test_harness_unit.py`:

```python
import json
import subprocess
```

Remove these imports from `tests/e2e/test_harness_unit.py`:

```python
from actions.internal.tea_api import TeaConfig
from tests.e2e.tea_suite import verify_forgejo
from tests.e2e.tea_suite.provision import assert_safe_e2e_resource
```

Append these tests to `tests/e2e/test_harness_unit.py`:

```python
def test_create_mock_tea_builds_executable_state_and_env(tmp_path):
    from tests.e2e.tea_suite.mock_tea import create_mock_tea

    mock_tea = create_mock_tea(tmp_path / "mock-tea")

    assert mock_tea.executable.exists()
    assert mock_tea.executable.name == "tea"
    assert mock_tea.state_path.exists()
    assert json.loads(mock_tea.state_path.read_text(encoding="utf-8")) == {"next_issue_number": 1, "issues": []}

    env = mock_tea.env_with_path({"PATH": "/usr/bin"})
    assert env["PATH"].split(os.pathsep)[0] == str(mock_tea.bin_dir)
    assert env["TEA_SKILLS_MOCK_TEA_STATE"] == str(mock_tea.state_path)
    assert env["TEA_SKILLS_MOCK_TEA_FIXTURES"] == str(mock_tea.fixture_pack_dir)


def test_mock_tea_creates_issue_and_renders_fixture_output(tmp_path):
    from tests.e2e.tea_suite.mock_tea import create_mock_tea, load_mock_tea_state

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    mock_tea = create_mock_tea(tmp_path / "mock-tea")

    completed = subprocess.run(
        [
            str(mock_tea.executable),
            "issues",
            "create",
            "--title",
            "Mocked issue",
            "--description",
            "Body marker",
        ],
        cwd=workspace,
        env=mock_tea.env_with_path(os.environ),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.stderr == ""
    assert "#1 Mocked issue" in completed.stdout
    assert load_mock_tea_state(mock_tea.state_path) == {
        "next_issue_number": 2,
        "issues": [
            {"number": 1, "title": "Mocked issue", "body": "Body marker", "state": "open"},
        ],
    }


def test_mock_tea_reads_body_from_body_flag_path(tmp_path):
    from tests.e2e.tea_suite.mock_tea import create_mock_tea, load_mock_tea_state

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "issue-body.md").write_text("Body from file\n", encoding="utf-8")
    mock_tea = create_mock_tea(tmp_path / "mock-tea")

    completed = subprocess.run(
        [str(mock_tea.executable), "issue", "c", "--title", "File body", "--body", "issue-body.md"],
        cwd=workspace,
        env=mock_tea.env_with_path(os.environ),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert completed.returncode == 0
    state = load_mock_tea_state(mock_tea.state_path)
    assert state["issues"][0]["body"] == "Body from file\n"


def test_mock_tea_lists_and_shows_issues_from_state(tmp_path):
    from tests.e2e.tea_suite.mock_tea import create_mock_tea

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    mock_tea = create_mock_tea(tmp_path / "mock-tea")
    env = mock_tea.env_with_path(os.environ)

    subprocess.run(
        [str(mock_tea.executable), "issues", "create", "--title", "Visible", "--description", "Visible body"],
        cwd=workspace,
        env=env,
        check=True,
    )
    listed = subprocess.run(
        [str(mock_tea.executable), "issues", "list", "-o", "simple"],
        cwd=workspace,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        check=False,
    )
    shown = subprocess.run(
        [str(mock_tea.executable), "issues", "show", "1"],
        cwd=workspace,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        check=False,
    )

    assert listed.returncode == 0
    assert "#1 Visible open" in listed.stdout
    assert shown.returncode == 0
    assert "Title: Visible" in shown.stdout
    assert "Visible body" in shown.stdout
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run --group e2e pytest tests/e2e/test_harness_unit.py -v
```

Expected: FAIL because `tests.e2e.tea_suite.mock_tea` and fixture files do not exist yet, and deleted imports/tests have not been cleaned up.

- [ ] **Step 3: Create versioned fixture pack files**

Create `tests/e2e/tea_suite/fixtures/tea/fixture-pack-v1/manifest.json`:

```json
{
  "fixture_pack": "fixture-pack-v1",
  "tea_cli_compatibility": "mocked tea issue workflow output for tea-skills E2E",
  "template_syntax": "Python str.format placeholders",
  "commands": {
    "logins": {"stdout": "logins.stdout.txt", "exit_code": 0},
    "issues create": {"stdout": "issues/create.success.stdout.txt", "exit_code": 0, "mutates": "create_issue"},
    "issues list -o simple": {"stdout": "issues/list.simple.stdout.txt", "exit_code": 0},
    "issues show": {"stdout": "issues/show.stdout.txt", "exit_code": 0}
  }
}
```

Create `tests/e2e/tea_suite/fixtures/tea/fixture-pack-v1/logins.stdout.txt`:

```text
mock-forgejo https://mock.invalid
```

Create `tests/e2e/tea_suite/fixtures/tea/fixture-pack-v1/issues/create.success.stdout.txt`:

```text
#{number} {title}
```

Create `tests/e2e/tea_suite/fixtures/tea/fixture-pack-v1/issues/list.empty.simple.stdout.txt`:

```text
No issues found.
```

Create `tests/e2e/tea_suite/fixtures/tea/fixture-pack-v1/issues/list.simple.stdout.txt`:

```text
{issues_simple}
```

Create `tests/e2e/tea_suite/fixtures/tea/fixture-pack-v1/issues/show.stdout.txt`:

```text
Number: {number}
Title: {title}
State: {state}

{body}
```

- [ ] **Step 4: Commit fixture tests and fixture pack**

```bash
git add tests/e2e/test_harness_unit.py tests/e2e/tea_suite/fixtures/tea/fixture-pack-v1
git commit -m "test: specify mock tea fixture pack"
```

## Task 2: Implement project-owned mock tea executable

**Files:**
- Create: `tests/e2e/tea_suite/mock_tea.py`
- Test: `tests/e2e/test_harness_unit.py`

- [ ] **Step 1: Create `tests/e2e/tea_suite/mock_tea.py`**

```python
from __future__ import annotations

import json
import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

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


def create_mock_tea(root: Path, fixture_pack_dir: Path = DEFAULT_FIXTURE_PACK) -> MockTea:
    root = root.resolve()
    fixture_pack_dir = fixture_pack_dir.resolve()
    bin_dir = root / "bin"
    state_path = root / "state.json"
    executable = bin_dir / "tea"

    bin_dir.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(DEFAULT_STATE, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    module_root = Path(__file__).resolve().parents[3]
    executable.write_text(
        f"""#!{sys.executable}
from __future__ import annotations

import sys
from pathlib import Path

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
        stdout, stderr, exit_code = run_mock_tea(args, state_path=state_path, fixture_pack_dir=fixture_pack_dir, cwd=Path.cwd())
    except MockTeaUsageError as error:
        stdout, stderr, exit_code = "", f"mock tea: {error}\n", 2

    if stdout:
        sys.stdout.write(stdout)
    if stderr:
        sys.stderr.write(stderr)
    return exit_code


class MockTeaUsageError(ValueError):
    pass


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

    if argv[0] in _ISSUES_ALIASES:
        return _run_issues(argv[1:], state_path=state_path, fixture_pack_dir=fixture_pack_dir, cwd=cwd)

    return "", f"mock tea: unsupported command: {' '.join(argv)}\n", 2


def _run_issues(
    argv: list[str],
    *,
    state_path: Path,
    fixture_pack_dir: Path,
    cwd: Path,
) -> tuple[str, str, int]:
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

    # Accept tea issue --title T create style by searching for the create alias later.
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
    body = _flag_value(argv, "--description", "--body", "-d") or ""
    body_path = _flag_value(argv, "--body")
    if body_path:
        candidate = (cwd / body_path).resolve()
        try:
            candidate.relative_to(cwd.resolve())
        except ValueError as error:
            raise MockTeaUsageError(f"body path escapes workspace: {body_path}") from error
        if candidate.exists():
            body = candidate.read_text(encoding="utf-8")

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
```

- [ ] **Step 2: Run mock tea unit tests**

Run:

```bash
uv run --group e2e pytest tests/e2e/test_harness_unit.py -v
```

Expected: PASS for the new mock tea tests, except any old live Forgejo unit tests still present should fail until removed in Task 4.

- [ ] **Step 3: Commit mock tea implementation**

```bash
git add tests/e2e/tea_suite/mock_tea.py tests/e2e/test_harness_unit.py
git commit -m "test: add stateful mock tea executable"
```

## Task 3: Replace live Forgejo E2E with env-gated mock tea E2E

**Files:**
- Modify: `tests/e2e/test_agent_e2e.py`

- [ ] **Step 1: Replace live Forgejo imports and fixtures**

In `tests/e2e/test_agent_e2e.py`, remove these imports:

```python
from dokimasia.suite.env import require_executable
from tests.e2e.tea_suite.provision import ForgejoRun, cleanup_run, create_org_and_repo
from tests.e2e.tea_suite.verify_forgejo import list_issues
```

Add these imports:

```python
from dataclasses import dataclass

from tests.e2e.tea_suite.mock_tea import MockTea, create_mock_tea
```

Delete the `e2e_real_tea()` function entirely.

Add this dataclass after `ISSUE_CREATE`:

```python
@dataclass(frozen=True)
class MockTeaRun:
    run_id: str
    workspace: Path
    artifact_dir: Path
    tea: MockTea
```

Replace the `forgejo_run` fixture with:

```python
@pytest.fixture
def mock_tea_run(live_run_id: str) -> MockTeaRun:
    root = e2e_run_root(live_run_id)
    workspace = root / "workspace" / "repo"
    artifact_dir = root / "artifacts"
    workspace.mkdir(parents=True, exist_ok=True)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (workspace / "AGENTS.md").write_text(
        "# Repository context\n\nThis repository is hosted on Forgejo. Use tea for issue workflows.\n",
        encoding="utf-8",
    )
    return MockTeaRun(
        run_id=live_run_id,
        workspace=workspace,
        artifact_dir=artifact_dir,
        tea=create_mock_tea(root / "mock-tea"),
    )
```

- [ ] **Step 2: Update the E2E test body to assert mock state**

Replace `test_create_issue_from_body_file_with_pytest_dokimasia_api` with:

```python
def test_create_issue_from_body_file_with_pytest_dokimasia_api(doki_factory, mock_tea_run: MockTeaRun):
    title = issue_title_for_run(mock_tea_run.run_id)
    body = issue_body_for_run(mock_tea_run.run_id)
    doki = doki_factory(
        agent=make_agent_adapter(),
        workspace=mock_tea_run.workspace,
        artifact_dir=mock_tea_run.artifact_dir,
        run_id=mock_tea_run.run_id,
        env=mock_tea_run.tea.env_with_path(os.environ),
        spies=[TEA],
    )
    doki.write_file("issue-body.md", body)

    result = doki.run(
        f'Create a Forgejo issue titled "{title}".\nUse issue-body.md as the body.',
        artifact_name="create issue from body file",
    )

    assert result.ok, result.failure_summary
    assert result.has_skill_loaded("create-issue")
    assert_command_ran(result, ISSUE_CREATE, times=1)
    assert len(result.commands) <= 12
    assert_single_issue_matches(mock_tea_run.tea.load_state()["issues"], title=title, body=body)
```

- [ ] **Step 3: Update E2E skip reason**

Replace the skip reason text in `pytestmark` with:

```python
reason="set TEA_SKILLS_E2E=1 to run AI-backed mock tea E2E tests",
```

- [ ] **Step 4: Run non-live tests**

Run:

```bash
uv run --group e2e pytest tests/e2e/test_harness_unit.py tests/e2e/test_agent_e2e.py -v
```

Expected: PASS with `tests/e2e/test_agent_e2e.py` skipped unless `TEA_SKILLS_E2E=1` is set.

- [ ] **Step 5: Commit E2E replacement**

```bash
git add tests/e2e/test_agent_e2e.py
git commit -m "test: run agent e2e against mock tea"
```

## Task 4: Remove live Forgejo E2E helpers and stale unit tests

**Files:**
- Delete: `tests/e2e/tea_suite/provision.py`
- Delete: `tests/e2e/tea_suite/verify_forgejo.py`
- Modify: `tests/e2e/test_harness_unit.py`

- [ ] **Step 1: Delete live Forgejo helper files**

```bash
rm tests/e2e/tea_suite/provision.py tests/e2e/tea_suite/verify_forgejo.py
```

- [ ] **Step 2: Remove stale live helper unit tests**

Delete these tests from `tests/e2e/test_harness_unit.py`:

```python
def test_live_e2e_requires_tea_through_dokimasia_env_helper():
    ...


def test_safe_e2e_resource_policy_requires_suite_prefix_and_run_id():
    ...


def test_list_issues_uses_project_owned_forgejo_api_request():
    ...


def test_list_issues_returns_empty_list_for_non_list_response():
    ...
```

Also remove any imports that only supported those tests:

```python
from actions.internal.tea_api import TeaConfig
from tests.e2e import test_agent_e2e
from tests.e2e.tea_suite import verify_forgejo
from tests.e2e.tea_suite.provision import assert_safe_e2e_resource
```

Keep `from tests.e2e import test_agent_e2e` if other tests in the file still use it.

- [ ] **Step 3: Run focused tests**

Run:

```bash
uv run --group e2e pytest tests/e2e/test_harness_unit.py -v
```

Expected: PASS.

- [ ] **Step 4: Search for stale live Forgejo references in E2E code**

Run:

```bash
rg -n "create_org_and_repo|cleanup_run|verify_forgejo|read_tea_config|require_executable\(\"tea\"\)|TEA_SKILLS_E2E_KEEP_REMOTE|real Forgejo|real tea|already logged in" tests/e2e
```

Expected: no matches, except historical wording in docs if Task 5 has not run yet.

- [ ] **Step 5: Commit live helper removal**

```bash
git add -A tests/e2e
git commit -m "test: remove live Forgejo e2e helpers"
```

## Task 5: Update contributor E2E documentation

**Files:**
- Modify: `tests/e2e/README.md`

- [ ] **Step 1: Replace README content**

Replace `tests/e2e/README.md` with:

```markdown
# tea-skills E2E tests

This directory contains the tea-skills opt-in AI agent E2E harness. These docs are for contributors testing this repository, not for users installing or consuming the skill plugin.

The harness runs a real agent against a local mock `tea` executable. It does not require a real `tea` binary, configured tea login, or Forgejo/Gitea server.

## Requirements

- Claude Code is installed and authenticated, or Pi is installed and configured.
- `uv` is installed. E2E dependencies are declared in `pyproject.toml` under the `e2e` dependency group and locked in `uv.lock`.

## Commands

Run the non-AI tests:

```bash
uv run --group e2e pytest
```

Run the AI-backed create-issue E2E test:

```bash
TEA_SKILLS_E2E=1 uv run --group e2e pytest tests/e2e/test_agent_e2e.py -v
```

Run with Pi instead of Claude Code:

```bash
TEA_SKILLS_E2E=1 TEA_SKILLS_E2E_AGENT=pi uv run --group e2e pytest tests/e2e/test_agent_e2e.py -v
```

Artifacts are stored under `.e2e-artifacts/<run-id>/` by default. Override the artifact directory:

```bash
TEA_SKILLS_E2E=1 TEA_SKILLS_E2E_ARTIFACT_DIR=/tmp/tea-skills-e2e uv run --group e2e pytest tests/e2e/test_agent_e2e.py -v
```

## Mock tea behavior

The test creates a local executable named `tea` before constructing the Dokimasia run. Dokimasia's `cmd.spy("tea")` then wraps that mock executable, so `result.commands` and `assert_command_ran(...)` still use the normal Dokimasia command assertion path without delegating to the host `tea` binary.

The mock `tea` stores state in JSON under the run artifact root and supports the issue commands needed by the create-issue skill scenario:

- `tea logins`
- `tea issues create --title ... --description ...`
- `tea issues create --title ... --body issue-body.md`
- `tea issues list -o simple`
- `tea issues show <number>`

The E2E assertion verifies local mock state instead of querying a remote Forgejo instance.

## Fixture pack maintenance

Versioned output fixtures live under:

```text
tests/e2e/tea_suite/fixtures/tea/fixture-pack-v1/
```

Keep fixture output as plain text files so changes are easy to review. If a future suite needs to model a different `tea` output style, add a new fixture pack directory such as `fixture-pack-v2/` and point the mock to it; do not silently rewrite old fixture semantics.

## Dokimasia suite boundary

The E2E harness uses Dokimasia only for generic pytest-first suite mechanics:

- `dokimasia.pytest.doki_factory` creates run artifacts, materializes command spies, and returns `result.commands`.
- `dokimasia.pytest.cmd` declares executable spies and command matchers.
- `dokimasia.pytest.assert_command_ran` asserts observed command invocations.
- `dokimasia.suite.layout` creates run ids and artifact directories.

Mock `tea` behavior, fixture packs, local issue state, executable choices, and state assertions remain in tea-skills under `tests/e2e/`. Dokimasia stays domain-neutral.
```

- [ ] **Step 2: Run doc stale-reference search**

Run:

```bash
rg -n "real Forgejo|real `tea`|tea is installed|tea logins|KEEP_REMOTE|create and delete organizations|logged-in account|preserve the disposable remote" tests/e2e/README.md tests/e2e
```

Expected: no stale live-server requirement matches. The phrase `tea logins` may appear only as a supported mock command.

- [ ] **Step 3: Commit docs**

```bash
git add tests/e2e/README.md
git commit -m "docs: document mock tea e2e harness"
```

## Task 6: Final verification

**Files:**
- All modified files

- [ ] **Step 1: Run full non-AI test suite**

```bash
uv run --group e2e pytest
```

Expected: PASS, with `tests/e2e/test_agent_e2e.py` skipped unless `TEA_SKILLS_E2E=1` is set.

- [ ] **Step 2: Run the AI-backed mock E2E**

Run with the default Claude Code adapter:

```bash
TEA_SKILLS_E2E=1 uv run --group e2e pytest tests/e2e/test_agent_e2e.py -v
```

Expected: PASS. The test should not require `command -v tea`, `tea logins`, network access to Forgejo, or cleanup of remote resources.

- [ ] **Step 3: Verify command evidence and state artifacts**

Inspect the newest artifact directory:

```bash
find .e2e-artifacts -maxdepth 4 -type f | sort | tail -40
```

Expected: files include `commands.jsonl`, mock tea `state.json`, `agent.stdout.jsonl`, and `agent.stderr.txt`.

Inspect command and state evidence:

```bash
python - <<'PY'
from pathlib import Path
import json
roots = sorted(Path('.e2e-artifacts').glob('*/artifacts/run-*'))
latest = roots[-1]
print('latest run:', latest)
print((latest / 'commands.jsonl').read_text())
state_paths = sorted(Path('.e2e-artifacts').glob('*/mock-tea/state.json'))
state = json.loads(state_paths[-1].read_text())
print(json.dumps(state, indent=2))
assert len(state['issues']) == 1
assert state['issues'][0]['state'] == 'open'
PY
```

Expected: one recorded `tea issues create` command and one open issue in mock state.

- [ ] **Step 4: Run stale dependency search**

```bash
rg -n "create_org_and_repo|cleanup_run|verify_forgejo|read_tea_config|require_executable\(\"tea\"\)|TEA_SKILLS_E2E_KEEP_REMOTE|real Forgejo|already logged in|can create and delete organizations" tests docs README.md
```

Expected: no live E2E requirement remains outside historical implementation plans. If historical plans match, leave them alone.

- [ ] **Step 5: Commit final verification cleanup if needed**

If Step 4 required any non-historical cleanup:

```bash
git add tests docs README.md
git commit -m "chore: remove stale live e2e references"
```

If no cleanup was needed, do not create an empty commit.

## Self-Review

- **Spec coverage:** The plan replaces the current live Forgejo E2E rather than adding a second path, keeps the test behind `TEA_SKILLS_E2E=1`, uses Dokimasia command instrumentation, avoids spying on the host `tea`, adds versioned maintainable output fixtures, and declares test-only dependencies while keeping skill actions dependency-free.
- **Placeholder scan:** No implementation steps contain `TBD`, `TODO`, or unspecified test instructions. Code snippets include exact paths, commands, and expected outcomes.
- **Type consistency:** `MockTea`, `create_mock_tea`, `load_mock_tea_state`, `MockTeaRun`, and `env_with_path(...)` are named consistently across tasks.
