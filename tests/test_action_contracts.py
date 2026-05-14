import os
import unittest
from pathlib import Path


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
    "actions/milestones/edit.py",
    "actions/org-labels/list.py",
    "actions/org-labels/create.py",
]


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


if __name__ == "__main__":
    unittest.main()
