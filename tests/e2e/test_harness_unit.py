from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from unittest import mock

import pytest

from tests.e2e import test_agent_e2e


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


def test_make_agent_adapter_uses_pi_with_checkout_skills():
    from dokimasia.agents.pi import PiAdapter

    adapter = test_agent_e2e.make_agent_adapter()

    assert isinstance(adapter, PiAdapter)
    assert adapter.skills_dir == test_agent_e2e.ROOT / "skills"
    assert adapter.extra_args == ("--no-extensions",)


def test_e2e_env_defaults_to_deepseek_model(tmp_path):
    from tests.e2e.tea_suite.mock_tea import create_mock_tea

    mock_tea = create_mock_tea(tmp_path / "mock-tea")

    with mock.patch.dict(os.environ, {}, clear=True):
        env = test_agent_e2e.e2e_env(mock_tea)

    assert env["DOKIMASIA_MODEL"] == "deepseek/deepseek-v4-flash"


def test_e2e_env_preserves_dokimasia_model_override(tmp_path):
    from tests.e2e.tea_suite.mock_tea import create_mock_tea

    mock_tea = create_mock_tea(tmp_path / "mock-tea")

    with mock.patch.dict(os.environ, {"DOKIMASIA_MODEL": "other/provider-model"}, clear=True):
        env = test_agent_e2e.e2e_env(mock_tea)

    assert env["DOKIMASIA_MODEL"] == "other/provider-model"


def test_mock_e2e_uses_bundled_mock_tea():
    from tests.e2e.tea_suite.mock_tea import MockTea, create_mock_tea

    assert test_agent_e2e.MockTea is MockTea
    assert test_agent_e2e.create_mock_tea is create_mock_tea


def test_mock_e2e_workspace_is_hermetic_git_repo(tmp_path):
    workspace = tmp_path / "workspace" / "repo"

    test_agent_e2e.prepare_mock_workspace(workspace)

    top_level = subprocess.run(
        ["git", "-C", str(workspace), "rev-parse", "--show-toplevel"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    origin = subprocess.run(
        ["git", "-C", str(workspace), "remote", "get-url", "origin"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    assert Path(top_level.stdout.strip()) == workspace.resolve()
    assert origin.stdout.strip() == test_agent_e2e.MOCK_ORIGIN_URL


def test_session_hook_in_mock_workspace_does_not_use_parent_repo_context():
    from tests.e2e.tea_suite.mock_tea import create_mock_tea

    run_root = test_agent_e2e.ROOT / ".e2e-artifacts" / f"unit-hermetic-{uuid.uuid4().hex}"
    workspace = run_root / "workspace" / "repo"
    try:
        test_agent_e2e.prepare_mock_workspace(workspace)
        mock_tea = create_mock_tea(run_root / "mock-tea")

        completed = subprocess.run(
            ["bash", str(test_agent_e2e.ROOT / "hooks" / "session-start.sh")],
            cwd=workspace,
            env=mock_tea.env_with_path(os.environ),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        assert completed.returncode == 0
        assert completed.stderr == ""
        assert "forgejo.tail9a847c.ts.net" not in completed.stdout
        assert "WORKTREE DETECTED" not in completed.stdout
        assert "tea CLI is configured and ready." in completed.stdout
    finally:
        shutil.rmtree(run_root, ignore_errors=True)


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


def test_issue_show_matcher_accepts_detail_commands_without_pinning_issue_number():
    commands = [
        {"source": "tea", "argv": ["issues", "1"], "exit_code": 0},
        {"source": "tea", "argv": ["issue", "show", "42"], "exit_code": 0},
        {"source": "tea", "argv": ["i", "s", "99"], "exit_code": 0},
    ]

    assert all(test_agent_e2e.ISSUE_SHOW.matches(command) for command in commands)
    assert not test_agent_e2e.ISSUE_SHOW.matches({"source": "tea", "argv": ["issues", "list"], "exit_code": 0})


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


def test_mock_tea_supports_login_list_csv_for_session_hook(tmp_path):
    from tests.e2e.tea_suite.mock_tea import create_mock_tea

    mock_tea = create_mock_tea(tmp_path / "mock-tea")
    env = mock_tea.env_with_path(os.environ)

    plain = subprocess.run(
        [str(mock_tea.executable), "login", "list"],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    csv = subprocess.run(
        [str(mock_tea.executable), "login", "list", "-o", "csv"],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    login_count = subprocess.run(
        ["sh", "-c", "tail -n +2 | wc -l"],
        input=csv.stdout,
        text=True,
        stdout=subprocess.PIPE,
        check=True,
    )

    assert plain.returncode == 0
    assert plain.stderr == ""
    assert "mock-forgejo https://mock.invalid" in plain.stdout
    assert csv.returncode == 0
    assert csv.stderr == ""
    assert csv.stdout.splitlines()[0] == "Name,URL"
    assert "mock-forgejo,https://mock.invalid" in csv.stdout.splitlines()[1:]
    assert int(login_count.stdout.strip()) > 0


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
