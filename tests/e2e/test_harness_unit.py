from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from unittest import mock

import pytest

from actions.internal.tea_api import TeaConfig
from tests.e2e import test_agent_e2e
from tests.e2e.tea_suite import verify_forgejo
from tests.e2e.tea_suite.provision import assert_safe_e2e_resource


def test_e2e_run_id_uses_dokimasia_layout():
    with mock.patch("tests.e2e.test_agent_e2e.create_run_id", return_value="abc123") as create:
        run_id = test_agent_e2e.e2e_run_id()

    assert run_id == "abc123"
    create.assert_called_once_with()


def test_e2e_run_root_defaults_to_repo_artifacts_dir():
    expected = test_agent_e2e.ROOT / ".e2e-artifacts" / "abc123"
    with mock.patch("tests.e2e.test_agent_e2e.prepare_run_root", return_value=expected) as prepare:
        with mock.patch.dict(os.environ, {}, clear=True):
            run_root = test_agent_e2e.e2e_run_root("abc123")

    assert run_root == expected
    prepare.assert_called_once_with(test_agent_e2e.ROOT / ".e2e-artifacts", "abc123")


def test_e2e_run_root_uses_env_artifact_dir():
    expected = Path("/tmp/tea-e2e") / "abc123"
    with mock.patch("tests.e2e.test_agent_e2e.prepare_run_root", return_value=expected) as prepare:
        with mock.patch.dict(os.environ, {"TEA_SKILLS_E2E_ARTIFACT_DIR": "/tmp/tea-e2e"}, clear=True):
            run_root = test_agent_e2e.e2e_run_root("abc123")

    assert run_root == expected
    prepare.assert_called_once_with(Path("/tmp/tea-e2e"), "abc123")


def test_make_agent_adapter_defaults_to_claude():
    from dokimasia.agents.claude_code import ClaudeCodeAdapter

    with mock.patch.dict(os.environ, {}, clear=True):
        adapter = test_agent_e2e.make_agent_adapter()

    assert isinstance(adapter, ClaudeCodeAdapter)
    assert adapter.plugin_dir == test_agent_e2e.ROOT


def test_make_agent_adapter_supports_pi():
    from dokimasia.agents.pi import PiAdapter

    with mock.patch.dict(os.environ, {"TEA_SKILLS_E2E_AGENT": "pi"}, clear=True):
        adapter = test_agent_e2e.make_agent_adapter()

    assert isinstance(adapter, PiAdapter)
    assert adapter.skills_dir == test_agent_e2e.ROOT / "skills"


def test_make_agent_adapter_rejects_unknown_agent():
    with mock.patch.dict(os.environ, {"TEA_SKILLS_E2E_AGENT": "bogus"}, clear=True):
        with pytest.raises(ValueError, match="unknown TEA_SKILLS_E2E_AGENT: bogus"):
            test_agent_e2e.make_agent_adapter()


def test_live_e2e_requires_tea_through_dokimasia_env_helper():
    with mock.patch("tests.e2e.test_agent_e2e.require_executable", return_value=Path("/bin/tea")) as require:
        real_tea = test_agent_e2e.e2e_real_tea()

    assert real_tea == Path("/bin/tea")
    require.assert_called_once_with("tea")


def test_issue_title_and_body_include_run_id():
    assert test_agent_e2e.issue_title_for_run("abc123") == "E2E abc123 create issue"
    assert test_agent_e2e.issue_body_for_run("abc123") == "E2E body marker: abc123\n"


def test_issue_create_matcher_accepts_tea_issue_create_aliases():
    commands = [
        {"source": "tea", "argv": ["issues", "create", "--title", "T"], "exit_code": 0},
        {"source": "tea", "argv": ["issue", "--title", "T", "create"], "exit_code": 0},
        {"source": "tea", "argv": ["i", "--body", "issue-body.md", "c"], "exit_code": 0},
    ]

    assert all(test_agent_e2e.ISSUE_CREATE.matches(command) for command in commands)
    assert not test_agent_e2e.ISSUE_CREATE.matches({"source": "tea", "argv": ["issues", "list"], "exit_code": 0})


def test_assert_single_issue_matches_checks_count_state_and_body():
    test_agent_e2e.assert_single_issue_matches(
        [
            {"number": 1, "title": "Other", "body": "ignored", "state": "open"},
            {"number": 2, "title": "Wanted", "body": "body marker", "state": "open"},
        ],
        title="Wanted",
        body="body marker\n",
    )

    with pytest.raises(AssertionError, match="expected exactly one issue titled 'Wanted', found 2"):
        test_agent_e2e.assert_single_issue_matches(
            [
                {"number": 1, "title": "Wanted", "body": "body marker", "state": "open"},
                {"number": 2, "title": "Wanted", "body": "body marker", "state": "open"},
            ],
            title="Wanted",
            body="body marker",
        )

    with pytest.raises(AssertionError, match="expected issue body"):
        test_agent_e2e.assert_single_issue_matches(
            [{"number": 1, "title": "Wanted", "body": "different", "state": "open"}],
            title="Wanted",
            body="body marker",
        )


def test_safe_e2e_resource_policy_requires_suite_prefix_and_run_id():
    assert_safe_e2e_resource("tea-e2e-abc123", "abc123")

    with pytest.raises(ValueError, match="out-of-scope disposable resource"):
        assert_safe_e2e_resource("production-org", "abc123")


def test_list_issues_uses_project_owned_forgejo_api_request():
    config = TeaConfig(token="token", base_url="https://forgejo.example")
    payload = [{"number": 1, "title": "Wanted"}]

    with mock.patch("tests.e2e.tea_suite.verify_forgejo.api_request", return_value=payload) as api_request:
        issues = verify_forgejo.list_issues(config, "org/name", "repo name")

    assert issues == payload
    api_request.assert_called_once_with(config, "GET", "repos/org%2Fname/repo%20name/issues?state=all")


def test_list_issues_returns_empty_list_for_non_list_response():
    with mock.patch("tests.e2e.tea_suite.verify_forgejo.api_request", return_value={"message": "not a list"}):
        assert (
            verify_forgejo.list_issues(TeaConfig(token="token", base_url="https://forgejo.example"), "org", "repo")
            == []
        )


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
