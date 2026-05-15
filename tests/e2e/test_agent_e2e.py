import os
import shutil
import unittest
from pathlib import Path

from dokimasia.agents.claude_code import ClaudeCodeAdapter
from dokimasia.agents.pi import PiAdapter
from dokimasia.core.model import RunContext
from dokimasia.core.runner import ScenarioRunner
from dokimasia.core.scenarios import load_scenarios
from tests.e2e.tea_suite.normalize import normalize_raw_audit_event
from tests.e2e.tea_suite.provision import cleanup_run, create_org_and_repo, new_run_id
from dokimasia.suite.spy import create_spy
from tests.e2e.tea_suite.verify_forgejo import verify_state

ROOT = Path(__file__).resolve().parents[2]


def e2e_run_root(run_id: str) -> Path:
    base = Path(os.environ.get("TEA_SKILLS_E2E_ARTIFACT_DIR", ROOT / ".e2e-artifacts"))
    return base / run_id


def make_agent_adapter():
    agent = os.environ.get("TEA_SKILLS_E2E_AGENT", "claude").lower()
    if agent == "claude":
        return ClaudeCodeAdapter(plugin_dir=ROOT)
    if agent == "pi":
        return PiAdapter(skills_dir=ROOT / "skills")
    raise ValueError(f"unknown TEA_SKILLS_E2E_AGENT: {agent}")


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
            scenario_path = ROOT / "tests/e2e/tea_suite/scenarios/issues.yaml"
            defaults_path = ROOT / "tests/e2e/tea_suite/defaults.yaml"
            scenario = load_scenarios(scenario_path, defaults_path)[0]
            ctx = RunContext(run.run_id, run.org, run.repo, run.workspace, run.artifact_dir)
            scenario_artifacts = run.artifact_dir / scenario.name.replace(" ", "-")
            spy = create_spy(
                root=root / "spy",
                executable_name="tea",
                real_executable=Path(real_tea),
                audit_log=scenario_artifacts / "audit.jsonl",
                source="tea",
            )
            adapter = make_agent_adapter()

            def verifier(expectations, context):
                return verify_state(expectations, context, run.config)

            runner = ScenarioRunner(
                adapter,
                normalize_raw_audit_event,
                verifier,
                audit_log_env_var="TEA_SKILLS_AUDIT_LOG",
            )
            env = spy.env_with_path(os.environ)
            result = runner.run(scenario, ctx, env)
            self.assertTrue(
                result.passed,
                f"{result.failure_class}: {result.message}; artifacts: {scenario_artifacts}",
            )
        finally:
            cleanup_run(run, keep_remote=os.environ.get("TEA_SKILLS_E2E_KEEP_REMOTE") == "1")


if __name__ == "__main__":
    unittest.main()
