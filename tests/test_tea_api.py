import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError

from actions.internal import issues, milestones, org_labels, org_scope, pulls, repo_scope, tea_api


class TeaApiCoreTests(unittest.TestCase):
    def make_repo_scope(self, opener):
        return repo_scope.RepositoryScope(
            tea_api.GiteaAdapter(tea_api.TeaConfig("t", "https://forge.example"), opener=opener),
            tea_api.RepoContext("owner", "repo"),
        )

    def make_org_scope(self, opener):
        return org_scope.OrgScope(
            tea_api.GiteaAdapter(tea_api.TeaConfig("t", "https://forge.example"), opener=opener),
            "owner",
        )

    def test_config_path_prefers_xdg_config_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            xdg = Path(tmp) / "xdg"
            expected = xdg / "tea" / "config.yml"
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(xdg)}):
                self.assertEqual(tea_api.config_path(), expected)

    def test_config_path_falls_back_to_home_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            with mock.patch.dict(os.environ, {}, clear=True):
                with mock.patch.object(Path, "home", return_value=home):
                    self.assertEqual(tea_api.config_path(), home / ".config" / "tea" / "config.yml")

    def test_read_config_extracts_first_token_and_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.yml"
            config.write_text(
                "logins:\n  - name: main\n    url: https://forge.example\n    token: abc123\n",
                encoding="utf-8",
            )
            result = tea_api.read_tea_config(config)
            self.assertEqual(result.token, "abc123")
            self.assertEqual(result.base_url, "https://forge.example")

    def test_read_config_errors_when_token_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.yml"
            config.write_text("url: https://forge.example\n", encoding="utf-8")
            with self.assertRaisesRegex(tea_api.TeaConfigError, "token"):
                tea_api.read_tea_config(config)

    def test_parse_repo_remote_supports_https(self):
        self.assertEqual(
            tea_api.parse_repo_remote("https://forge.example/owner/repo.git"),
            ("owner", "repo"),
        )

    def test_parse_repo_remote_supports_ssh_scp_style(self):
        self.assertEqual(
            tea_api.parse_repo_remote("git@forge.example:owner/repo.git"),
            ("owner", "repo"),
        )

    def test_build_url_encodes_query_values(self):
        config = tea_api.TeaConfig(token="t", base_url="https://forge.example")
        context = tea_api.RepoContext(owner="alice", repo="project")
        scope = repo_scope.RepositoryScope(tea_api.GiteaAdapter(config=config, opener=lambda request: None), context)
        url = scope.url("milestones", {"name": "v1.0 alpha"})
        self.assertEqual(
            url,
            "https://forge.example/api/v1/repos/alice/project/milestones?name=v1.0+alpha",
        )

    def test_request_json_encodes_body_and_headers(self):
        captured = {}

        def opener(request):
            captured["url"] = request.full_url
            captured["method"] = request.get_method()
            captured["headers"] = dict(request.header_items())
            captured["data"] = request.data
            return tea_api.FakeHttpResponse(201, {"id": 1})

        config = tea_api.TeaConfig(token="secret", base_url="https://forge.example")
        context = tea_api.RepoContext(owner="alice", repo="project")
        scope = repo_scope.RepositoryScope(tea_api.GiteaAdapter(config=config, opener=opener), context)
        result = scope.post("issues/1/reactions", {"content": "+1"})

        self.assertEqual(result, {"id": 1})
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["headers"]["Authorization"], "token secret")
        self.assertEqual(captured["headers"]["Content-type"], "application/json")
        self.assertEqual(json.loads(captured["data"].decode("utf-8")), {"content": "+1"})

    def test_http_error_includes_status_and_body(self):
        def opener(request):
            raise HTTPError(
                request.full_url,
                409,
                "Conflict",
                hdrs=None,
                fp=tea_api.BytesBody(b'{"message":"already exists"}'),
            )

        config = tea_api.TeaConfig(token="secret", base_url="https://forge.example")
        context = tea_api.RepoContext(owner="alice", repo="project")
        scope = repo_scope.RepositoryScope(tea_api.GiteaAdapter(config=config, opener=opener), context)

        with self.assertRaises(tea_api.ApiError) as raised:
            scope.post("issues/1/dependencies", {"index": 2})

        self.assertEqual(raised.exception.status, 409)
        self.assertIn("POST", str(raised.exception))
        self.assertIn("already exists", str(raised.exception))

    def test_repo_context_uses_git_remote_origin(self):
        completed = subprocess.CompletedProcess(
            args=["git"], returncode=0, stdout="git@forge.example:owner/repo.git\n", stderr=""
        )
        with mock.patch("subprocess.run", return_value=completed):
            self.assertEqual(tea_api.discover_repo_context(), tea_api.RepoContext("owner", "repo"))

    def test_repository_scope_prefers_remote_matching_adapter_base_url(self):
        def fake_run(args, check, text, stdout, stderr):
            if args == ["git", "remote", "-v"]:
                return subprocess.CompletedProcess(
                    args=args,
                    returncode=0,
                    stdout=(
                        "origin\tgit@github.com:deevus/tea-skills.git (fetch)\n"
                        "origin\tgit@github.com:deevus/tea-skills.git (push)\n"
                        "self-hosted\tssh://git@forgejo.tail9a847c.ts.net/sh/tea-skills.git (fetch)\n"
                        "self-hosted\tssh://git@forgejo.tail9a847c.ts.net/sh/tea-skills.git (push)\n"
                    ),
                    stderr="",
                )
            if args == ["git", "remote", "get-url", "origin"]:
                return subprocess.CompletedProcess(
                    args=args,
                    returncode=0,
                    stdout="git@github.com:deevus/tea-skills.git\n",
                    stderr="",
                )
            raise AssertionError(f"unexpected command: {args}")

        api = tea_api.GiteaAdapter(
            tea_api.TeaConfig("t", "https://forgejo.tail9a847c.ts.net"),
            opener=lambda request: None,
        )

        with mock.patch("subprocess.run", side_effect=fake_run):
            scope = repo_scope.RepositoryScope(api)

        self.assertEqual(scope.repo, tea_api.RepoContext("sh", "tea-skills"))

    def test_edit_issue_comment_sends_body(self):
        calls = []
        scope = self.make_repo_scope(lambda request: calls.append(request) or tea_api.FakeHttpResponse(200, {"id": 12}))
        result = issues.edit_comment(scope, 12, "updated text")
        self.assertEqual(result["id"], 12)
        self.assertEqual(calls[0].get_method(), "PATCH")
        self.assertTrue(calls[0].full_url.endswith("/issues/comments/12"))
        self.assertEqual(json.loads(calls[0].data.decode("utf-8")), {"body": "updated text"})

    def test_issue_dependency_add_handles_conflict(self):
        def opener(request):
            raise HTTPError(request.full_url, 409, "Conflict", hdrs=None, fp=tea_api.BytesBody(b"exists"))

        scope = self.make_repo_scope(opener)
        self.assertEqual(issues.add_dependency(scope, 25, 26), "exists")

    def test_ready_issues_filters_open_blockers(self):
        responses = {
            "issues": [
                {"number": 1, "state": "open", "title": "Ready"},
                {"number": 2, "state": "open", "title": "Blocked"},
            ],
            "issues/1/dependencies": [],
            "issues/2/dependencies": [{"number": 99, "state": "open", "title": "Blocker"}],
        }

        def opener(request):
            endpoint = request.full_url.split("/repos/owner/repo/", 1)[1].split("?", 1)[0]
            return tea_api.FakeHttpResponse(200, responses[endpoint])

        scope = self.make_repo_scope(opener)
        self.assertEqual(issues.ready(scope), [{"number": 1, "state": "open", "title": "Ready"}])

    def test_find_milestone_id_by_name_uses_query_encoding(self):
        captured = {}

        def opener(request):
            captured["url"] = request.full_url
            return tea_api.FakeHttpResponse(200, [{"id": 7, "title": "v1.0 alpha"}])

        scope = self.make_repo_scope(opener)
        self.assertEqual(milestones.find_id_by_name(scope, "v1.0 alpha"), 7)
        self.assertTrue(captured["url"].endswith("/milestones?name=v1.0+alpha"))

    def test_edit_milestone_sends_due_on_timestamp(self):
        bodies = []

        def opener(request):
            if request.get_method() == "GET":
                return tea_api.FakeHttpResponse(200, [{"id": 7}])
            bodies.append(json.loads(request.data.decode("utf-8")))
            return tea_api.FakeHttpResponse(200, {"id": 7})

        scope = self.make_repo_scope(opener)
        milestones.edit(scope, "v1", due_date="2026-06-01")
        self.assertEqual(bodies[-1], {"due_on": "2026-06-01T00:00:00Z"})

    def test_create_org_label_posts_to_org_scope(self):
        captured = {}

        def opener(request):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return tea_api.FakeHttpResponse(201, {"name": "org:team-a"})

        scope = self.make_org_scope(opener)
        org_labels.create(scope, "org:team-a", "#0052cc", "Owned by Team A")
        self.assertEqual(captured["url"], "https://forge.example/api/v1/orgs/owner/labels")
        self.assertEqual(captured["body"]["description"], "Owned by Team A")

    def test_set_automerge_enable_sends_merge_when_checks_succeed(self):
        captured = {}

        def opener(request):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return tea_api.FakeHttpResponse(200, {})

        scope = self.make_repo_scope(opener)
        pulls.enable_automerge(scope, 15, "squash", "feat: add auth")
        self.assertEqual(
            captured["body"],
            {"Do": "squash", "merge_when_checks_succeed": True, "merge_message_field": "feat: add auth"},
        )

    def test_find_pull_requests_by_branch_filters_head_ref_and_base_branch(self):
        captured = {}
        payload = [
            {
                "number": 12,
                "html_url": "https://forge.example/owner/repo/pulls/12",
                "title": "Feature",
                "state": "open",
                "head": {"label": "owner:feature", "ref": "feature"},
                "base": {"label": "owner:main", "ref": "main"},
            },
            {
                "number": 13,
                "html_url": "https://forge.example/owner/repo/pulls/13",
                "title": "Other base",
                "state": "open",
                "head": {"label": "owner:feature", "ref": "feature"},
                "base": {"label": "owner:develop", "ref": "develop"},
            },
            {
                "number": 14,
                "html_url": "https://forge.example/owner/repo/pulls/14",
                "title": "Other head",
                "state": "open",
                "head": {"label": "owner:other", "ref": "other"},
                "base": {"label": "owner:main", "ref": "main"},
            },
        ]

        def opener(request):
            captured["url"] = request.full_url
            return tea_api.FakeHttpResponse(200, payload)

        scope = self.make_repo_scope(opener)

        self.assertEqual(
            pulls.find_by_branch(scope, "feature", base="main", state="open"),
            [
                {
                    "number": 12,
                    "url": "https://forge.example/owner/repo/pulls/12",
                    "title": "Feature",
                    "state": "open",
                    "head": {"owner": "owner", "branch": "feature"},
                    "base": {"owner": "owner", "branch": "main"},
                }
            ],
        )
        self.assertTrue(captured["url"].endswith("/pulls?state=open&base_branch=main"))

    def test_find_pull_requests_by_branch_matches_owner_prefixed_head_label(self):
        scope = self.make_repo_scope(
            lambda request: tea_api.FakeHttpResponse(
                200,
                [
                    {
                        "number": 12,
                        "url": "https://forge.example/owner/repo/pulls/12",
                        "title": "Fork feature",
                        "state": "open",
                        "head": {"label": "contributor:feature", "ref": "feature"},
                        "base": {"label": "owner:main", "ref": "main"},
                    },
                    {
                        "number": 13,
                        "url": "https://forge.example/owner/repo/pulls/13",
                        "title": "Local feature",
                        "state": "open",
                        "head": {"label": "owner:feature", "ref": "feature"},
                        "base": {"label": "owner:main", "ref": "main"},
                    },
                ],
            )
        )

        matches = pulls.find_by_branch(scope, "contributor:feature", state="all")

        self.assertEqual([match["number"] for match in matches], [12])
        self.assertEqual(matches[0]["head"], {"owner": "contributor", "branch": "feature"})

    def test_audit_action_noops_without_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            with mock.patch.dict(os.environ, {}, clear=True):
                tea_api.audit_action(action="actions/issues/lock.py", argv=["1"], exit_code=0)
            self.assertFalse(path.exists())

    def test_audit_action_writes_jsonl_when_env_is_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            with mock.patch.dict(os.environ, {"TEA_SKILLS_AUDIT_LOG": str(path)}):
                tea_api.audit_action(
                    action="actions/issues/lock.py",
                    argv=["1", "resolved"],
                    exit_code=0,
                    phase="finish",
                )
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["source"], "tea-skills-action")
            self.assertEqual(rows[0]["action"], "actions/issues/lock.py")
            self.assertEqual(rows[0]["argv"], ["1", "resolved"])
            self.assertEqual(rows[0]["phase"], "finish")
            self.assertEqual(rows[0]["exit_code"], 0)
            self.assertIn("cwd", rows[0])
            self.assertIn("timestamp", rows[0])
            self.assertIn("pid", rows[0])

    def test_run_action_logs_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"

            def main(argv):
                self.assertEqual(argv, ["7"])
                return 3

            with mock.patch.dict(os.environ, {"TEA_SKILLS_AUDIT_LOG": str(path)}):
                exit_code = tea_api.run_action(Path("/repo/actions/issues/lock.py"), ["7"], main)

            self.assertEqual(exit_code, 3)
            row = json.loads(path.read_text(encoding="utf-8").strip())
            self.assertEqual(row["action"], "actions/issues/lock.py")
            self.assertEqual(row["exit_code"], 3)

    def test_run_action_logs_unhandled_exception_then_reraises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"

            def main(argv):
                raise RuntimeError("boom")

            with mock.patch.dict(os.environ, {"TEA_SKILLS_AUDIT_LOG": str(path)}):
                with self.assertRaisesRegex(RuntimeError, "boom"):
                    tea_api.run_action(Path("/repo/actions/issues/lock.py"), [], main)

            row = json.loads(path.read_text(encoding="utf-8").strip())
            self.assertEqual(row["action"], "actions/issues/lock.py")
            self.assertEqual(row["exit_code"], 1)
            self.assertEqual(row["error"], "RuntimeError: boom")


if __name__ == "__main__":
    unittest.main()
