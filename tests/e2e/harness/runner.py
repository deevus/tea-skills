from __future__ import annotations

from typing import Any, Callable

from .audit import AuditAssertionError, assert_audit, load_audit_events
from .model import AuditEvent, RunContext, Scenario, ScenarioResult
from .template import render_template


def _render_data(value: Any, data: dict[str, Any]) -> Any:
    if isinstance(value, str):
        return render_template(value, data)
    if isinstance(value, list):
        return [_render_data(item, data) for item in value]
    if isinstance(value, dict):
        return {key: _render_data(item, data) for key, item in value.items()}
    return value


def _skill_name_matches(actual: str | None, expected: str) -> bool:
    if actual is None:
        return False
    return actual == expected or actual.endswith(f":{expected}")


class ScenarioRunner:
    def __init__(
        self,
        agent_adapter: Any,
        audit_normalizer: Callable[[dict[str, Any]], AuditEvent],
        state_verifier: Callable[[list[dict[str, Any]], RunContext], list[dict[str, Any]]],
    ):
        self.agent_adapter = agent_adapter
        self.audit_normalizer = audit_normalizer
        self.state_verifier = state_verifier

    def _assert_trace(self, scenario: Scenario, trace_events: list[Any]) -> str | None:
        for expected in scenario.expect_trace.get("events", []):
            if expected.get("kind") == "skill.loaded":
                name = expected["name"]
                if not any(event.kind == "skill.loaded" and _skill_name_matches(event.name, name) for event in trace_events):
                    return f"expected skill to load: {name}"
        return None

    def _write_fixtures(self, scenario: Scenario, ctx: RunContext) -> None:
        data = ctx.template_data()
        for relative, content in scenario.fixtures.get("files", {}).items():
            path = ctx.workspace / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(render_template(content, data), encoding="utf-8")

    def run(self, scenario: Scenario, ctx: RunContext, env: dict[str, str]) -> ScenarioResult:
        assert ctx.artifact_dir is not None
        scenario_artifacts = ctx.artifact_dir / scenario.name.replace(" ", "-")
        scenario_artifacts.mkdir(parents=True, exist_ok=True)
        audit_log = scenario_artifacts / "audit.jsonl"
        if audit_log.exists():
            audit_log.unlink()

        self._write_fixtures(scenario, ctx)
        run_env = dict(env)
        run_env["TEA_SKILLS_AUDIT_LOG"] = str(audit_log)
        prompt = render_template(scenario.prompt, ctx.template_data())
        timeout = int(scenario.execution.get("timeout_seconds", 300))
        agent_result = self.agent_adapter.run(prompt, ctx.workspace, scenario_artifacts, run_env, timeout)

        if agent_result.timed_out:
            return ScenarioResult(scenario.name, False, "agent_timeout", "agent timed out", agent_result.trace_events, [])
        if agent_result.exit_code != 0:
            return ScenarioResult(
                scenario.name,
                False,
                "agent_nonzero_exit",
                f"agent exit code {agent_result.exit_code}",
                agent_result.trace_events,
                [],
            )

        trace_error = self._assert_trace(scenario, agent_result.trace_events)
        if trace_error:
            return ScenarioResult(
                scenario.name,
                False,
                "expected_skill_not_loaded",
                trace_error,
                agent_result.trace_events,
                [],
            )

        audit_events = load_audit_events(audit_log, self.audit_normalizer)
        rendered_expect_state = _render_data(scenario.expect_state, ctx.template_data())
        state_results = self.state_verifier(rendered_expect_state, ctx)
        failed_state = [result for result in state_results if not result.get("passed")]
        if failed_state:
            return ScenarioResult(
                scenario.name,
                False,
                "state_mismatch",
                failed_state[0].get("message", "state mismatch"),
                agent_result.trace_events,
                audit_events,
            )

        try:
            assert_audit(audit_events, scenario.expect_audit)
        except AuditAssertionError as exc:
            return ScenarioResult(
                scenario.name,
                False,
                "missing_audited_mutation",
                str(exc),
                agent_result.trace_events,
                audit_events,
            )

        return ScenarioResult(scenario.name, True, trace_events=agent_result.trace_events, audit_events=audit_events)
