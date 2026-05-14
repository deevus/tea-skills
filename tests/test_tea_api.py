import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError

from actions.internal import tea_api


class TeaApiCoreTests(unittest.TestCase):
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
                "logins:\n"
                "  - name: main\n"
                "    url: https://forge.example\n"
                "    token: abc123\n",
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
        adapter = tea_api.GiteaAdapter(config=config, repo=context, opener=lambda request: None)
        url = adapter.repo_url("milestones", {"name": "v1.0 alpha"})
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
        adapter = tea_api.GiteaAdapter(config=config, repo=context, opener=opener)
        result = adapter.post_repo("issues/1/reactions", {"content": "+1"})

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
        adapter = tea_api.GiteaAdapter(config=config, repo=context, opener=opener)

        with self.assertRaises(tea_api.ApiError) as raised:
            adapter.post_repo("issues/1/dependencies", {"index": 2})

        self.assertEqual(raised.exception.status, 409)
        self.assertIn("POST", str(raised.exception))
        self.assertIn("already exists", str(raised.exception))

    def test_repo_context_uses_git_remote_origin(self):
        completed = subprocess.CompletedProcess(
            args=["git"], returncode=0, stdout="git@forge.example:owner/repo.git\n", stderr=""
        )
        with mock.patch("subprocess.run", return_value=completed):
            self.assertEqual(tea_api.discover_repo_context(), tea_api.RepoContext("owner", "repo"))


if __name__ == "__main__":
    unittest.main()
