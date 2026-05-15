from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from dokimasia.agents.claude_code import ClaudeCodeAdapter
from dokimasia.agents.pi import PiAdapter
from dokimasia.pytest import assert_command_ran, cmd
from dokimasia.suite.env import require_executable
from dokimasia.suite.layout import create_run_id, prepare_run_root
from tests.e2e.tea_suite.provision import ForgejoRun, cleanup_run, create_org_and_repo
from tests.e2e.tea_suite.verify_forgejo import list_issues

ROOT = Path(__file__).resolve().parents[2]
TEA = cmd.spy("tea")
ISSUE_CREATE = TEA.match(pattern=[("issues", "issue", "i"), ("create", "c")])

pytestmark = pytest.mark.skipif(
    os.environ.get("TEA_SKILLS_E2E") != "1",
    reason="set TEA_SKILLS_E2E=1 to run live agent E2E tests",
)


def issue_title_for_run(run_id: str) -> str:
    return f"E2E {run_id} create issue"


def issue_body_for_run(run_id: str) -> str:
    return f"E2E body marker: {run_id}\n"


def e2e_run_id() -> str:
    return create_run_id()


def e2e_real_tea() -> Path:
    return require_executable("tea")


def e2e_run_root(run_id: str) -> Path:
    base = Path(os.environ.get("TEA_SKILLS_E2E_ARTIFACT_DIR", ROOT / ".e2e-artifacts"))
    return prepare_run_root(base, run_id)


def make_agent_adapter():
    agent = os.environ.get("TEA_SKILLS_E2E_AGENT", "claude").lower()
    if agent == "claude":
        return ClaudeCodeAdapter(plugin_dir=ROOT)
    if agent == "pi":
        return PiAdapter(skills_dir=ROOT / "skills")
    raise ValueError(f"unknown TEA_SKILLS_E2E_AGENT: {agent}")


def assert_single_issue_matches(issues: list[dict[str, Any]], *, title: str, body: str) -> None:
    candidates = [issue for issue in issues if issue.get("title") == title]
    assert len(candidates) == 1, f"expected exactly one issue titled {title!r}, found {len(candidates)}"

    issue = candidates[0]
    assert issue.get("state") == "open"
    assert issue.get("body", "").strip() == body.strip(), "expected issue body to match issue-body.md"


@pytest.fixture
def live_run_id() -> str:
    return e2e_run_id()


@pytest.fixture
def forgejo_run(live_run_id: str) -> ForgejoRun:
    require_executable("tea")
    run = create_org_and_repo(e2e_run_root(live_run_id), live_run_id)
    try:
        yield run
    finally:
        cleanup_run(run, keep_remote=os.environ.get("TEA_SKILLS_E2E_KEEP_REMOTE") == "1")


def test_create_issue_from_body_file_with_pytest_dokimasia_api(doki_factory, forgejo_run: ForgejoRun):
    title = issue_title_for_run(forgejo_run.run_id)
    body = issue_body_for_run(forgejo_run.run_id)
    doki = doki_factory(
        agent=make_agent_adapter(),
        workspace=forgejo_run.workspace,
        artifact_dir=forgejo_run.artifact_dir,
        run_id=forgejo_run.run_id,
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
    assert_single_issue_matches(
        list_issues(forgejo_run.config, forgejo_run.org, forgejo_run.repo), title=title, body=body
    )
