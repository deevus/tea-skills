import json
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
