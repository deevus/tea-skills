import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


EXPECTED_ACTIONS = [
    "actions/issues/comment-edit.py",
    "actions/issues/lock.py",
    "actions/issues/unlock.py",
    "actions/issues/pin.py",
    "actions/issues/unpin.py",
    "actions/issues/reaction-add.py",
    "actions/issues/reaction-list.py",
    "actions/issues/dependency-add.py",
    "actions/issues/dependency-remove.py",
    "actions/issues/dependency-list.py",
    "actions/issues/dependency-all.py",
    "actions/issues/dependency-ready.py",
    "actions/issues/dependency-graph.py",
    "actions/pull-requests/set-automerge.py",
    "actions/pull-requests/find-by-branch.py",
    "actions/milestones/edit.py",
    "actions/org-labels/list.py",
    "actions/org-labels/create.py",
]

REPOSITORY_SCOPED_ACTIONS = [relative for relative in EXPECTED_ACTIONS if relative.startswith("actions/issues/")] + [
    "actions/pull-requests/set-automerge.py",
    "actions/pull-requests/find-by-branch.py",
    "actions/milestones/edit.py",
]


def load_action_module(relative: str):
    module_name = relative.replace("/", "_").replace("-", "_").replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def assert_scope_options(test_case, default_repo_scope, *, login, remote, repo):
    default_repo_scope.assert_called_once()
    options = default_repo_scope.call_args.kwargs.get("options")
    test_case.assertIsNotNone(options)
    test_case.assertEqual(options.login, login)
    test_case.assertEqual(options.remote, remote)
    test_case.assertEqual(options.repo, repo)


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

    def test_no_action_uses_external_http_or_json_tools(self):
        forbidden = ["cur" + "l", "j" + "q"]
        for relative in EXPECTED_ACTIONS:
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(action=relative):
                for term in forbidden:
                    self.assertNotIn(term, text)

    def test_actions_use_audit_wrapper(self):
        for relative in EXPECTED_ACTIONS:
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(action=relative):
                self.assertIn("run_action", text)
                self.assertIn("Path(__file__)", text)

    def test_repository_scoped_actions_show_shared_targeting_flags_in_help(self):
        for relative in REPOSITORY_SCOPED_ACTIONS:
            with self.subTest(action=relative):
                completed = subprocess.run(
                    [sys.executable, str(ROOT / relative), "--help"],
                    check=False,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertIn("--login", completed.stdout)
                self.assertIn("--remote", completed.stdout)
                self.assertIn("--repo", completed.stdout)

    def test_issue_action_passes_shared_scope_options(self):
        module = load_action_module("actions/issues/pin.py")
        fake_scope = mock.Mock()
        default_repo_scope = mock.Mock(return_value=fake_scope)
        pin = mock.Mock()
        stdout = io.StringIO()

        with (
            mock.patch.object(module, "default_repo_scope", default_repo_scope),
            mock.patch.object(module, "pin", pin),
            contextlib.redirect_stdout(stdout),
        ):
            exit_code = module.main(["--login", "forgejo", "--remote", "upstream", "--repo", "owner/repo", "12"])

        self.assertEqual(exit_code, 0)
        assert_scope_options(self, default_repo_scope, login="forgejo", remote="upstream", repo="owner/repo")
        pin.assert_called_once_with(fake_scope, 12)

    def test_milestone_action_passes_shared_scope_options(self):
        module = load_action_module("actions/milestones/edit.py")
        fake_scope = mock.Mock()
        default_repo_scope = mock.Mock(return_value=fake_scope)
        edit_milestone = mock.Mock()
        stdout = io.StringIO()

        with (
            mock.patch.object(module, "default_repo_scope", default_repo_scope),
            mock.patch.object(module, "edit_milestone", edit_milestone),
            contextlib.redirect_stdout(stdout),
        ):
            exit_code = module.main(["--login", "forgejo", "--repo", "owner/repo", "v1", "--title", "Version 1"])

        self.assertEqual(exit_code, 0)
        assert_scope_options(self, default_repo_scope, login="forgejo", remote=None, repo="owner/repo")
        edit_milestone.assert_called_once_with(fake_scope, "v1", "Version 1", None, None)

    def test_pull_request_action_passes_shared_scope_options(self):
        module = load_action_module("actions/pull-requests/set-automerge.py")
        fake_scope = mock.Mock()
        default_repo_scope = mock.Mock(return_value=fake_scope)
        enable_automerge = mock.Mock()
        stdout = io.StringIO()

        with (
            mock.patch.object(module, "default_repo_scope", default_repo_scope),
            mock.patch.object(module, "enable_automerge", enable_automerge),
            contextlib.redirect_stdout(stdout),
        ):
            exit_code = module.main(["--login", "forgejo", "--repo", "owner/repo", "12", "--enable"])

        self.assertEqual(exit_code, 0)
        assert_scope_options(self, default_repo_scope, login="forgejo", remote=None, repo="owner/repo")
        enable_automerge.assert_called_once_with(fake_scope, 12, "squash", "")


if __name__ == "__main__":
    unittest.main()
