# Generic Agent E2E Harness Extraction Design

Date: 2026-05-14
Status: approved design

## Goal

Extract the agent E2E harness into a separate, generic Python package so harness dependencies, scenario formats, adapters, reports, and runtime concerns do not inherit the constraints of this `tea-skills` plugin repository.

The extracted harness must be generic: it must not know about `tea`, Forgejo, Gitea, issues, pull requests, milestones, labels, or Claude Code plugins beyond generic adapter configuration.

## Problem

The current `tests/e2e/harness/` code started inside `tea-skills` to prove the vertical slice quickly. That was useful, but it created two kinds of cross-pollination:

1. The plugin repository avoids package/dependency management for skill runtime content, while a test harness should be free to use normal Python test tooling such as PyYAML, pytest, rich output, and packaging metadata.
2. The generic harness boundary is becoming mixed with the `tea-skills` suite boundary. Generic concepts like scenario loading, artifact directories, trace assertions, and agent adapters sit next to mock `tea` behavior and `tea` audit normalization.

This already caused a design mismatch: the design used YAML scenario sketches, while the implementation used JSON to avoid adding dependencies inside the plugin repository.

## Architecture

Create a separate Python package/repository for the generic harness. `tea-skills` consumes it as a dev/test dependency and keeps only project-specific suite code.

### Generic harness package responsibilities

The generic package owns:

- scenario loading and schema validation;
- YAML-first scenario authoring, with optional JSON compatibility during migration;
- template rendering;
- fixture writing;
- run artifact root selection and artifact preservation;
- agent adapter contracts;
- built-in generic adapters such as Claude Code and Pi;
- trace event parsing and trace assertions;
- audit event model and audit/budget assertions;
- scenario runner orchestration;
- CLI and/or pytest/unittest integration helpers;
- result reporting.

The generic package must not import or mention `tea`, Forgejo, Gitea, or `tea-skills` internals.

Suggested package layout:

```text
agent_e2e/
  __init__.py
  agents/
    __init__.py
    base.py
    claude_code.py
    pi.py
  core/
    __init__.py
    artifacts.py
    model.py
    runner.py
    scenarios.py
    template.py
    trace.py
  audit/
    __init__.py
    assertions.py
    model.py
  cli.py
```

### `tea-skills` suite responsibilities

`tea-skills` owns only the suite code that is specific to testing this plugin's Forgejo workflows:

- mock `tea` executable behavior and fixture packs;
- `tea` command spy/wrapper;
- `tea` and bundled action audit normalization;
- mock state verifiers;
- skill scenario files;
- defaults for this suite;
- thin test/CLI host that wires generic harness interfaces to the `tea-skills` suite implementation.

Suggested in-repo layout after extraction:

```text
tests/e2e/
  tea_suite/
    __init__.py
    mock_tea.py
    fixtures/
      tea/
        fixture-pack-v1/
    defaults.yaml
    scenarios/
      issues.yaml
  test_agent_e2e.py
```

The current generic implementation files under `tests/e2e/harness/` should move to the package. The current `tests/e2e/suites/tea/*` files should remain in this repository, possibly renamed to `tests/e2e/tea_suite/*` for clarity.

## Interfaces

The generic runner should keep an inversion-of-control shape similar to the current implementation:

```python
ScenarioRunner(
    agent_adapter=adapter,
    audit_normalizer=normalize_raw_audit_event,
    state_verifier=verify_state,
).run(scenario, context, env)
```

The generic package defines the data structures and calls project-provided functions. The project provides domain behavior.

### Agent adapter contract

Adapters return normalized run results:

```python
@dataclass
class AgentRunResult:
    exit_code: int
    stdout_path: Path
    stderr_path: Path
    raw_trace_path: Path | None
    trace_events: list[TraceEvent]
    duration_seconds: float
    timed_out: bool = False
```

Trace events use generic names:

```python
@dataclass(frozen=True)
class TraceEvent:
    kind: str
    name: str | None = None
    tool: str | None = None
    text: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
```

Skill trace assertions should accept project-qualified skill names. For example, an expected `create-issue` event is satisfied by an actual `tea:create-issue` event.

### Audit contract

The generic package defines audit event and budget assertion logic. Project suites convert raw audit records into generic audit events:

```python
@dataclass(frozen=True)
class AuditEvent:
    root: str
    argv: list[str]
    cwd: str
    exit_code: int
    mutates: bool
    source: str
    raw: dict[str, Any] = field(default_factory=dict)
```

The generic package does not know what roots mean. It only counts roots, command totals, mutation totals, and successful required events.

## Scenario format

The extracted package should support YAML as the canonical format. JSON compatibility may remain during migration if it is cheap, but new docs and examples should use YAML.

Example `tea-skills` scenario after migration:

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
```

## Dependency policy

The generic harness package may use normal Python testing and packaging dependencies. At minimum it should use PyYAML for YAML loading. It may later add pytest, rich, typer, pydantic, or jsonschema if those improve harness quality.

`tea-skills` remains dependency-light for plugin runtime content. Harness dependencies are dev/test dependencies only and should not be required for installing or using the Claude Code plugin skills.

## Consumption from `tea-skills`

During active development, `tea-skills` can consume the package as an editable path dependency:

```bash
python -m pip install -e /Users/sh/Projects/dokimasia
```

Once stable, the dependency can be pinned by git SHA or package version.

The AI-backed E2E command should remain simple:

```bash
TEA_SKILLS_E2E=1 python -m unittest tests.e2e.test_agent_e2e -v
```

A package CLI may also be supported:

```bash
TEA_SKILLS_E2E=1 doki run tests/e2e/tea_suite/scenarios/issues.yaml
```

## Migration plan

1. Create the standalone generic package and move generic modules into it without changing behavior.
2. Update `tea-skills` imports to consume the package while keeping the current mock-backed create-issue scenario passing.
3. Convert `defaults.json` and `issues.json` to YAML.
4. Add an env/CLI agent selector so the same suite can run against Claude Code or Pi.
5. Remove duplicated generic harness code from `tea-skills` once the dependency is wired.
6. Keep Forgejo/tea-specific mock behavior, audit normalization, and state verifiers in `tea-skills`.

## Success criteria

- The generic package has no imports from `tea-skills`, no references to Forgejo/Gitea/tea, and no scenario assumptions beyond generic contracts.
- `tea-skills` still passes the non-AI test suite.
- The AI-backed create-issue scenario still passes against the mock `tea` executable using the external harness package.
- Scenario files in `tea-skills` are YAML.
- Harness artifacts continue to default to `.e2e-artifacts/<run-id>/`, configurable by environment.
- Claude Code and Pi adapters both continue to force current-checkout skill source isolation where applicable.

## Non-goals

- Do not build the full every-skill scenario catalog as part of the extraction.
- Do not move mock `tea` behavior or `tea` audit normalization into the generic package.
- Do not require the generic package to know about Claude Code plugin structure beyond adapter configuration.
- Do not make AI-backed E2E tests run by default.
