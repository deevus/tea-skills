import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.e2e.harness.model import RunContext
from tests.e2e.harness.scenarios import load_scenarios
from tests.e2e.harness.template import render_template


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
        from tests.e2e.harness.audit import AuditAssertionError, assert_audit

        with self.assertRaisesRegex(AuditAssertionError, "tea.issues.create"):
            assert_audit([], {"events": [{"root": "tea.issues.create", "min": 1, "max": 1}]})

    def test_audit_expectations_ignore_failed_required_events(self):
        from tests.e2e.harness.audit import AuditAssertionError, assert_audit
        from tests.e2e.harness.model import AuditEvent

        events = [AuditEvent("tea.issues.create", [], "/repo", 1, True, "tea")]
        with self.assertRaisesRegex(AuditAssertionError, "tea.issues.create"):
            assert_audit(events, {"events": [{"root": "tea.issues.create", "min": 1}]})

    def test_audit_budgets_fail_on_repeated_root(self):
        from tests.e2e.harness.audit import AuditAssertionError, assert_audit
        from tests.e2e.harness.model import AuditEvent

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

    def test_claude_trace_parser_extracts_skill_loaded_events(self):
        from tests.e2e.harness.agents.claude_code import parse_claude_stream_json

        lines = [
            json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Using create-issue to create the issue."}]}}),
            json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "create-issue"}}]}}),
        ]
        events = parse_claude_stream_json(lines)
        skills = [event.name for event in events if event.kind == "skill.loaded"]
        self.assertIn("create-issue", skills)

    def test_claude_code_adapter_stream_json_print_command_is_verbose(self):
        from tests.e2e.harness.agents.claude_code import ClaudeCodeAdapter

        captured: dict[str, list[str]] = {}

        def fake_run(command, **kwargs):
            captured["command"] = command
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch("tests.e2e.harness.agents.claude_code.subprocess.run", side_effect=fake_run):
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
        from tests.e2e.harness.agents.claude_code import ClaudeCodeAdapter

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
            with mock.patch("tests.e2e.harness.agents.claude_code.subprocess.run", side_effect=fake_run):
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
        from tests.e2e.harness.agents.claude_code import ClaudeCodeAdapter

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
            with mock.patch("tests.e2e.harness.agents.claude_code.subprocess.run", side_effect=fake_run):
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


if __name__ == "__main__":
    unittest.main()
