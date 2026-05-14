import os
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


EXPECTED_ACTIONS = [
    "actions/issues/comment-edit",
    "actions/issues/lock",
    "actions/issues/unlock",
    "actions/issues/pin",
    "actions/issues/unpin",
    "actions/issues/reaction-add",
    "actions/issues/reaction-list",
    "actions/issues/dependency-add",
    "actions/issues/dependency-remove",
    "actions/issues/dependency-list",
    "actions/issues/dependency-all",
    "actions/issues/dependency-ready",
    "actions/issues/dependency-graph",
    "actions/pull-requests/set-automerge",
    "actions/milestones/edit",
    "actions/org-labels/list",
    "actions/org-labels/create",
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

    def test_no_action_uses_curl_or_jq(self):
        for relative in EXPECTED_ACTIONS:
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(action=relative):
                self.assertNotIn("curl", text)
                self.assertNotIn("jq", text)


if __name__ == "__main__":
    unittest.main()
