import os
import shutil
import unittest
from pathlib import Path

from tests.e2e.harness.agents.claude_code import ClaudeCodeAdapter
from tests.e2e.harness.model import RunContext
from tests.e2e.harness.runner import ScenarioRunner
from tests.e2e.harness.scenarios import load_scenarios
from tests.e2e.suites.tea.normalize import normalize_raw_audit_event
from tests.e2e.suites.tea.provision import cleanup_run, create_org_and_repo, new_run_id
from tests.e2e.suites.tea.tea_spy import create_tea_spy
from tests.e2e.suites.tea.verify_forgejo import verify_state

ROOT = Path(__file__).resolve().parents[2]


def e2e_run_root(run_id: str) -> Path:
    base = Path(os.environ.get("TEA_SKILLS_E2E_ARTIFACT_DIR", ROOT / ".e2e-artifacts"))
    return base / run_id


@unittest.skipUnless(os.environ.get("TEA_SKILLS_E2E") == "1", "set TEA_SKILLS_E2E=1 to run live agent E2E tests")
class TeaSkillsAgentE2ETests(unittest.TestCase):
    def test_create_issue_scenario(self):
        real_tea = shutil.which("tea")
        self.assertIsNotNone(real_tea, "tea must be installed")
        run_id = new_run_id()
        root = e2e_run_root(run_id)
        root.mkdir(parents=True, exist_ok=True)
        run = create_org_and_repo(root, run_id)
        try:
            scenario_path = ROOT / "tests/e2e/suites/tea/scenarios/issues.json"
            defaults_path = ROOT / "tests/e2e/suites/tea/defaults.json"
            scenario = load_scenarios(scenario_path, defaults_path)[0]
            ctx = RunContext(run.run_id, run.org, run.repo, run.workspace, run.artifact_dir)
            scenario_artifacts = run.artifact_dir / scenario.name.replace(" ", "-")
            spy = create_tea_spy(root / "spy", Path(real_tea), scenario_artifacts / "audit.jsonl")
            adapter = ClaudeCodeAdapter(plugin_dir=ROOT)

            def verifier(expectations, context):
                return verify_state(expectations, context, run.config)

            runner = ScenarioRunner(adapter, normalize_raw_audit_event, verifier)
            env = {"PATH": f"{spy.path_prefix}{os.pathsep}{os.environ.get('PATH', '')}"}
            result = runner.run(scenario, ctx, env)
            self.assertTrue(
                result.passed,
                f"{result.failure_class}: {result.message}; artifacts: {scenario_artifacts}",
            )
        finally:
            cleanup_run(run, keep_remote=os.environ.get("TEA_SKILLS_E2E_KEEP_REMOTE") == "1")


if __name__ == "__main__":
    unittest.main()
