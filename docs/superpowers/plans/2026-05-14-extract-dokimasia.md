# Dokimasia Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the generic agent E2E harness into a separate Python package named `dokimasia` with CLI `doki`, while keeping `tea-skills` as a suite consumer.

**Architecture:** Create a sibling package repository/directory for `dokimasia`, move generic harness modules into it, and leave only Forgejo/tea-specific suite code in `tea-skills`. `tea-skills` imports `dokimasia` as an editable test dependency and keeps the current create-issue vertical slice passing.

**Tech Stack:** Python 3.14-compatible stdlib, PyYAML for YAML scenarios, unittest for the current host, optional future CLI entry point `doki`.

---

## File map

### New sibling package

Create outside this repo worktree:

```text
/Users/sh/Projects/dokimasia/
  pyproject.toml
  README.md
  src/dokimasia/
    __init__.py
    agents/
      __init__.py
      base.py
      claude_code.py
      pi.py
    audit/
      __init__.py
      assertions.py
      model.py
    core/
      __init__.py
      model.py
      runner.py
      scenarios.py
      template.py
  tests/
    __init__.py
    test_core.py
```

### `tea-skills` changes

```text
/Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness/
  tests/e2e/
    test_agent_e2e.py                    # imports dokimasia
    tea_suite/                            # renamed from suites/tea
      __init__.py
      normalize.py
      provision.py
      tea_spy.py
      verify_forgejo.py
      defaults.yaml
      scenarios/issues.yaml
    suites/                               # remove after import migration
    harness/                              # remove after import migration
  tests/test_dokimasia_integration.py     # optional import smoke, or fold into existing tests
  README.md
```

Keep current commits intact. Do not rewrite history.

---

### Task 1: Create `dokimasia` package skeleton

**Files:**
- Create: `/Users/sh/Projects/dokimasia/pyproject.toml`
- Create: `/Users/sh/Projects/dokimasia/README.md`
- Create: `/Users/sh/Projects/dokimasia/src/dokimasia/__init__.py`
- Create: `/Users/sh/Projects/dokimasia/src/dokimasia/agents/__init__.py`
- Create: `/Users/sh/Projects/dokimasia/src/dokimasia/audit/__init__.py`
- Create: `/Users/sh/Projects/dokimasia/src/dokimasia/core/__init__.py`
- Create: `/Users/sh/Projects/dokimasia/tests/__init__.py`

- [ ] **Step 1: Create package directories**

Run:

```bash
mkdir -p /Users/sh/Projects/dokimasia/src/dokimasia/{agents,audit,core} /Users/sh/Projects/dokimasia/tests
```

- [ ] **Step 2: Add `pyproject.toml`**

Create `/Users/sh/Projects/dokimasia/pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "dokimasia"
version = "0.1.0"
description = "Generic agent end-to-end evaluation harness"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "PyYAML>=6.0",
]

[project.scripts]
doki = "dokimasia.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
```

- [ ] **Step 3: Add package README**

Create `/Users/sh/Projects/dokimasia/README.md`:

```markdown
# Dokimasia

Dokimasia is a generic agent end-to-end harness. It runs single-turn agent scenarios, preserves artifacts, normalizes traces, and asserts that expected trace/audit/state evidence exists.

The package is intentionally domain-neutral. It does not know about any specific product, CLI, issue tracker, or skill repository. Projects provide provisioning, audit normalization, and state verification.

CLI name: `doki`.
```

- [ ] **Step 4: Add package markers**

Run:

```bash
: > /Users/sh/Projects/dokimasia/src/dokimasia/__init__.py
: > /Users/sh/Projects/dokimasia/src/dokimasia/agents/__init__.py
: > /Users/sh/Projects/dokimasia/src/dokimasia/audit/__init__.py
: > /Users/sh/Projects/dokimasia/src/dokimasia/core/__init__.py
: > /Users/sh/Projects/dokimasia/tests/__init__.py
```

- [ ] **Step 5: Commit package skeleton**

Run:

```bash
cd /Users/sh/Projects/dokimasia
git init
git add .
git commit -m "chore: create dokimasia package skeleton"
```

Expected: commit succeeds.

---

### Task 2: Move generic models, template, audit, and runner into `dokimasia`

**Files:**
- Create: `/Users/sh/Projects/dokimasia/src/dokimasia/core/model.py`
- Create: `/Users/sh/Projects/dokimasia/src/dokimasia/core/template.py`
- Create: `/Users/sh/Projects/dokimasia/src/dokimasia/audit/assertions.py`
- Create: `/Users/sh/Projects/dokimasia/src/dokimasia/audit/model.py`
- Create: `/Users/sh/Projects/dokimasia/src/dokimasia/core/runner.py`
- Create: `/Users/sh/Projects/dokimasia/tests/test_core.py`

- [ ] **Step 1: Copy current generic code into package**

Copy these files from `tea-skills` into `dokimasia` and adjust imports:

```bash
cp /Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness/tests/e2e/harness/model.py /Users/sh/Projects/dokimasia/src/dokimasia/core/model.py
cp /Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness/tests/e2e/harness/template.py /Users/sh/Projects/dokimasia/src/dokimasia/core/template.py
cp /Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness/tests/e2e/harness/audit.py /Users/sh/Projects/dokimasia/src/dokimasia/audit/assertions.py
cp /Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness/tests/e2e/harness/runner.py /Users/sh/Projects/dokimasia/src/dokimasia/core/runner.py
```

- [ ] **Step 2: Add audit model re-export**

Create `/Users/sh/Projects/dokimasia/src/dokimasia/audit/model.py`:

```python
from __future__ import annotations

from dokimasia.core.model import AuditEvent

__all__ = ["AuditEvent"]
```

- [ ] **Step 3: Fix imports in `audit/assertions.py`**

In `/Users/sh/Projects/dokimasia/src/dokimasia/audit/assertions.py`, replace:

```python
from .model import AuditEvent
```

with:

```python
from dokimasia.core.model import AuditEvent
```

- [ ] **Step 4: Fix imports in `core/runner.py`**

In `/Users/sh/Projects/dokimasia/src/dokimasia/core/runner.py`, replace:

```python
from .audit import AuditAssertionError, assert_audit, load_audit_events
from .model import AuditEvent, RunContext, Scenario, ScenarioResult
from .template import render_template
```

with:

```python
from dokimasia.audit.assertions import AuditAssertionError, assert_audit, load_audit_events
from dokimasia.core.model import AuditEvent, RunContext, Scenario, ScenarioResult
from dokimasia.core.template import render_template
```

- [ ] **Step 5: Add focused package tests**

Create `/Users/sh/Projects/dokimasia/tests/test_core.py`:

```python
import json
import tempfile
import unittest
from pathlib import Path

from dokimasia.core.model import AgentRunResult, AuditEvent, RunContext, Scenario, TraceEvent
from dokimasia.core.runner import ScenarioRunner
from dokimasia.core.template import render_template
from dokimasia.audit.assertions import AuditAssertionError, assert_audit


class DokimasiaCoreTests(unittest.TestCase):
    def test_render_template_replaces_dotted_values(self):
        self.assertEqual(
            render_template("{{ issue.title }} / {{ run.id }}", {"issue": {"title": "Hello"}, "run": {"id": "abc"}}),
            "Hello / abc",
        )

    def test_audit_expectations_ignore_failed_required_events(self):
        events = [AuditEvent("cli.create", [], "/repo", 1, True, "cli")]
        with self.assertRaisesRegex(AuditAssertionError, "cli.create"):
            assert_audit(events, {"events": [{"root": "cli.create", "min": 1}]})

    def test_runner_accepts_plugin_qualified_skill_names(self):
        class FakeAdapter:
            def run(self, prompt, workspace, artifact_dir, env, timeout_seconds):
                stdout = artifact_dir / "stdout.txt"
                stderr = artifact_dir / "stderr.txt"
                stdout.write_text("", encoding="utf-8")
                stderr.write_text("", encoding="utf-8")
                return AgentRunResult(0, stdout, stderr, None, [TraceEvent(kind="skill.loaded", name="tea:create-issue")], 0.01, False)

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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 6: Run package tests**

Run:

```bash
cd /Users/sh/Projects/dokimasia
python -m pip install -e .
python -m unittest discover -s tests -v
```

Expected: PASS.

- [ ] **Step 7: Commit generic core move**

Run:

```bash
cd /Users/sh/Projects/dokimasia
git add .
git commit -m "feat: add generic scenario runner core"
```

---

### Task 3: Add generic agent adapters to `dokimasia`

**Files:**
- Create: `/Users/sh/Projects/dokimasia/src/dokimasia/agents/base.py`
- Create: `/Users/sh/Projects/dokimasia/src/dokimasia/agents/claude_code.py`
- Create: `/Users/sh/Projects/dokimasia/src/dokimasia/agents/pi.py`
- Modify: `/Users/sh/Projects/dokimasia/tests/test_core.py`

- [ ] **Step 1: Copy adapter files**

Run:

```bash
cp /Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness/tests/e2e/harness/agents/base.py /Users/sh/Projects/dokimasia/src/dokimasia/agents/base.py
cp /Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness/tests/e2e/harness/agents/claude_code.py /Users/sh/Projects/dokimasia/src/dokimasia/agents/claude_code.py
cp /Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness/tests/e2e/harness/agents/pi.py /Users/sh/Projects/dokimasia/src/dokimasia/agents/pi.py
```

- [ ] **Step 2: Fix adapter imports**

In all three adapter files under `/Users/sh/Projects/dokimasia/src/dokimasia/agents/`, replace imports from `tests.e2e.harness.model` with:

```python
from dokimasia.core.model import AgentRunResult, TraceEvent
```

For `base.py`, use:

```python
from dokimasia.core.model import AgentRunResult
```

- [ ] **Step 3: Add adapter parser tests**

Append to `/Users/sh/Projects/dokimasia/tests/test_core.py`:

```python
class DokimasiaAgentAdapterTests(unittest.TestCase):
    def test_claude_parser_extracts_plugin_qualified_skill_loaded(self):
        from dokimasia.agents.claude_code import parse_claude_stream_json

        events = parse_claude_stream_json([
            json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "tea:create-issue"}}]}}),
        ])
        self.assertIn("tea:create-issue", [event.name for event in events if event.kind == "skill.loaded"])

    def test_pi_parser_extracts_skill_loaded_from_current_skill_read(self):
        from dokimasia.agents.pi import parse_pi_json_events

        events = parse_pi_json_events([
            json.dumps({"type": "tool_execution_start", "toolName": "read", "args": {"path": "/repo/skills/create-issue/SKILL.md"}}),
        ], skills_dir=Path("/repo/skills"))
        self.assertEqual([event.name for event in events if event.kind == "skill.loaded"], ["create-issue"])
```

- [ ] **Step 4: Run package tests**

Run:

```bash
cd /Users/sh/Projects/dokimasia
python -m unittest discover -s tests -v
```

Expected: PASS.

- [ ] **Step 5: Commit adapters**

Run:

```bash
cd /Users/sh/Projects/dokimasia
git add .
git commit -m "feat: add claude and pi adapters"
```

---

### Task 4: Add YAML scenario loading to `dokimasia`

**Files:**
- Create: `/Users/sh/Projects/dokimasia/src/dokimasia/core/scenarios.py`
- Modify: `/Users/sh/Projects/dokimasia/tests/test_core.py`

- [ ] **Step 1: Copy scenario loader and add YAML support**

Create `/Users/sh/Projects/dokimasia/src/dokimasia/core/scenarios.py`:

```python
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import yaml

from dokimasia.core.model import Scenario


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_document(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".json":
        loaded = json.loads(text)
    elif suffix in {".yaml", ".yml"}:
        loaded = yaml.safe_load(text)
    else:
        raise ValueError(f"unsupported scenario file extension: {path.suffix}")
    return loaded if isinstance(loaded, dict) else {}


def load_scenarios(path: Path, defaults_path: Path | None = None) -> list[Scenario]:
    defaults = load_document(defaults_path) if defaults_path else {}
    document = load_document(path)
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

- [ ] **Step 2: Add YAML loader tests**

Append to `/Users/sh/Projects/dokimasia/tests/test_core.py`:

```python
class DokimasiaScenarioLoaderTests(unittest.TestCase):
    def test_load_yaml_scenarios_merges_defaults(self):
        from dokimasia.core.scenarios import load_scenarios

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            defaults = root / "defaults.yaml"
            scenarios = root / "scenarios.yaml"
            defaults.write_text("""
execution:
  timeout_seconds: 10
expect_audit:
  budgets:
    total_commands:
      max: 5
""", encoding="utf-8")
            scenarios.write_text("""
scenarios:
  - name: one
    prompt: Run {{ run.id }}
    expect_trace:
      events: []
""", encoding="utf-8")
            loaded = load_scenarios(scenarios, defaults)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].execution["timeout_seconds"], 10)
        self.assertEqual(loaded[0].expect_audit["budgets"]["total_commands"], {"max": 5})
```

- [ ] **Step 3: Run package tests**

Run:

```bash
cd /Users/sh/Projects/dokimasia
python -m unittest discover -s tests -v
```

Expected: PASS.

- [ ] **Step 4: Commit YAML scenario loader**

Run:

```bash
cd /Users/sh/Projects/dokimasia
git add .
git commit -m "feat: load yaml scenarios"
```

---

### Task 5: Wire `tea-skills` to consume editable `dokimasia`

**Files:**
- Modify: `/Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness/tests/e2e/test_agent_e2e.py`
- Modify: `/Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness/tests/e2e/test_harness_unit.py`

- [ ] **Step 1: Install editable package in the active Python environment**

Run:

```bash
cd /Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness
python -m pip install -e /Users/sh/Projects/dokimasia
```

Expected: pip reports `Successfully installed dokimasia` or an editable install.

- [ ] **Step 2: Update imports in `test_agent_e2e.py`**

Replace imports from `tests.e2e.harness` with imports from `dokimasia`:

```python
from dokimasia.agents.claude_code import ClaudeCodeAdapter
from dokimasia.agents.pi import PiAdapter
from dokimasia.core.model import RunContext
from dokimasia.core.runner import ScenarioRunner
from dokimasia.core.scenarios import load_scenarios
```

Add adapter selector:

```python
def make_agent_adapter():
    agent = os.environ.get("TEA_SKILLS_E2E_AGENT", "claude").lower()
    if agent == "claude":
        return ClaudeCodeAdapter(plugin_dir=ROOT)
    if agent == "pi":
        return PiAdapter(skills_dir=ROOT / "skills")
    raise ValueError(f"unknown TEA_SKILLS_E2E_AGENT: {agent}")
```

Replace:

```python
adapter = ClaudeCodeAdapter(plugin_dir=ROOT)
```

with:

```python
adapter = make_agent_adapter()
```

- [ ] **Step 3: Update `test_harness_unit.py` imports**

For tests that exercise generic harness behavior, replace imports from `tests.e2e.harness` with `dokimasia`:

```python
from dokimasia.core.model import RunContext
from dokimasia.core.scenarios import load_scenarios
from dokimasia.core.template import render_template
```

Inside tests, replace:

```python
from tests.e2e.harness.model import ...
from tests.e2e.harness.runner import ScenarioRunner
from tests.e2e.harness.audit import ...
from tests.e2e.harness.agents.claude_code import ...
from tests.e2e.harness.agents.pi import ...
```

with:

```python
from dokimasia.core.model import ...
from dokimasia.core.runner import ScenarioRunner
from dokimasia.audit.assertions import ...
from dokimasia.agents.claude_code import ...
from dokimasia.agents.pi import ...
```

Also update mock patch paths for adapter tests from `tests.e2e.harness.agents...` to `dokimasia.agents...`.

- [ ] **Step 4: Run non-live `tea-skills` tests**

Run:

```bash
cd /Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness
python -m unittest discover -s tests -v
```

Expected: PASS with live E2E skipped.

- [ ] **Step 5: Commit `tea-skills` import migration**

Run:

```bash
cd /Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness
git add tests/e2e/test_agent_e2e.py tests/e2e/test_harness_unit.py
git commit -m "test: consume dokimasia harness package"
```

---

### Task 6: Move `tea-skills` scenario files to YAML and suite directory

**Files:**
- Create: `/Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness/tests/e2e/tea_suite/defaults.yaml`
- Create: `/Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness/tests/e2e/tea_suite/scenarios/issues.yaml`
- Move: `/Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness/tests/e2e/suites/tea/*.py` to `/Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness/tests/e2e/tea_suite/*.py`
- Remove: old JSON scenario/default files after tests pass
- Modify: `/Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness/tests/e2e/test_agent_e2e.py`
- Modify: `/Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness/tests/e2e/test_harness_unit.py`

- [ ] **Step 1: Create suite directory and move Python suite files**

Run:

```bash
cd /Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness
mkdir -p tests/e2e/tea_suite/scenarios
mv tests/e2e/suites/tea/normalize.py tests/e2e/tea_suite/normalize.py
mv tests/e2e/suites/tea/provision.py tests/e2e/tea_suite/provision.py
mv tests/e2e/suites/tea/tea_spy.py tests/e2e/tea_suite/tea_spy.py
mv tests/e2e/suites/tea/verify_forgejo.py tests/e2e/tea_suite/verify_forgejo.py
: > tests/e2e/tea_suite/__init__.py
```

- [ ] **Step 2: Convert defaults JSON to YAML**

Create `tests/e2e/tea_suite/defaults.yaml`:

```yaml
execution:
  timeout_seconds: 300
  max_turns: 1
expect_audit:
  budgets:
    total_commands:
      max: 20
    total_mutations:
      max: 4
    per_root:
      tea.issues.list:
        max: 5
      tea.issues.show:
        max: 5
      tea.labels.list:
        max: 5
```

- [ ] **Step 3: Convert issue scenario JSON to YAML**

Create `tests/e2e/tea_suite/scenarios/issues.yaml`:

```yaml
scenarios:
  - name: create issue from body file
    tags:
      - skill:create-issue
      - domain:issues
      - smoke
    fixtures:
      files:
        issue-body.md: |
          E2E body marker: {{ run.id }}
    prompt: >-
      Create a Forgejo issue titled "E2E {{ run.id }} create issue".
      Use issue-body.md as the body.
    expect_trace:
      events:
        - kind: skill.loaded
          name: create-issue
    expect_state:
      - kind: forgejo.issue
        id: main_issue
        match:
          title: E2E {{ run.id }} create issue
        assert:
          count: 1
          state: open
          body_equals_file: issue-body.md
    expect_audit:
      events:
        - root: tea.issues.create
          min: 1
          max: 1
      budgets:
        total_commands:
          max: 12
        total_mutations:
          max: 2
        per_root:
          tea.issues.create:
            min: 1
            max: 1
          tea.issues.list:
            max: 3
          tea.issues.show:
            max: 3
          tea.labels.list:
            max: 3
```

- [ ] **Step 4: Update imports and paths**

In `tests/e2e/test_agent_e2e.py`, replace imports from `tests.e2e.suites.tea` with `tests.e2e.tea_suite`, and change scenario/default paths to:

```python
scenario_path = ROOT / "tests/e2e/tea_suite/scenarios/issues.yaml"
defaults_path = ROOT / "tests/e2e/tea_suite/defaults.yaml"
```

In `tests/e2e/test_harness_unit.py`, replace imports from `tests.e2e.suites.tea` with `tests.e2e.tea_suite` and mock patch paths accordingly.

In moved `verify_forgejo.py`, replace:

```python
from tests.e2e.suites.tea.provision import api_request
```

with:

```python
from tests.e2e.tea_suite.provision import api_request
```

- [ ] **Step 5: Remove old suite directory**

Run:

```bash
rm -rf tests/e2e/suites
```

- [ ] **Step 6: Run non-live tests**

Run:

```bash
python -m unittest discover -s tests -v
```

Expected: PASS.

- [ ] **Step 7: Commit suite YAML migration**

Run:

```bash
git add tests/e2e
git commit -m "test: move e2e suite to yaml"
```

---

### Task 7: Remove in-repo generic harness copy

**Files:**
- Remove: `/Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness/tests/e2e/harness/`
- Modify: tests if any stale imports remain

- [ ] **Step 1: Search for stale generic harness imports**

Run:

```bash
cd /Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness
rg "tests\.e2e\.harness|from \.harness|e2e/harness" tests docs README.md
```

Expected: no required runtime imports remain. Documentation references to old paths should be updated or removed.

- [ ] **Step 2: Remove old harness directory**

Run:

```bash
rm -rf tests/e2e/harness
```

- [ ] **Step 3: Run tests**

Run:

```bash
python -m unittest discover -s tests -v
```

Expected: PASS.

- [ ] **Step 4: Commit removal**

Run:

```bash
git add tests docs README.md
git commit -m "test: remove in-repo generic harness"
```

---

### Task 8: Document Dokimasia dependency and commands

**Files:**
- Modify: `/Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness/README.md`
- Modify: `/Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness/docs/superpowers/specs/2026-05-14-generic-agent-e2e-harness-extraction-design.md`
- Modify: `/Users/sh/Projects/dokimasia/README.md`

- [ ] **Step 1: Update `tea-skills` README E2E section**

Add to the live E2E requirements list:

```markdown
- Dokimasia is installed for test development: `python -m pip install -e /Users/sh/Projects/dokimasia`.
```

Document agent selection:

```markdown
Run with Pi instead of Claude Code:

```bash
TEA_SKILLS_E2E=1 TEA_SKILLS_E2E_AGENT=pi python -m unittest tests.e2e.test_agent_e2e -v
```
```

- [ ] **Step 2: Update Dokimasia README with package usage**

Append to `/Users/sh/Projects/dokimasia/README.md`:

```markdown
## Development install

```bash
python -m pip install -e /Users/sh/Projects/dokimasia
```

## Python usage

```python
from dokimasia.core.runner import ScenarioRunner
from dokimasia.core.scenarios import load_scenarios
from dokimasia.agents.claude_code import ClaudeCodeAdapter
```

Project suites provide provisioning, audit normalization, and state verification.
```

- [ ] **Step 3: Run tests in both repos**

Run:

```bash
cd /Users/sh/Projects/dokimasia
python -m unittest discover -s tests -v
cd /Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness
python -m unittest discover -s tests -v
```

Expected: both pass.

- [ ] **Step 4: Commit docs in each repo**

Run:

```bash
cd /Users/sh/Projects/dokimasia
git add README.md
git commit -m "docs: document dokimasia usage"
cd /Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness
git add README.md docs/superpowers/specs/2026-05-14-generic-agent-e2e-harness-extraction-design.md
git commit -m "docs: document dokimasia test dependency"
```

---

### Task 9: Final live verification with Claude and optional Pi

**Files:**
- No code changes expected unless a verified bug appears.

- [ ] **Step 1: Run non-live verification**

Run:

```bash
cd /Users/sh/Projects/dokimasia
python -m unittest discover -s tests -v
cd /Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness
python -m unittest discover -s tests -v
```

Expected: both pass.

- [ ] **Step 2: Run live Claude scenario**

Run:

```bash
cd /Users/sh/Projects/tea-skills/.worktrees/agent-e2e-harness
TEA_SKILLS_E2E=1 TEA_SKILLS_E2E_AGENT=claude python -m unittest tests.e2e.test_agent_e2e -v
```

Expected: PASS.

- [ ] **Step 3: Run live Pi scenario if Pi credentials/provider are available**

Run:

```bash
TEA_SKILLS_E2E=1 TEA_SKILLS_E2E_AGENT=pi python -m unittest tests.e2e.test_agent_e2e -v
```

Expected: PASS, or a clear adapter/provider failure with artifacts preserved under `.e2e-artifacts/<run-id>/`.

- [ ] **Step 4: Confirm cleanup**

Run:

```bash
python - <<'PY'
from actions.internal.tea_api import read_tea_config
from tests.e2e.tea_suite.provision import api_request
config = read_tea_config()
orgs = api_request(config, 'GET', 'user/orgs')
print([org.get('username') for org in orgs if isinstance(org, dict) and str(org.get('username', '')).startswith('tea-e2e-')])
PY
```

Expected: `[]` or only intentionally preserved debug orgs.

- [ ] **Step 5: Commit any final fixes or document provider limitation**

If no code changes are needed, do not create a commit. If Pi cannot run due provider/auth limitations, document the exact failure in the final response and keep artifacts.

---

## Self-review

- Spec coverage: package extraction, generic boundary, YAML scenarios, dev dependency, agent selector, artifact preservation, and live verification are covered.
- Placeholder scan: no TODO/TBD placeholders remain.
- Type consistency: plan uses current dataclass names and current runner/adapter call shapes.
- Risk: creating a sibling repo means commits span two git repositories. Each task explicitly states which repo to commit in.
