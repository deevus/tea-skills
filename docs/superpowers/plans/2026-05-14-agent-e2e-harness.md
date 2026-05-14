# Agent E2E Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working vertical slice of the audited agent E2E harness for `tea-skills`, including action audit logging, generic harness primitives, a tea suite, a Claude Code adapter, and one live create-issue scenario.

**Architecture:** Keep the harness core generic and in-repo under `tests/e2e/harness/`, with Forgejo/tea-specific behavior under `tests/e2e/suites/tea/`. Use stdlib-only Python and `unittest`-style tests so the current repo remains dependency-free; these tests remain pytest-collectable when pytest is available. The first vertical slice proves the full evidence chain: expected skill trace, audited `tea` mutation, independent Forgejo state verification, budgets, timeout, and cleanup.

**Tech Stack:** Python 3 stdlib (`unittest`, `dataclasses`, `json`, `subprocess`, `tempfile`, `urllib`), existing `actions/internal/tea_api.py`, `tea` CLI, Claude Code CLI headless `--print --output-format stream-json` adapter.

---

## Scope and sequencing note

The ADR describes a harness that can eventually test every skill. This plan deliberately implements a complete vertical slice first, not the full scenario catalog. After this plan passes against a real Forgejo server, write a follow-up scenario-expansion plan for every current skill. This avoids building a large catalog before the trace/audit/state contracts are proven.

## File structure

- Modify `actions/internal/tea_api.py`
  - Add permanent, env-gated action audit helpers: `audit_action()`, `action_name_from_path()`, and `run_action()`.
- Modify all executable `actions/**/*.py` files except `actions/internal/tea_api.py`
  - Use `run_action(Path(__file__), sys.argv[1:], main)` at the process boundary.
- Modify `tests/test_tea_api.py`
  - Unit-test audit no-op, JSONL output, wrapper exit logging, and exception logging.
- Modify `tests/test_action_contracts.py`
  - Assert every action script delegates through `run_action`.
- Create `tests/e2e/harness/__init__.py`
- Create `tests/e2e/harness/model.py`
  - Shared dataclasses for trace events, audit events, scenarios, expectations, run context, and results.
- Create `tests/e2e/harness/template.py`
  - Small `{{ dotted.path }}` renderer with no external dependencies.
- Create `tests/e2e/harness/scenarios.py`
  - JSON scenario/default loader and renderer.
- Create `tests/e2e/harness/audit.py`
  - Read JSONL audit events, normalize fields, enforce expected events and budgets.
- Create `tests/e2e/harness/agents/__init__.py`
- Create `tests/e2e/harness/agents/base.py`
  - Agent adapter protocol and common command runner.
- Create `tests/e2e/harness/agents/claude_code.py`
  - Claude Code headless adapter and skill trace parser.
- Create `tests/e2e/harness/runner.py`
  - Scenario runner that coordinates fixtures, agent execution, trace assertions, audit assertions, state verification, and output capture.
- Create `tests/e2e/suites/__init__.py`
- Create `tests/e2e/suites/tea/__init__.py`
- Create `tests/e2e/suites/tea/normalize.py`
  - Map `tea` argv and action paths to normalized roots and mutation flags.
- Create `tests/e2e/suites/tea/tea_spy.py`
  - Generate a temporary `tea` wrapper that writes audit JSONL and delegates to real `tea`.
- Create `tests/e2e/suites/tea/provision.py`
  - Preflight, disposable org/repo create/delete, clone workspace, and safety guards.
- Create `tests/e2e/suites/tea/verify_forgejo.py`
  - Direct API verifier for the first `forgejo.issue` state assertion.
- Create `tests/e2e/suites/tea/defaults.json`
  - Default execution and command budgets.
- Create `tests/e2e/suites/tea/scenarios/issues.json`
  - First live single-turn create-issue scenario.
- Create `tests/e2e/test_agent_e2e.py`
  - Opt-in unittest host; skips unless `TEA_SKILLS_E2E=1`.
- Create `tests/e2e/test_harness_unit.py`
  - Fast stdlib unit tests for templating, audit budgets, normalizer, fake runner behavior.

---

### Task 1: Add env-gated audit logging to bundled actions

**Files:**
- Modify: `actions/internal/tea_api.py`
- Modify: all executable `actions/**/*.py` except `actions/internal/tea_api.py`
- Modify: `tests/test_tea_api.py`
- Modify: `tests/test_action_contracts.py`

- [ ] **Step 1: Add failing audit tests**

Append these tests to `TeaApiCoreTests` in `tests/test_tea_api.py` before the `if __name__ == "__main__"` block:

```python
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
```

- [ ] **Step 2: Run the focused failing tests**

Run:

```bash
python -m unittest tests.test_tea_api.TeaApiCoreTests.test_audit_action_noops_without_env \
  tests.test_tea_api.TeaApiCoreTests.test_audit_action_writes_jsonl_when_env_is_set \
  tests.test_tea_api.TeaApiCoreTests.test_run_action_logs_exit_code \
  tests.test_tea_api.TeaApiCoreTests.test_run_action_logs_unhandled_exception_then_reraises -v
```

Expected: FAIL because `audit_action` and `run_action` do not exist yet.

- [ ] **Step 3: Implement audit helpers**

In `actions/internal/tea_api.py`, add `import sys` and `from datetime import datetime, timezone` near the existing imports. Then add this block immediately before `def default_adapter()`:

```python
def action_name_from_path(path: Path) -> str:
    """Return a stable actions/... path for an action executable."""
    resolved = Path(path)
    parts = resolved.parts
    if "actions" in parts:
        index = len(parts) - 1 - list(reversed(parts)).index("actions")
        return "/".join(parts[index:])
    return str(resolved)


def audit_action(
    action: str,
    argv: list[str],
    exit_code: int,
    phase: str = "finish",
    error: str | None = None,
) -> None:
    """Append an action audit event when TEA_SKILLS_AUDIT_LOG is set."""
    log_path = os.environ.get("TEA_SKILLS_AUDIT_LOG")
    if not log_path or os.environ.get("TEA_SKILLS_AUDIT_DISABLE") == "1":
        return

    event: dict[str, Any] = {
        "source": "tea-skills-action",
        "action": action,
        "argv": list(argv),
        "cwd": os.getcwd(),
        "pid": os.getpid(),
        "phase": phase,
        "exit_code": exit_code,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if error:
        event["error"] = error

    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


def run_action(action_file: Path, argv: list[str], main: Callable[[list[str]], int]) -> int:
    """Run an action main function and record its audited finish event."""
    action = action_name_from_path(action_file)
    try:
        exit_code = int(main(argv))
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        audit_action(action=action, argv=argv, exit_code=code)
        raise
    except Exception as exc:
        audit_action(
            action=action,
            argv=argv,
            exit_code=1,
            error=f"{exc.__class__.__name__}: {exc}",
        )
        raise
    audit_action(action=action, argv=argv, exit_code=exit_code)
    return exit_code
```

- [ ] **Step 4: Update every action executable to use the wrapper**

Run this one-off migration script from the repository root:

```bash
python - <<'PY'
from pathlib import Path

for path in sorted(Path('actions').glob('*/*.py')):
    if path.parts[:2] == ('actions', 'internal'):
        continue
    text = path.read_text(encoding='utf-8')
    text = text.replace(
        'from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter',
        'from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter, run_action',
    )
    text = text.replace(
        'if __name__ == "__main__":\n    raise SystemExit(main(sys.argv[1:]))\n',
        'if __name__ == "__main__":\n    raise SystemExit(run_action(Path(__file__), sys.argv[1:], main))\n',
    )
    path.write_text(text, encoding='utf-8')
PY
```

- [ ] **Step 5: Add an action contract test for the wrapper**

Append this method to `ActionContractTests` in `tests/test_action_contracts.py`:

```python
    def test_actions_use_audit_wrapper(self):
        for relative in EXPECTED_ACTIONS:
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(action=relative):
                self.assertIn("run_action", text)
                self.assertIn("Path(__file__)", text)
```

- [ ] **Step 6: Run tests for Task 1**

Run:

```bash
python -m unittest tests.test_tea_api tests.test_action_contracts -v
```

Expected: PASS.

- [ ] **Step 7: Commit Task 1**

```bash
git add actions tests/test_tea_api.py tests/test_action_contracts.py
git commit -m "feat: audit bundled action invocations"
```

---

### Task 2: Add generic harness models, templating, and scenario loading

**Files:**
- Create: `tests/e2e/harness/__init__.py`
- Create: `tests/e2e/harness/model.py`
- Create: `tests/e2e/harness/template.py`
- Create: `tests/e2e/harness/scenarios.py`
- Create: `tests/e2e/test_harness_unit.py`

- [ ] **Step 1: Create failing unit tests for template rendering and scenario loading**

Create `tests/e2e/test_harness_unit.py` with this initial content:

```python
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
```

- [ ] **Step 2: Run the failing harness tests**

Run:

```bash
python -m unittest tests.e2e.test_harness_unit -v
```

Expected: FAIL because `tests/e2e/harness/*` does not exist.

- [ ] **Step 3: Create package marker files**

Run:

```bash
mkdir -p tests/e2e/harness
: > tests/e2e/__init__.py
: > tests/e2e/harness/__init__.py
```

- [ ] **Step 4: Implement the generic model file**

Create `tests/e2e/harness/model.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TraceEvent:
    kind: str
    name: str | None = None
    tool: str | None = None
    text: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AuditEvent:
    root: str
    argv: list[str]
    cwd: str
    exit_code: int
    mutates: bool
    source: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRunResult:
    exit_code: int
    stdout_path: Path
    stderr_path: Path
    raw_trace_path: Path | None
    trace_events: list[TraceEvent]
    duration_seconds: float
    timed_out: bool = False


@dataclass
class Scenario:
    name: str
    prompt: str
    tags: list[str] = field(default_factory=list)
    fixtures: dict[str, Any] = field(default_factory=dict)
    expect_trace: dict[str, Any] = field(default_factory=dict)
    expect_audit: dict[str, Any] = field(default_factory=dict)
    expect_state: list[dict[str, Any]] = field(default_factory=list)
    outputs: dict[str, str] = field(default_factory=dict)
    execution: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)


@dataclass
class RunContext:
    run_id: str
    org: str
    repo: str
    workspace: Path
    artifact_dir: Path | None = None
    outputs: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)

    def template_data(self) -> dict[str, Any]:
        return {
            "run": {"id": self.run_id},
            "org": self.org,
            "repo": self.repo,
            "workspace": str(self.workspace),
            "context": self.outputs,
            "state": self.state,
        }


@dataclass
class ScenarioResult:
    name: str
    passed: bool
    failure_class: str | None = None
    message: str = ""
    trace_events: list[TraceEvent] = field(default_factory=list)
    audit_events: list[AuditEvent] = field(default_factory=list)
```

- [ ] **Step 5: Implement the template renderer**

Create `tests/e2e/harness/template.py`:

```python
from __future__ import annotations

import re
from typing import Any

_TOKEN = re.compile(r"{{\s*([A-Za-z0-9_.-]+)\s*}}")


def resolve_dotted(path: str, data: dict[str, Any]) -> Any:
    value: Any = data
    for part in path.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
            continue
        raise KeyError(path)
    return value


def render_template(text: str, data: dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return str(resolve_dotted(key, data))

    return _TOKEN.sub(replace, text)
```

- [ ] **Step 6: Implement the JSON scenario loader**

Create `tests/e2e/harness/scenarios.py`:

```python
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .model import Scenario


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_scenarios(path: Path, defaults_path: Path | None = None) -> list[Scenario]:
    defaults = load_json(defaults_path) if defaults_path else {}
    document = load_json(path)
    scenarios: list[Scenario] = []
    for item in document.get("scenarios", []):
        merged = deep_merge(defaults, item)
        scenarios.append(
            Scenario(
                name=merged["name"],
                prompt=merged["prompt"],
                tags=merged.get("tags", []),
                fixtures=merged.get("fixtures", {}),
                expect_trace=merged.get("expect_trace", {}),
                expect_audit=merged.get("expect_audit", {}),
                expect_state=merged.get("expect_state", []),
                outputs=merged.get("outputs", {}),
                execution=merged.get("execution", {}),
                depends_on=merged.get("depends_on", []),
            )
        )
    return scenarios
```

- [ ] **Step 7: Run tests for Task 2**

Run:

```bash
python -m unittest tests.e2e.test_harness_unit -v
```

Expected: PASS.

- [ ] **Step 8: Commit Task 2**

```bash
git add tests/e2e
git commit -m "feat: add generic e2e scenario model"
```

---

### Task 3: Add audit ingestion, normalization, and budget assertions

**Files:**
- Create: `tests/e2e/harness/audit.py`
- Create: `tests/e2e/suites/__init__.py`
- Create: `tests/e2e/suites/tea/__init__.py`
- Create: `tests/e2e/suites/tea/normalize.py`
- Modify: `tests/e2e/test_harness_unit.py`

- [ ] **Step 1: Add failing audit and normalizer tests**

Append these tests to `HarnessUnitTests`:

```python
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
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
python -m unittest tests.e2e.test_harness_unit -v
```

Expected: FAIL because audit and normalizer modules do not exist.

- [ ] **Step 3: Create tea suite package markers**

Run:

```bash
mkdir -p tests/e2e/suites/tea
: > tests/e2e/suites/__init__.py
: > tests/e2e/suites/tea/__init__.py
```

- [ ] **Step 4: Implement tea audit normalizer**

Create `tests/e2e/suites/tea/normalize.py`:

```python
from __future__ import annotations

from typing import Any

from tests.e2e.harness.model import AuditEvent

_MUTATING_TEA_VERBS = {
    "create", "edit", "close", "reopen", "delete", "del", "rm", "merge", "approve", "reject", "review"
}
_MUTATING_ACTION_WORDS = {
    "add", "remove", "edit", "lock", "unlock", "pin", "unpin", "create", "set", "cancel"
}


def _clean_action_root(action: str) -> str:
    clean = action.removesuffix(".py")
    if clean.startswith("actions/"):
        clean = clean[len("actions/"):]
    return "action." + clean.replace("/", ".")


def _tea_root(argv: list[str]) -> str:
    if not argv:
        return "tea"
    return "tea." + ".".join(part for part in argv[:2] if not part.startswith("-"))


def _tea_mutates(argv: list[str]) -> bool:
    if not argv:
        return False
    return any(part in _MUTATING_TEA_VERBS for part in argv[:3])


def _action_mutates(root: str) -> bool:
    tail = root.rsplit(".", 1)[-1]
    return any(word in tail.split("-") for word in _MUTATING_ACTION_WORDS)


def normalize_raw_audit_event(raw: dict[str, Any]) -> AuditEvent:
    source = str(raw.get("source") or "tea")
    argv = [str(arg) for arg in raw.get("argv", [])]
    cwd = str(raw.get("cwd") or "")
    exit_code = int(raw.get("exit_code", 0))

    if source == "tea-skills-action":
        root = _clean_action_root(str(raw.get("action") or "actions/unknown"))
        mutates = _action_mutates(root)
    else:
        root = _tea_root(argv)
        mutates = _tea_mutates(argv)

    return AuditEvent(root=root, argv=argv, cwd=cwd, exit_code=exit_code, mutates=mutates, source=source, raw=raw)
```

- [ ] **Step 5: Implement audit assertions**

Create `tests/e2e/harness/audit.py`:

```python
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from .model import AuditEvent


class AuditAssertionError(AssertionError):
    pass


def load_audit_events(path: Path, normalizer: Callable[[dict[str, Any]], AuditEvent]) -> list[AuditEvent]:
    if not path.exists():
        return []
    events: list[AuditEvent] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(normalizer(json.loads(line)))
    return events


def assert_audit(events: list[AuditEvent], expectation: dict[str, Any]) -> None:
    counts = Counter(event.root for event in events)
    for required in expectation.get("events", []):
        root = required["root"]
        actual = counts[root]
        minimum = int(required.get("min", 0))
        maximum = required.get("max")
        if actual < minimum:
            raise AuditAssertionError(f"{root} count {actual} is below min {minimum}")
        if maximum is not None and actual > int(maximum):
            raise AuditAssertionError(f"{root} count {actual} is above max {maximum}")

    budgets = expectation.get("budgets", {})
    total_commands = budgets.get("total_commands", {})
    if "max" in total_commands and len(events) > int(total_commands["max"]):
        raise AuditAssertionError(f"total command count {len(events)} is above max {total_commands['max']}")

    mutation_count = sum(1 for event in events if event.mutates)
    total_mutations = budgets.get("total_mutations", {})
    if "max" in total_mutations and mutation_count > int(total_mutations["max"]):
        raise AuditAssertionError(f"mutation count {mutation_count} is above max {total_mutations['max']}")

    for root, budget in budgets.get("per_root", {}).items():
        actual = counts[root]
        if "min" in budget and actual < int(budget["min"]):
            raise AuditAssertionError(f"{root} count {actual} is below min {budget['min']}")
        if "max" in budget and actual > int(budget["max"]):
            raise AuditAssertionError(f"{root} count {actual} is above max {budget['max']}")
```

- [ ] **Step 6: Run tests for Task 3**

Run:

```bash
python -m unittest tests.e2e.test_harness_unit -v
```

Expected: PASS.

- [ ] **Step 7: Commit Task 3**

```bash
git add tests/e2e
git commit -m "feat: add e2e audit normalization and budgets"
```

---

### Task 4: Add tea PATH spy generator

**Files:**
- Create: `tests/e2e/suites/tea/tea_spy.py`
- Modify: `tests/e2e/test_harness_unit.py`

- [ ] **Step 1: Add failing tea spy tests**

Append this test to `HarnessUnitTests`:

```python
    def test_tea_spy_writes_wrapper(self):
        from tests.e2e.suites.tea.tea_spy import create_tea_spy

        with tempfile.TemporaryDirectory() as tmp:
            spy = create_tea_spy(Path(tmp), Path("/bin/tea-real"), Path(tmp) / "audit.jsonl")
            self.assertTrue((spy.bin_dir / "tea").exists())
            text = (spy.bin_dir / "tea").read_text(encoding="utf-8")
            self.assertIn("/bin/tea-real", text)
            self.assertIn("audit.jsonl", text)
            self.assertIn(str(spy.bin_dir), spy.path_prefix)
```

- [ ] **Step 2: Run failing test**

Run:

```bash
python -m unittest tests.e2e.test_harness_unit.HarnessUnitTests.test_tea_spy_writes_wrapper -v
```

Expected: FAIL because `tea_spy.py` does not exist.

- [ ] **Step 3: Implement tea spy generator**

Create `tests/e2e/suites/tea/tea_spy.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import stat


@dataclass(frozen=True)
class TeaSpy:
    bin_dir: Path
    audit_log: Path
    real_tea: Path

    @property
    def path_prefix(self) -> str:
        return str(self.bin_dir)


def create_tea_spy(root: Path, real_tea: Path, audit_log: Path) -> TeaSpy:
    bin_dir = root / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    audit_log.parent.mkdir(parents=True, exist_ok=True)
    wrapper = bin_dir / "tea"
    wrapper.write_text(
        f'''#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

real = {str(real_tea)!r}
audit = Path({str(audit_log)!r})
argv = sys.argv[1:]
proc = subprocess.run([real] + argv, text=False)
event = {{
    "source": "tea",
    "argv": argv,
    "cwd": os.getcwd(),
    "pid": os.getpid(),
    "phase": "finish",
    "exit_code": proc.returncode,
    "timestamp": datetime.now(timezone.utc).isoformat(),
}}
audit.parent.mkdir(parents=True, exist_ok=True)
with audit.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(event, sort_keys=True) + "\\n")
raise SystemExit(proc.returncode)
''',
        encoding="utf-8",
    )
    wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return TeaSpy(bin_dir=bin_dir, audit_log=audit_log, real_tea=real_tea)
```

- [ ] **Step 4: Run tests for Task 4**

Run:

```bash
python -m unittest tests.e2e.test_harness_unit -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 4**

```bash
git add tests/e2e
git commit -m "feat: add tea command spy generator"
```

---

### Task 5: Add agent adapter contract and Claude Code adapter

**Files:**
- Create: `tests/e2e/harness/agents/__init__.py`
- Create: `tests/e2e/harness/agents/base.py`
- Create: `tests/e2e/harness/agents/claude_code.py`
- Modify: `tests/e2e/test_harness_unit.py`

- [ ] **Step 1: Add failing adapter trace parser test**

Append this test to `HarnessUnitTests`:

```python
    def test_claude_trace_parser_extracts_skill_loaded_events(self):
        from tests.e2e.harness.agents.claude_code import parse_claude_stream_json

        lines = [
            json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Using create-issue to create the issue."}]}}),
            json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "create-issue"}}]}}),
        ]
        events = parse_claude_stream_json(lines)
        skills = [event.name for event in events if event.kind == "skill.loaded"]
        self.assertIn("create-issue", skills)
```

- [ ] **Step 2: Run failing parser test**

Run:

```bash
python -m unittest tests.e2e.test_harness_unit.HarnessUnitTests.test_claude_trace_parser_extracts_skill_loaded_events -v
```

Expected: FAIL because the adapter module does not exist.

- [ ] **Step 3: Create agent package marker**

Run:

```bash
mkdir -p tests/e2e/harness/agents
: > tests/e2e/harness/agents/__init__.py
```

- [ ] **Step 4: Implement base adapter protocol**

Create `tests/e2e/harness/agents/base.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from tests.e2e.harness.model import AgentRunResult


class AgentAdapter(Protocol):
    def run(
        self,
        prompt: str,
        workspace: Path,
        artifact_dir: Path,
        env: dict[str, str],
        timeout_seconds: int,
    ) -> AgentRunResult:
        ...
```

- [ ] **Step 5: Implement Claude Code adapter**

Create `tests/e2e/harness/agents/claude_code.py`:

```python
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Iterable

from tests.e2e.harness.model import AgentRunResult, TraceEvent

_SKILL_TEXT = re.compile(r"\bUsing\s+([A-Za-z0-9_-]+)\b")


def _extract_texts(obj: object) -> Iterable[str]:
    if isinstance(obj, dict):
        if obj.get("type") == "text" and isinstance(obj.get("text"), str):
            yield obj["text"]
        for value in obj.values():
            yield from _extract_texts(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _extract_texts(item)


def parse_claude_stream_json(lines: list[str]) -> list[TraceEvent]:
    events: list[TraceEvent] = []
    seen_skills: set[str] = set()
    for line in lines:
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue

        for text in _extract_texts(raw):
            events.append(TraceEvent(kind="agent.message", text=text, raw=raw))
            match = _SKILL_TEXT.search(text)
            if match and match.group(1) not in seen_skills:
                seen_skills.add(match.group(1))
                events.append(TraceEvent(kind="skill.loaded", name=match.group(1), raw=raw))

        for content in raw.get("message", {}).get("content", []) if isinstance(raw, dict) else []:
            if isinstance(content, dict) and content.get("type") == "tool_use":
                tool_name = str(content.get("name"))
                events.append(TraceEvent(kind="tool.call", tool=tool_name, raw=raw))
                tool_input = content.get("input", {})
                if tool_name.lower() == "skill" and isinstance(tool_input, dict):
                    skill = tool_input.get("skill") or tool_input.get("name")
                    if isinstance(skill, str) and skill not in seen_skills:
                        seen_skills.add(skill)
                        events.append(TraceEvent(kind="skill.loaded", name=skill, raw=raw))
    return events


class ClaudeCodeAdapter:
    def __init__(self, claude_bin: str = "claude", plugin_dir: Path | None = None):
        self.claude_bin = claude_bin
        self.plugin_dir = plugin_dir

    def run(
        self,
        prompt: str,
        workspace: Path,
        artifact_dir: Path,
        env: dict[str, str],
        timeout_seconds: int,
    ) -> AgentRunResult:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = artifact_dir / "agent.stdout.jsonl"
        stderr_path = artifact_dir / "agent.stderr.txt"
        command = [
            self.claude_bin,
            "--print",
            "--output-format",
            "stream-json",
            "--permission-mode",
            "bypassPermissions",
        ]
        if self.plugin_dir is not None:
            command.extend(["--plugin-dir", str(self.plugin_dir)])
        command.append(prompt)

        started = time.monotonic()
        merged_env = os.environ.copy()
        merged_env.update(env)
        try:
            completed = subprocess.run(
                command,
                cwd=workspace,
                env=merged_env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_seconds,
                check=False,
            )
            timed_out = False
            stdout = completed.stdout
            stderr = completed.stderr
            exit_code = completed.returncode
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            exit_code = 124

        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        lines = stdout.splitlines()
        return AgentRunResult(
            exit_code=exit_code,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            raw_trace_path=stdout_path,
            trace_events=parse_claude_stream_json(lines),
            duration_seconds=time.monotonic() - started,
            timed_out=timed_out,
        )
```

- [ ] **Step 6: Run tests for Task 5**

Run:

```bash
python -m unittest tests.e2e.test_harness_unit -v
```

Expected: PASS.

- [ ] **Step 7: Commit Task 5**

```bash
git add tests/e2e
git commit -m "feat: add claude code e2e adapter"
```

---

### Task 5b: Add Pi adapter and current-checkout skill-source isolation

**Why this task exists:** The harness must prove it is testing the skills from the current repository checkout, not a stale globally installed copy. Pi can enforce this strongly with `--no-skills --skill <repo-root>/skills`. Claude Code already accepts `--plugin-dir <repo-root>`; this task adds Pi support and tests the explicit current-checkout skill source invariant.

**Files:**
- Create: `tests/e2e/harness/agents/pi.py`
- Modify: `tests/e2e/test_harness_unit.py`

- [ ] **Step 1: Add failing Pi parser and command tests**

Append these tests to `HarnessUnitTests` in `tests/e2e/test_harness_unit.py`:

```python
    def test_pi_trace_parser_extracts_skill_loaded_from_current_skill_read(self):
        from tests.e2e.harness.agents.pi import parse_pi_json_events

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
        from tests.e2e.harness.agents.pi import parse_pi_json_events

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
        from tests.e2e.harness.agents.pi import PiAdapter

        captured: dict[str, list[str]] = {}

        def fake_run(command, **kwargs):
            captured["command"] = command
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills = root / "repo" / "skills"
            skills.mkdir(parents=True)
            with mock.patch("tests.e2e.harness.agents.pi.subprocess.run", side_effect=fake_run):
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
```

- [ ] **Step 2: Run the focused failing tests**

Run:

```bash
python -m unittest \
  tests.e2e.test_harness_unit.HarnessUnitTests.test_pi_trace_parser_extracts_skill_loaded_from_current_skill_read \
  tests.e2e.test_harness_unit.HarnessUnitTests.test_pi_trace_parser_ignores_skill_reads_outside_current_checkout \
  tests.e2e.test_harness_unit.HarnessUnitTests.test_pi_adapter_command_uses_only_current_repo_skills -v
```

Expected: FAIL because `tests/e2e/harness/agents/pi.py` does not exist.

- [ ] **Step 3: Implement the Pi adapter**

Create `tests/e2e/harness/agents/pi.py`:

```python
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from tests.e2e.harness.model import AgentRunResult, TraceEvent


def _decode_subprocess_output(output: str | bytes | None) -> str:
    if isinstance(output, str):
        return output
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return ""


def _content_texts(content: Any) -> list[str]:
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        texts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                texts.append(item["text"])
        return texts
    return []


def _skill_from_read_path(path: str, skills_dir: Path) -> str | None:
    try:
        relative = Path(path).resolve().relative_to(skills_dir.resolve())
    except ValueError:
        return None
    parts = relative.parts
    if len(parts) == 2 and parts[1] == "SKILL.md":
        return parts[0]
    return None


def parse_pi_json_events(lines: list[str], skills_dir: Path) -> list[TraceEvent]:
    events: list[TraceEvent] = []
    seen_skills: set[str] = set()
    for line in lines:
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue

        event_type = raw.get("type") if isinstance(raw, dict) else None
        if event_type == "tool_execution_start":
            tool_name = str(raw.get("toolName") or "")
            events.append(TraceEvent(kind="tool.call", tool=tool_name, raw=raw))
            args = raw.get("args", {})
            path = args.get("path") if isinstance(args, dict) else None
            if tool_name == "read" and isinstance(path, str):
                skill = _skill_from_read_path(path, skills_dir)
                if skill and skill not in seen_skills:
                    seen_skills.add(skill)
                    events.append(TraceEvent(kind="skill.loaded", name=skill, raw=raw))

        if event_type in {"message_start", "message_update", "message_end"}:
            message = raw.get("message", {})
            if isinstance(message, dict):
                for text in _content_texts(message.get("content")):
                    events.append(TraceEvent(kind="agent.message", text=text, raw=raw))
            assistant_event = raw.get("assistantMessageEvent")
            if isinstance(assistant_event, dict) and isinstance(assistant_event.get("delta"), str):
                events.append(TraceEvent(kind="agent.message", text=assistant_event["delta"], raw=raw))
    return events


class PiAdapter:
    def __init__(self, pi_bin: str = "pi", skills_dir: Path | None = None):
        self.pi_bin = pi_bin
        self.skills_dir = skills_dir

    def run(
        self,
        prompt: str,
        workspace: Path,
        artifact_dir: Path,
        env: dict[str, str],
        timeout_seconds: int,
    ) -> AgentRunResult:
        if self.skills_dir is None:
            raise ValueError("PiAdapter requires skills_dir so tests use the current checkout's skills")

        artifact_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = artifact_dir / "agent.stdout.jsonl"
        stderr_path = artifact_dir / "agent.stderr.txt"
        command = [
            self.pi_bin,
            "--print",
            "--mode",
            "json",
            "--no-session",
            "--no-skills",
            "--skill",
            str(self.skills_dir),
            prompt,
        ]

        started = time.monotonic()
        merged_env = os.environ.copy()
        merged_env.update(env)
        try:
            completed = subprocess.run(
                command,
                cwd=workspace,
                env=merged_env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_seconds,
                check=False,
            )
            timed_out = False
            stdout = _decode_subprocess_output(completed.stdout)
            stderr = _decode_subprocess_output(completed.stderr)
            exit_code = completed.returncode
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout = _decode_subprocess_output(exc.stdout)
            stderr = _decode_subprocess_output(exc.stderr)
            exit_code = 124

        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        return AgentRunResult(
            exit_code=exit_code,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            raw_trace_path=stdout_path,
            trace_events=parse_pi_json_events(stdout.splitlines(), self.skills_dir),
            duration_seconds=time.monotonic() - started,
            timed_out=timed_out,
        )
```

- [ ] **Step 4: Run Task 5b tests**

Run:

```bash
python -m unittest tests.e2e.test_harness_unit -v
```

Expected: PASS.

- [ ] **Step 5: Run full non-live test suite**

Run:

```bash
python -m unittest discover -s tests -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 5b**

```bash
git add tests/e2e/harness/agents/pi.py tests/e2e/test_harness_unit.py
git commit -m "feat: add pi e2e adapter"
```

---

### Task 6: Add Forgejo provisioner and issue verifier

**Files:**
- Create: `tests/e2e/suites/tea/provision.py`
- Create: `tests/e2e/suites/tea/verify_forgejo.py`
- Modify: `tests/e2e/test_harness_unit.py`

- [ ] **Step 1: Add unit tests for safety guard and issue assertion**

Append these tests to `HarnessUnitTests`:

```python
    def test_cleanup_guard_accepts_only_current_run_resources(self):
        from tests.e2e.suites.tea.provision import assert_safe_e2e_resource

        assert_safe_e2e_resource("tea-e2e-abc123", "abc123")
        with self.assertRaisesRegex(ValueError, "refusing"):
            assert_safe_e2e_resource("production", "abc123")

    def test_issue_verifier_matches_title_and_body_file(self):
        from tests.e2e.harness.model import RunContext
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
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
python -m unittest tests.e2e.test_harness_unit.HarnessUnitTests.test_cleanup_guard_accepts_only_current_run_resources \
  tests.e2e.test_harness_unit.HarnessUnitTests.test_issue_verifier_matches_title_and_body_file -v
```

Expected: FAIL because modules do not exist.

- [ ] **Step 3: Implement provisioning helpers**

Create `tests/e2e/suites/tea/provision.py`:

```python
from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import parse, request

from actions.internal.tea_api import TeaConfig, read_tea_config


@dataclass
class ForgejoRun:
    run_id: str
    org: str
    repo: str
    clone_url: str
    workspace: Path
    artifact_dir: Path
    config: TeaConfig


def new_run_id() -> str:
    return str(int(time.time()))


def assert_safe_e2e_resource(name: str, run_id: str) -> None:
    if not name.startswith("tea-e2e-") or run_id not in name:
        raise ValueError(f"refusing to delete non-e2e resource: {name}")


def api_request(config: TeaConfig, method: str, endpoint: str, body: bytes | None = None) -> Any:
    import json

    url = f"{config.base_url.rstrip('/')}/api/v1/{endpoint.lstrip('/')}"
    headers = {"Authorization": f"token {config.token}", "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=body, headers=headers, method=method)
    with request.urlopen(req) as response:
        raw = response.read()
    if not raw:
        return None
    return json.loads(raw.decode("utf-8"))


def create_org_and_repo(root: Path, run_id: str) -> ForgejoRun:
    import json

    config = read_tea_config()
    org = f"tea-e2e-{run_id}"
    repo = "repo"
    artifact_dir = root / "artifacts"
    workspace = root / "workspace" / repo
    artifact_dir.mkdir(parents=True, exist_ok=True)

    api_request(config, "POST", "orgs", json.dumps({"username": org, "full_name": org}).encode("utf-8"))
    created = api_request(config, "POST", f"orgs/{parse.quote(org, safe='')}/repos", json.dumps({"name": repo, "auto_init": True}).encode("utf-8"))
    clone_url = created.get("clone_url") or created.get("ssh_url")
    if not clone_url:
        raise RuntimeError("created repository did not include a clone_url or ssh_url")
    workspace.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", clone_url, str(workspace)], check=True)
    (workspace / "AGENTS.md").write_text("# Repository context\n\nThis repository is hosted on Forgejo.\n", encoding="utf-8")
    subprocess.run(["git", "add", "AGENTS.md"], cwd=workspace, check=True)
    subprocess.run(["git", "commit", "-m", "test: add agent context"], cwd=workspace, check=True)
    subprocess.run(["git", "push", "origin", "HEAD"], cwd=workspace, check=True)
    return ForgejoRun(run_id, org, repo, clone_url, workspace, artifact_dir, config)


def cleanup_run(run: ForgejoRun, keep_remote: bool = False) -> None:
    if run.workspace.exists():
        shutil.rmtree(run.workspace.parent, ignore_errors=True)
    if keep_remote:
        return
    assert_safe_e2e_resource(run.org, run.run_id)
    try:
        api_request(run.config, "DELETE", f"repos/{parse.quote(run.org, safe='')}/{parse.quote(run.repo, safe='')}")
    finally:
        api_request(run.config, "DELETE", f"orgs/{parse.quote(run.org, safe='')}")
```

- [ ] **Step 4: Implement first Forgejo verifier**

Create `tests/e2e/suites/tea/verify_forgejo.py`:

```python
from __future__ import annotations

from typing import Any
from urllib import parse

from tests.e2e.harness.model import RunContext
from tests.e2e.suites.tea.provision import api_request
from actions.internal.tea_api import TeaConfig


def list_issues(config: TeaConfig, org: str, repo: str) -> list[dict[str, Any]]:
    result = api_request(config, "GET", f"repos/{parse.quote(org, safe='')}/{parse.quote(repo, safe='')}/issues?state=all")
    return result if isinstance(result, list) else []


def verify_issue_expectation(expectation: dict[str, Any], ctx: RunContext, issues: list[dict[str, Any]]) -> dict[str, Any]:
    match = expectation.get("match", {})
    assertions = expectation.get("assert", {})
    candidates = issues
    if "title" in match:
        candidates = [issue for issue in candidates if issue.get("title") == match["title"]]

    expected_count = assertions.get("count")
    if expected_count is not None and len(candidates) != int(expected_count):
        return {"passed": False, "message": f"expected {expected_count} issue(s), found {len(candidates)}"}
    if not candidates:
        return {"passed": False, "message": "no matching issue found"}

    issue = candidates[0]
    if "state" in assertions and issue.get("state") != assertions["state"]:
        return {"passed": False, "message": f"expected state {assertions['state']}, found {issue.get('state')}"}
    if "body_equals_file" in assertions:
        expected_body = (ctx.workspace / assertions["body_equals_file"]).read_text(encoding="utf-8")
        if issue.get("body", "").strip() != expected_body.strip():
            return {"passed": False, "message": "issue body did not match file"}
    if expectation.get("id"):
        ctx.state[expectation["id"]] = issue
    return {"passed": True, "message": ""}


def verify_state(expectations: list[dict[str, Any]], ctx: RunContext, config: TeaConfig) -> list[dict[str, Any]]:
    issues_cache: list[dict[str, Any]] | None = None
    results: list[dict[str, Any]] = []
    for expectation in expectations:
        kind = expectation["kind"]
        if kind == "forgejo.issue":
            if issues_cache is None:
                issues_cache = list_issues(config, ctx.org, ctx.repo)
            results.append(verify_issue_expectation(expectation, ctx, issues_cache))
        else:
            results.append({"passed": False, "message": f"unsupported state verifier: {kind}"})
    return results
```

- [ ] **Step 5: Run tests for Task 6**

Run:

```bash
python -m unittest tests.e2e.test_harness_unit -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 6**

```bash
git add tests/e2e
git commit -m "feat: add forgejo e2e provisioning helpers"
```

---

### Task 7: Add scenario runner and opt-in live test host

**Files:**
- Create: `tests/e2e/harness/runner.py`
- Create: `tests/e2e/suites/tea/defaults.json`
- Create: `tests/e2e/suites/tea/scenarios/issues.json`
- Create: `tests/e2e/test_agent_e2e.py`
- Modify: `tests/e2e/test_harness_unit.py`

- [ ] **Step 1: Add failing runner unit test with fake adapter and fake verifier**

Append this test to `HarnessUnitTests`:

```python
    def test_runner_fails_when_expected_skill_is_missing(self):
        from tests.e2e.harness.model import AgentRunResult, Scenario
        from tests.e2e.harness.runner import ScenarioRunner

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
```

- [ ] **Step 2: Run failing runner test**

Run:

```bash
python -m unittest tests.e2e.test_harness_unit.HarnessUnitTests.test_runner_fails_when_expected_skill_is_missing -v
```

Expected: FAIL because `runner.py` does not exist.

- [ ] **Step 3: Implement scenario runner**

Create `tests/e2e/harness/runner.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .audit import AuditAssertionError, assert_audit, load_audit_events
from .model import AuditEvent, RunContext, Scenario, ScenarioResult
from .template import render_template


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
                if not any(event.kind == "skill.loaded" and event.name == name for event in trace_events):
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
            return ScenarioResult(scenario.name, False, "agent_nonzero_exit", f"agent exit code {agent_result.exit_code}", agent_result.trace_events, [])

        trace_error = self._assert_trace(scenario, agent_result.trace_events)
        if trace_error:
            return ScenarioResult(scenario.name, False, "expected_skill_not_loaded", trace_error, agent_result.trace_events, [])

        audit_events = load_audit_events(audit_log, self.audit_normalizer)
        state_results = self.state_verifier(scenario.expect_state, ctx)
        failed_state = [result for result in state_results if not result.get("passed")]
        if failed_state:
            return ScenarioResult(scenario.name, False, "state_mismatch", failed_state[0].get("message", "state mismatch"), agent_result.trace_events, audit_events)

        try:
            assert_audit(audit_events, scenario.expect_audit)
        except AuditAssertionError as exc:
            return ScenarioResult(scenario.name, False, "missing_audited_mutation", str(exc), agent_result.trace_events, audit_events)

        return ScenarioResult(scenario.name, True, trace_events=agent_result.trace_events, audit_events=audit_events)
```

- [ ] **Step 4: Add default budget file**

Create `tests/e2e/suites/tea/defaults.json`:

```json
{
  "execution": {
    "timeout_seconds": 300,
    "max_turns": 1
  },
  "expect_audit": {
    "budgets": {
      "total_commands": {"max": 20},
      "total_mutations": {"max": 4},
      "per_root": {
        "tea.issues.list": {"max": 5},
        "tea.issues.show": {"max": 5},
        "tea.labels.list": {"max": 5}
      }
    }
  }
}
```

- [ ] **Step 5: Add first live scenario file**

Create directory `tests/e2e/suites/tea/scenarios/` and file `tests/e2e/suites/tea/scenarios/issues.json`:

```json
{
  "scenarios": [
    {
      "name": "create issue from body file",
      "tags": ["skill:create-issue", "domain:issues", "smoke"],
      "fixtures": {
        "files": {
          "issue-body.md": "E2E body marker: {{ run.id }}\n"
        }
      },
      "prompt": "Create a Forgejo issue titled \"E2E {{ run.id }} create issue\". Use issue-body.md as the body.",
      "expect_trace": {
        "events": [
          {"kind": "skill.loaded", "name": "create-issue"}
        ]
      },
      "expect_state": [
        {
          "kind": "forgejo.issue",
          "id": "main_issue",
          "match": {"title": "E2E {{ run.id }} create issue"},
          "assert": {"count": 1, "state": "open", "body_equals_file": "issue-body.md"}
        }
      ],
      "expect_audit": {
        "events": [
          {"root": "tea.issues.create", "min": 1, "max": 1}
        ],
        "budgets": {
          "total_commands": {"max": 12},
          "total_mutations": {"max": 2},
          "per_root": {
            "tea.issues.create": {"min": 1, "max": 1},
            "tea.issues.list": {"max": 3},
            "tea.issues.show": {"max": 3},
            "tea.labels.list": {"max": 3}
          }
        }
      }
    }
  ]
}
```

- [ ] **Step 6: Add opt-in live E2E test host**

Create `tests/e2e/test_agent_e2e.py`:

```python
import os
import shutil
import tempfile
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


@unittest.skipUnless(os.environ.get("TEA_SKILLS_E2E") == "1", "set TEA_SKILLS_E2E=1 to run live agent E2E tests")
class TeaSkillsAgentE2ETests(unittest.TestCase):
    def test_create_issue_scenario(self):
        real_tea = shutil.which("tea")
        self.assertIsNotNone(real_tea, "tea must be installed")
        with tempfile.TemporaryDirectory(prefix="tea-skills-e2e-") as tmp:
            root = Path(tmp)
            run = create_org_and_repo(root, new_run_id())
            try:
                scenario_path = ROOT / "tests/e2e/suites/tea/scenarios/issues.json"
                defaults_path = ROOT / "tests/e2e/suites/tea/defaults.json"
                scenario = load_scenarios(scenario_path, defaults_path)[0]
                ctx = RunContext(run.run_id, run.org, run.repo, run.workspace, run.artifact_dir)
                spy = create_tea_spy(root / "spy", Path(real_tea), run.artifact_dir / "tea-audit.jsonl")
                adapter = ClaudeCodeAdapter(plugin_dir=ROOT)

                def verifier(expectations, context):
                    return verify_state(expectations, context, run.config)

                runner = ScenarioRunner(adapter, normalize_raw_audit_event, verifier)
                env = {"PATH": f"{spy.path_prefix}{os.pathsep}{os.environ.get('PATH', '')}"}
                result = runner.run(scenario, ctx, env)
                self.assertTrue(result.passed, f"{result.failure_class}: {result.message}")
            finally:
                cleanup_run(run, keep_remote=os.environ.get("TEA_SKILLS_E2E_KEEP_REMOTE") == "1")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 7: Run focused runner tests**

Run:

```bash
python -m unittest tests.e2e.test_harness_unit -v
```

Expected: PASS.

- [ ] **Step 8: Run full non-live test suite**

Run:

```bash
python -m unittest discover -s tests -v
```

Expected: PASS, with `TeaSkillsAgentE2ETests` skipped unless `TEA_SKILLS_E2E=1`.

- [ ] **Step 9: Commit Task 7**

```bash
git add tests/e2e
git commit -m "feat: add opt-in agent e2e runner"
```

---

### Task 8: Document how to run the live harness

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-05-14-agent-e2e-harness-augmentation-design.md`

- [ ] **Step 1: Add README section**

Add this section to `README.md` after prerequisites:

~~~markdown
## Opt-in live agent E2E tests

The repository includes an opt-in harness that runs a real agent against a real Forgejo server using disposable `tea-e2e-*` organizations and repositories.

Requirements:

- `tea` is installed and already logged in to a Forgejo/Gitea server.
- The logged-in account can create and delete organizations and repositories.
- Claude Code is installed and authenticated.

Run the non-live tests:

```bash
python -m unittest discover -s tests -v
```

Run the live create-issue agent E2E scenario:

```bash
TEA_SKILLS_E2E=1 python -m unittest tests.e2e.test_agent_e2e -v
```

Preserve the disposable remote resources for debugging:

```bash
TEA_SKILLS_E2E=1 TEA_SKILLS_E2E_KEEP_REMOTE=1 python -m unittest tests.e2e.test_agent_e2e -v
```

The harness records agent traces, `tea` calls, bundled action calls, and Forgejo state snapshots under the run artifact directory. Scenario prompts do not mention skills, `tea`, bundled actions, or forbidden alternatives; skill discovery is part of what the test verifies.
~~~

- [ ] **Step 2: Add implementation note to the augmentation spec**

Append this short section to `docs/superpowers/specs/2026-05-14-agent-e2e-harness-augmentation-design.md`:

```markdown
## Implemented vertical slice

The first implementation pass builds a single live create-issue scenario to prove the full harness contract. It intentionally uses stdlib `unittest` as the dependency-free host while remaining pytest-collectable. Full representative scenarios for every skill should be added in a follow-up plan once the vertical slice is stable against the target Forgejo server and selected agent adapter.
```

- [ ] **Step 3: Run full non-live test suite**

Run:

```bash
python -m unittest discover -s tests -v
```

Expected: PASS.

- [ ] **Step 4: Commit Task 8**

```bash
git add README.md docs/superpowers/specs/2026-05-14-agent-e2e-harness-augmentation-design.md
git commit -m "docs: document agent e2e harness"
```

---

### Task 9: Optional live verification checkpoint

**Files:**
- No code changes expected.

- [ ] **Step 1: Confirm live prerequisites**

Run:

```bash
command -v tea
command -v claude
tea logins
```

Expected: `tea` and `claude` paths print, and `tea logins` shows at least one configured login.

- [ ] **Step 2: Run the live scenario only when prerequisites are available**

Run:

```bash
TEA_SKILLS_E2E=1 python -m unittest tests.e2e.test_agent_e2e -v
```

Expected: PASS, or a clear failure class such as `expected_skill_not_loaded`, `missing_audited_mutation`, `state_mismatch`, or `agent_timeout` with artifacts preserved.

- [ ] **Step 3: If live verification passes, commit no-op status is clean**

Run:

```bash
git status --short
```

Expected: no uncommitted files except optional preserved artifacts ignored or outside the repo.

---

## Final verification

Run:

```bash
python -m unittest discover -s tests -v
```

Expected: all non-live tests pass and live E2E tests are skipped unless `TEA_SKILLS_E2E=1`.

If live prerequisites are available, also run:

```bash
TEA_SKILLS_E2E=1 python -m unittest tests.e2e.test_agent_e2e -v
```

Expected: the create-issue scenario passes against a disposable Forgejo org/repo and cleanup succeeds.

## Follow-up plan required after this one

After this vertical slice is stable, write a second plan to add representative scenarios for every current skill. That plan should reuse the harness built here and focus on Forgejo fixture setup, state verifiers, dependency ordering, and scenario budgets for issues, pull requests, milestones, labels, org labels, and API-gap actions.
