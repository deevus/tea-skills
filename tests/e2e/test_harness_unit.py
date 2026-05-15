from __future__ import annotations

import os
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
