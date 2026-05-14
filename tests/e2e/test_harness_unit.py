import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from dokimasia.core.model import RunContext
from dokimasia.core.scenarios import load_scenarios
from dokimasia.core.template import render_template


from tests.e2e import test_agent_e2e


class HarnessUnitTests(unittest.TestCase):
    def test_render_template_replaces_dotted_values(self):
        context = {"run": {"id": "abc123"}, "issue": {"title": "Hello"}}
        self.assertEqual(
            render_template("{{ issue.title }} / {{ run.id }}", context),
            "Hello / abc123",
        )

    def test_render_template_errors_for_missing_value(self):
        with self.assertRaisesRegex(KeyError, "missing.path"):
            render_template("{{ missing.path }}", {})

    def test_load_scenarios_merges_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            defaults = root / "defaults.json"
            scenarios = root / "scenarios.json"
            defaults.write_text(
                json.dumps({"execution": {"timeout_seconds": 10}, "expect_audit": {"budgets": {"total_commands": {"max": 5}}}}),
                encoding="utf-8",
            )
            scenarios.write_text(
                json.dumps({"scenarios": [{"name": "one", "prompt": "Run {{ run.id }}", "expect_trace": {"events": []}}]}),
                encoding="utf-8",
            )
            loaded = load_scenarios(scenarios, defaults)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].name, "one")
            self.assertEqual(loaded[0].execution["timeout_seconds"], 10)
            self.assertEqual(loaded[0].expect_audit["budgets"]["total_commands"], {"max": 5})

    def test_run_context_template_data_includes_outputs(self):
        ctx = RunContext(run_id="run-1", org="tea-e2e-run-1", repo="repo", workspace=Path("/tmp/repo"))
        ctx.outputs["issue_number"] = 7
        self.assertEqual(ctx.template_data()["context"]["issue_number"], 7)

    def test_normalize_tea_event_classifies_issue_create_as_mutation(self):
        from tests.e2e.suites.tea.normalize import normalize_raw_audit_event

        event = normalize_raw_audit_event({
            "source": "tea",
            "argv": ["issues", "create", "--title", "Hello"],
            "cwd": "/repo",
            "exit_code": 0,
        })
        self.assertEqual(event.root, "tea.issues.create")
        self.assertTrue(event.mutates)

    def test_normalize_tea_event_handles_command_options_before_subcommand(self):
        from tests.e2e.suites.tea.normalize import normalize_raw_audit_event

        event = normalize_raw_audit_event({
            "source": "tea",
            "argv": ["issues", "--repo", "foo/bar", "create", "--title", "Hello"],
            "cwd": "/repo",
            "exit_code": 0,
        })
        self.assertEqual(event.root, "tea.issues.create")
        self.assertTrue(event.mutates)

    def test_normalize_tea_event_canonicalizes_aliases(self):
        from tests.e2e.suites.tea.normalize import normalize_raw_audit_event

        event = normalize_raw_audit_event({
            "source": "tea",
            "argv": ["issue", "c", "--title", "Hello"],
            "cwd": "/repo",
            "exit_code": 0,
        })
        self.assertEqual(event.root, "tea.issues.create")
        self.assertTrue(event.mutates)

    def test_normalize_tea_event_handles_common_alias_and_option_forms(self):
        from tests.e2e.suites.tea.normalize import normalize_raw_audit_event

        cases = [
            (["issues", "-R", "origin", "create"], "tea.issues.create"),
            (["issues", "--state", "all", "create"], "tea.issues.create"),
            (["i", "c"], "tea.issues.create"),
            (["pr", "c"], "tea.pulls.create"),
            (["pulls", "m", "15"], "tea.pulls.merge"),
        ]
        for argv, root in cases:
            with self.subTest(argv=argv):
                event = normalize_raw_audit_event({
                    "source": "tea",
                    "argv": argv,
                    "cwd": "/repo",
                    "exit_code": 0,
                })
                self.assertEqual(event.root, root)
                self.assertTrue(event.mutates)

    def test_normalize_action_event_uses_action_path(self):
        from tests.e2e.suites.tea.normalize import normalize_raw_audit_event

        event = normalize_raw_audit_event({
            "source": "tea-skills-action",
            "action": "actions/issues/dependency-add.py",
            "argv": ["1", "2"],
            "cwd": "/repo",
            "exit_code": 0,
        })
        self.assertEqual(event.root, "action.issues.dependency-add")
        self.assertTrue(event.mutates)

    def test_audit_expectations_fail_when_required_event_missing(self):
        from dokimasia.audit.assertions import AuditAssertionError, assert_audit

        with self.assertRaisesRegex(AuditAssertionError, "tea.issues.create"):
            assert_audit([], {"events": [{"root": "tea.issues.create", "min": 1, "max": 1}]})

    def test_audit_expectations_ignore_failed_required_events(self):
        from dokimasia.audit.assertions import AuditAssertionError, assert_audit
        from dokimasia.core.model import AuditEvent

        events = [AuditEvent("tea.issues.create", [], "/repo", 1, True, "tea")]
        with self.assertRaisesRegex(AuditAssertionError, "tea.issues.create"):
            assert_audit(events, {"events": [{"root": "tea.issues.create", "min": 1}]})

    def test_audit_budgets_fail_on_repeated_root(self):
        from dokimasia.audit.assertions import AuditAssertionError, assert_audit
        from dokimasia.core.model import AuditEvent

        events = [
            AuditEvent("tea.issues.list", [], "/repo", 0, False, "tea"),
            AuditEvent("tea.issues.list", [], "/repo", 0, False, "tea"),
            AuditEvent("tea.issues.list", [], "/repo", 0, False, "tea"),
        ]
        with self.assertRaisesRegex(AuditAssertionError, "tea.issues.list"):
            assert_audit(events, {"budgets": {"per_root": {"tea.issues.list": {"max": 2}}}})

    def test_tea_spy_writes_wrapper(self):
        from tests.e2e.suites.tea.tea_spy import create_tea_spy

        with tempfile.TemporaryDirectory() as tmp:
            spy = create_tea_spy(Path(tmp), Path("/bin/tea-real"), Path(tmp) / "audit.jsonl")
            self.assertTrue((spy.bin_dir / "tea").exists())
            text = (spy.bin_dir / "tea").read_text(encoding="utf-8")
            self.assertIn("/bin/tea-real", text)
            self.assertIn("audit.jsonl", text)
            self.assertIn(str(spy.bin_dir), spy.path_prefix)



    def test_e2e_run_root_defaults_to_repo_artifacts_dir(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            run_root = test_agent_e2e.e2e_run_root("abc123")
        self.assertEqual(run_root, test_agent_e2e.ROOT / ".e2e-artifacts" / "abc123")

    def test_e2e_run_root_uses_env_artifact_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"TEA_SKILLS_E2E_ARTIFACT_DIR": tmp}, clear=True):
                run_root = test_agent_e2e.e2e_run_root("abc123")
        self.assertEqual(run_root, Path(tmp) / "abc123")

    def test_make_agent_adapter_defaults_to_claude(self):
        from dokimasia.agents.claude_code import ClaudeCodeAdapter

        with mock.patch.dict(os.environ, {}, clear=True):
            adapter = test_agent_e2e.make_agent_adapter()
        self.assertIsInstance(adapter, ClaudeCodeAdapter)
        self.assertEqual(adapter.plugin_dir, test_agent_e2e.ROOT)

    def test_make_agent_adapter_supports_pi(self):
        from dokimasia.agents.pi import PiAdapter

        with mock.patch.dict(os.environ, {"TEA_SKILLS_E2E_AGENT": "pi"}, clear=True):
            adapter = test_agent_e2e.make_agent_adapter()
        self.assertIsInstance(adapter, PiAdapter)
        self.assertEqual(adapter.skills_dir, test_agent_e2e.ROOT / "skills")

    def test_make_agent_adapter_rejects_unknown_agent(self):
        with mock.patch.dict(os.environ, {"TEA_SKILLS_E2E_AGENT": "unknown"}, clear=True):
            with self.assertRaisesRegex(ValueError, "unknown TEA_SKILLS_E2E_AGENT"):
                test_agent_e2e.make_agent_adapter()

    def test_claude_trace_parser_extracts_skill_loaded_events(self):
        from dokimasia.agents.claude_code import parse_claude_stream_json

        lines = [
            json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Using create-issue to create the issue."}]}}),
            json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "create-issue"}}]}}),
        ]
        events = parse_claude_stream_json(lines)
        skills = [event.name for event in events if event.kind == "skill.loaded"]
        self.assertIn("create-issue", skills)

    def test_claude_code_adapter_stream_json_print_command_is_verbose(self):
        from dokimasia.agents.claude_code import ClaudeCodeAdapter

        captured: dict[str, list[str]] = {}

        def fake_run(command, **kwargs):
            captured["command"] = command
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch("dokimasia.agents.claude_code.subprocess.run", side_effect=fake_run):
                ClaudeCodeAdapter(claude_bin="claude").run(
                    "hello",
                    workspace=root,
                    artifact_dir=root / "artifacts",
                    env={},
                    timeout_seconds=5,
                )

        command = captured["command"]
        self.assertIn("--print", command)
        self.assertEqual(command[command.index("--output-format") + 1], "stream-json")
        self.assertIn("--verbose", command)

    def test_claude_code_adapter_preserves_timeout_bytes_stream_json(self):
        from dokimasia.agents.claude_code import ClaudeCodeAdapter

        stream_line = json.dumps({
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "Using create-issue to create the issue."},
                ],
            },
        })
        stdout_bytes = f"{stream_line}\n".encode("utf-8")
        stderr_bytes = b"partial stderr"

        def fake_run(command, **kwargs):
            raise subprocess.TimeoutExpired(
                command,
                kwargs.get("timeout"),
                output=stdout_bytes,
                stderr=stderr_bytes,
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact_dir = root / "artifacts"
            with mock.patch("dokimasia.agents.claude_code.subprocess.run", side_effect=fake_run):
                result = ClaudeCodeAdapter(claude_bin="claude").run(
                    "hello",
                    workspace=root,
                    artifact_dir=artifact_dir,
                    env={},
                    timeout_seconds=5,
                )

            self.assertTrue(result.timed_out)
            self.assertEqual(result.exit_code, 124)
            self.assertEqual((artifact_dir / "agent.stdout.jsonl").read_text(encoding="utf-8"), f"{stream_line}\n")
            self.assertEqual((artifact_dir / "agent.stderr.txt").read_text(encoding="utf-8"), "partial stderr")
            skills = [event.name for event in result.trace_events if event.kind == "skill.loaded"]
            self.assertIn("create-issue", skills)

    def test_claude_code_adapter_preserves_timeout_string_stream_json(self):
        from dokimasia.agents.claude_code import ClaudeCodeAdapter

        stream_line = json.dumps({
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "Using create-issue to create the issue."},
                ],
            },
        })
        stdout_text = f"{stream_line}\n"
        stderr_text = "partial stderr"

        def fake_run(command, **kwargs):
            raise subprocess.TimeoutExpired(
                command,
                kwargs.get("timeout"),
                output=stdout_text,
                stderr=stderr_text,
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact_dir = root / "artifacts"
            with mock.patch("dokimasia.agents.claude_code.subprocess.run", side_effect=fake_run):
                result = ClaudeCodeAdapter(claude_bin="claude").run(
                    "hello",
                    workspace=root,
                    artifact_dir=artifact_dir,
                    env={},
                    timeout_seconds=5,
                )

            self.assertTrue(result.timed_out)
            self.assertEqual(result.exit_code, 124)
            self.assertEqual((artifact_dir / "agent.stdout.jsonl").read_text(encoding="utf-8"), stdout_text)
            self.assertEqual((artifact_dir / "agent.stderr.txt").read_text(encoding="utf-8"), stderr_text)
            skills = [event.name for event in result.trace_events if event.kind == "skill.loaded"]
            self.assertIn("create-issue", skills)

    def test_pi_trace_parser_extracts_skill_loaded_from_current_skill_read(self):
        from dokimasia.agents.pi import parse_pi_json_events

        lines = [
            json.dumps({
                "type": "tool_execution_start",
                "toolName": "read",
                "args": {"path": "/repo/skills/create-issue/SKILL.md"},
            }),
            json.dumps({
                "type": "message_update",
                "assistantMessageEvent": {"type": "text_delta", "delta": "Using create-issue"},
            }),
        ]
        events = parse_pi_json_events(lines, skills_dir=Path("/repo/skills"))
        skills = [event.name for event in events if event.kind == "skill.loaded"]
        self.assertEqual(skills, ["create-issue"])

    def test_pi_trace_parser_ignores_skill_reads_outside_current_checkout(self):
        from dokimasia.agents.pi import parse_pi_json_events

        lines = [
            json.dumps({
                "type": "tool_execution_start",
                "toolName": "read",
                "args": {"path": "/old/global/skills/create-issue/SKILL.md"},
            }),
        ]
        events = parse_pi_json_events(lines, skills_dir=Path("/repo/skills"))
        self.assertEqual([event for event in events if event.kind == "skill.loaded"], [])

    def test_pi_adapter_command_uses_only_current_repo_skills(self):
        from dokimasia.agents.pi import PiAdapter

        captured: dict[str, list[str]] = {}

        def fake_run(command, **kwargs):
            captured["command"] = command
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills = root / "repo" / "skills"
            skills.mkdir(parents=True)
            with mock.patch("dokimasia.agents.pi.subprocess.run", side_effect=fake_run):
                PiAdapter(pi_bin="pi", skills_dir=skills).run(
                    "hello",
                    workspace=root,
                    artifact_dir=root / "artifacts",
                    env={},
                    timeout_seconds=5,
                )

        command = captured["command"]
        self.assertIn("--print", command)
        self.assertEqual(command[command.index("--mode") + 1], "json")
        self.assertIn("--no-session", command)
        self.assertIn("--no-skills", command)
        self.assertEqual(command[command.index("--skill") + 1], str(skills))

    def test_cleanup_guard_accepts_only_current_run_resources(self):
        from tests.e2e.suites.tea.provision import assert_safe_e2e_resource

        assert_safe_e2e_resource("tea-e2e-abc123", "abc123")
        with self.assertRaisesRegex(ValueError, "refusing"):
            assert_safe_e2e_resource("production", "abc123")
        with self.assertRaisesRegex(ValueError, "refusing"):
            assert_safe_e2e_resource("tea-e2e-other", "abc123")


    def test_create_org_and_repo_writes_local_context_without_pushing(self):
        from actions.internal.tea_api import TeaConfig
        from tests.e2e.suites.tea import provision

        api_calls = []
        git_calls = []

        def fake_api(config, method, endpoint, body=None):
            api_calls.append((method, endpoint))
            if method == "POST" and endpoint.endswith("/repos"):
                return {"clone_url": "https://example.test/org/repo.git"}
            return {}

        def fake_run(command, **kwargs):
            git_calls.append(command)
            if command[:2] == ["git", "clone"]:
                Path(command[3]).mkdir(parents=True)
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("tests.e2e.suites.tea.provision.read_tea_config", return_value=TeaConfig("token", "https://forgejo.test")), \
                 mock.patch("tests.e2e.suites.tea.provision.api_request", side_effect=fake_api), \
                 mock.patch("tests.e2e.suites.tea.provision.subprocess.run", side_effect=fake_run):
                run = provision.create_org_and_repo(Path(tmp), "abc123")
                self.assertEqual(run.org, "tea-e2e-abc123")
                self.assertTrue((run.workspace / "AGENTS.md").exists())
                self.assertEqual(git_calls, [["git", "clone", "https://example.test/org/repo.git", str(run.workspace)]])
                self.assertNotIn(("DELETE", "repos/tea-e2e-abc123/repo"), api_calls)

    def test_create_org_and_repo_cleans_remote_if_clone_fails(self):
        from actions.internal.tea_api import TeaConfig
        from tests.e2e.suites.tea import provision

        api_calls = []

        def fake_api(config, method, endpoint, body=None):
            api_calls.append((method, endpoint))
            if method == "POST" and endpoint.endswith("/repos"):
                return {"clone_url": "https://example.test/org/repo.git"}
            return {}

        def fake_run(command, **kwargs):
            raise subprocess.CalledProcessError(128, command)

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("tests.e2e.suites.tea.provision.read_tea_config", return_value=TeaConfig("token", "https://forgejo.test")), \
                 mock.patch("tests.e2e.suites.tea.provision.api_request", side_effect=fake_api), \
                 mock.patch("tests.e2e.suites.tea.provision.subprocess.run", side_effect=fake_run):
                with self.assertRaises(subprocess.CalledProcessError):
                    provision.create_org_and_repo(Path(tmp), "abc123")

        self.assertIn(("DELETE", "repos/tea-e2e-abc123/repo"), api_calls)
        self.assertIn(("DELETE", "orgs/tea-e2e-abc123"), api_calls)

    def test_issue_verifier_matches_title_and_body_file(self):
        from dokimasia.core.model import RunContext
        from tests.e2e.suites.tea.verify_forgejo import verify_issue_expectation

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "issue-body.md").write_text("body marker", encoding="utf-8")
            ctx = RunContext("run", "org", "repo", workspace)
            issues = [{"number": 1, "title": "Title", "body": "body marker", "state": "open", "labels": []}]
            result = verify_issue_expectation(
                {"id": "main", "match": {"title": "Title"}, "assert": {"count": 1, "state": "open", "body_equals_file": "issue-body.md"}},
                ctx,
                issues,
            )
            self.assertTrue(result["passed"])
            self.assertEqual(ctx.state["main"]["number"], 1)

    def test_runner_fails_when_expected_skill_is_missing(self):
        from dokimasia.core.model import AgentRunResult, Scenario
        from dokimasia.core.runner import ScenarioRunner

        class FakeAdapter:
            def run(self, prompt, workspace, artifact_dir, env, timeout_seconds):
                stdout = artifact_dir / "stdout.txt"
                stderr = artifact_dir / "stderr.txt"
                stdout.write_text("", encoding="utf-8")
                stderr.write_text("", encoding="utf-8")
                return AgentRunResult(0, stdout, stderr, None, [], 0.01, False)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx = RunContext("run", "org", "repo", root / "workspace", root / "artifacts")
            ctx.workspace.mkdir()
            scenario = Scenario(
                name="missing skill",
                prompt="Do it",
                expect_trace={"events": [{"kind": "skill.loaded", "name": "create-issue"}]},
            )
            result = ScenarioRunner(FakeAdapter(), lambda raw: raw, lambda expectations, ctx: []).run(scenario, ctx, {})
            self.assertFalse(result.passed)
            self.assertEqual(result.failure_class, "expected_skill_not_loaded")

    def test_runner_accepts_plugin_qualified_skill_names(self):
        from dokimasia.core.model import AgentRunResult, Scenario, TraceEvent
        from dokimasia.core.runner import ScenarioRunner

        class FakeAdapter:
            def run(self, prompt, workspace, artifact_dir, env, timeout_seconds):
                stdout = artifact_dir / "stdout.txt"
                stderr = artifact_dir / "stderr.txt"
                stdout.write_text("", encoding="utf-8")
                stderr.write_text("", encoding="utf-8")
                return AgentRunResult(
                    0,
                    stdout,
                    stderr,
                    None,
                    [TraceEvent(kind="skill.loaded", name="tea:create-issue")],
                    0.01,
                    False,
                )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx = RunContext("run", "org", "repo", root / "workspace", root / "artifacts")
            ctx.workspace.mkdir()
            scenario = Scenario(
                name="qualified skill",
                prompt="Do it",
                expect_trace={"events": [{"kind": "skill.loaded", "name": "create-issue"}]},
            )
            result = ScenarioRunner(FakeAdapter(), lambda raw: raw, lambda expectations, ctx: []).run(scenario, ctx, {})
            self.assertTrue(result.passed, result.message)


    def test_issue_verifier_supports_zero_count_assertion(self):
        from dokimasia.core.model import RunContext
        from tests.e2e.suites.tea.verify_forgejo import verify_issue_expectation

        with tempfile.TemporaryDirectory() as tmp:
            ctx = RunContext("run", "org", "repo", Path(tmp))
            result = verify_issue_expectation(
                {"match": {"title": "Missing"}, "assert": {"count": 0}},
                ctx,
                [{"number": 1, "title": "Present", "body": "", "state": "open", "labels": []}],
            )
            self.assertTrue(result["passed"])


if __name__ == "__main__":
    unittest.main()
