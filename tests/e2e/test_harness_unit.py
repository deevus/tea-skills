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


if __name__ == "__main__":
    unittest.main()
