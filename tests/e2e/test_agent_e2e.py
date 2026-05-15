from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from dokimasia.agents.pi import PiAdapter
from dokimasia.pytest import assert_command_ran, cmd
from dokimasia.suite.layout import create_run_id, prepare_run_root
from tests.e2e.tea_suite.mock_tea import MockTea, create_mock_tea

ROOT = Path(__file__).resolve().parents[2]
TEA = cmd.spy("tea")
ISSUE_CREATE = TEA.match(pattern=[("issues", "issue", "i"), ("create", "c")])
MOCK_ORIGIN_URL = "https://mock.invalid/sh/mock-repo.git"


@dataclass(frozen=True)
class MockTeaRun:
    run_id: str
    workspace: Path
    artifact_dir: Path
    tea: MockTea


pytestmark = pytest.mark.skipif(
    os.environ.get("TEA_SKILLS_E2E") != "1",
    reason="set TEA_SKILLS_E2E=1 to run AI-backed mock tea E2E tests",
)


def issue_title_for_run(run_id: str) -> str:
    return f"E2E {run_id} create issue"


def issue_body_for_run(run_id: str) -> str:
    return f"E2E body marker: {run_id}\n"


def e2e_run_id() -> str:
    return create_run_id()


def e2e_run_root(run_id: str) -> Path:
    base = Path(os.environ.get("TEA_SKILLS_E2E_ARTIFACT_DIR", ROOT / ".e2e-artifacts"))
    return prepare_run_root(base, run_id)


def make_agent_adapter():
    return PiAdapter(skills_dir=ROOT / "skills", extra_args=["--no-extensions"])


def prepare_mock_workspace(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "AGENTS.md").write_text(
        "# Repository context\n\nThis repository is hosted on Forgejo. Use tea for issue workflows.\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=workspace, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(
        ["git", "remote", "remove", "origin"],
        cwd=workspace,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    subprocess.run(
        ["git", "remote", "add", "origin", MOCK_ORIGIN_URL],
        cwd=workspace,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def assert_single_issue_matches(issues: list[dict[str, Any]], *, title: str, body: str) -> None:
    candidates = [issue for issue in issues if issue.get("title") == title]
    assert len(candidates) == 1, f"expected exactly one issue titled {title!r}, found {len(candidates)}"

    issue = candidates[0]
    assert issue.get("state") == "open"
    assert issue.get("body", "").strip() == body.strip(), "expected issue body to match issue-body.md"


@pytest.fixture
def mock_run_id() -> str:
    return e2e_run_id()


@pytest.fixture
def mock_tea_run(mock_run_id: str) -> MockTeaRun:
    root = e2e_run_root(mock_run_id)
    workspace = root / "workspace" / "repo"
    artifact_dir = root / "artifacts"
    prepare_mock_workspace(workspace)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    return MockTeaRun(
        run_id=mock_run_id,
        workspace=workspace,
        artifact_dir=artifact_dir,
        tea=create_mock_tea(root / "mock-tea"),
    )


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
