import contextlib
import importlib.util
import io
import json
import subprocess
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
ACTION_PATH = ROOT / "actions" / "pull-requests" / "find-by-branch.py"


def load_action_module():
    spec = importlib.util.spec_from_file_location("find_by_branch_action", ACTION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FindPullRequestByBranchActionTests(unittest.TestCase):
    def test_uses_current_branch_by_default_and_writes_jsonl_matches(self):
        module = load_action_module()
        fake_adapter = mock.Mock()
        fake_adapter.find_pull_requests_by_branch.return_value = [
            {
                "number": 12,
                "url": "https://forge.example/owner/repo/pulls/12",
                "title": "Feature",
                "state": "open",
                "head": {"owner": "owner", "branch": "feature"},
                "base": {"owner": "owner", "branch": "main"},
            }
        ]
        branch = subprocess.CompletedProcess(
            args=["git", "branch", "--show-current"],
            returncode=0,
            stdout="feature\n",
            stderr="",
        )
        stdout = io.StringIO()
        stderr = io.StringIO()

        with mock.patch.object(module, "default_adapter", return_value=fake_adapter), \
            mock.patch("subprocess.run", return_value=branch), \
            contextlib.redirect_stdout(stdout), \
            contextlib.redirect_stderr(stderr):
            exit_code = module.main([])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(json.loads(stdout.getvalue()), fake_adapter.find_pull_requests_by_branch.return_value[0])
        fake_adapter.find_pull_requests_by_branch.assert_called_once_with("feature", base=None, state="open")

    def test_writes_one_jsonl_record_per_match(self):
        module = load_action_module()
        fake_adapter = mock.Mock()
        fake_adapter.find_pull_requests_by_branch.return_value = [
            {"number": 12, "url": "https://forge.example/pulls/12", "title": "A", "state": "open", "head": {"owner": "o", "branch": "f"}, "base": {"owner": "o", "branch": "main"}},
            {"number": 13, "url": "https://forge.example/pulls/13", "title": "B", "state": "open", "head": {"owner": "o", "branch": "f"}, "base": {"owner": "o", "branch": "develop"}},
        ]
        stdout = io.StringIO()

        with mock.patch.object(module, "default_adapter", return_value=fake_adapter), contextlib.redirect_stdout(stdout):
            exit_code = module.main(["--head", "feature", "--state", "all"])

        self.assertEqual(exit_code, 0)
        rows = [json.loads(line) for line in stdout.getvalue().splitlines()]
        self.assertEqual([row["number"] for row in rows], [12, 13])
        fake_adapter.find_pull_requests_by_branch.assert_called_once_with("feature", base=None, state="all")

    def test_no_matches_writes_jsonl_error_to_stderr(self):
        module = load_action_module()
        fake_adapter = mock.Mock()
        fake_adapter.find_pull_requests_by_branch.return_value = []
        stdout = io.StringIO()
        stderr = io.StringIO()

        with mock.patch.object(module, "default_adapter", return_value=fake_adapter), \
            contextlib.redirect_stdout(stdout), \
            contextlib.redirect_stderr(stderr):
            exit_code = module.main(["--head", "missing"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        error = json.loads(stderr.getvalue())
        self.assertEqual(error["error"], "not_found")
        self.assertIn("missing", error["message"])

    def test_rejects_owner_prefixed_base_as_jsonl_error(self):
        module = load_action_module()
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            exit_code = module.main(["--head", "feature", "--base", "owner:main"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(json.loads(stderr.getvalue())["error"], "invalid_base")

    def test_missing_current_branch_reports_head_required(self):
        module = load_action_module()
        detached = subprocess.CompletedProcess(
            args=["git", "branch", "--show-current"],
            returncode=0,
            stdout="\n",
            stderr="",
        )
        stderr = io.StringIO()

        with mock.patch("subprocess.run", return_value=detached), contextlib.redirect_stderr(stderr):
            exit_code = module.main([])

        self.assertEqual(exit_code, 1)
        self.assertEqual(json.loads(stderr.getvalue())["error"], "head_required")

    def test_invalid_head_writes_jsonl_error_to_stderr(self):
        module = load_action_module()
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            exit_code = module.main(["--head", "owner:"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(json.loads(stderr.getvalue())["error"], "invalid_head")

    def test_invalid_state_writes_jsonl_error_to_stderr(self):
        module = load_action_module()
        stdout = io.StringIO()
        stderr = io.StringIO()

        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as raised:
                module.main(["--head", "feature", "--state", "bad"])

        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(json.loads(stderr.getvalue())["error"], "invalid_arguments")

    def test_adapter_errors_write_jsonl_error_to_stderr(self):
        module = load_action_module()
        cases = [
            module.TeaConfigError("missing config"),
            module.RepoContextError("missing remote"),
            module.ApiError("GET", "https://forge.example/api", 500, "server down"),
        ]

        for exception in cases:
            with self.subTest(exception=exception.__class__.__name__):
                stderr = io.StringIO()
                with mock.patch.object(module, "default_adapter", side_effect=exception), \
                    contextlib.redirect_stderr(stderr):
                    exit_code = module.main(["--head", "feature"])

                self.assertEqual(exit_code, 1)
                error = json.loads(stderr.getvalue())
                self.assertEqual(error["error"], "api_error")
                self.assertIn(str(exception), error["message"])


if __name__ == "__main__":
    unittest.main()
