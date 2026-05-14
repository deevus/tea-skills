# Agent E2E Harness Augmentation Design

Date: 2026-05-14

Status: augmentation to `2026-05-14-action-based-api-gap-adapter-design.md`

Source of truth: `docs/adr/0003-agent-e2e-harness-with-audited-actions.md`

## Summary

Augment the action-based API gap adapter work with an opt-in agent-facing end-to-end harness. The harness runs real single-turn agent sessions against a real Forgejo server, using disposable Forgejo organizations and repositories. It verifies not only that Forgejo state changes correctly, but that the agent loaded the expected skill and reached the state through observed `tea` or bundled `actions/*` calls.

This spec gives implementation detail and examples. The ADR is authoritative for architectural decisions.

## Relationship to the action adapter design

The action adapter design replaces old bash scripts with action-specific `actions/*` executables backed by a private Python adapter. This E2E harness assumes that migration has happened or is being implemented in parallel with these testability hooks:

- Old `scripts/*` are gone.
- New `actions/*` support `TEA_SKILLS_AUDIT_LOG`.
- The harness never invokes bundled actions directly to satisfy scenario expectations.
- Verifier and cleanup routes do not write to the agent audit log.

## Goals

- Verify that agents discover and load the relevant skill without being explicitly told which skill to use.
- Verify real Forgejo state changes in a disposable org/repo.
- Attribute expected mutations to audited `tea` or bundled action calls.
- Detect loop/confusion behavior through repeated command roots and timeouts.
- Keep the harness generic enough to extract later, while implementing it inside this repository first.

## Non-goals

- Do not provision Forgejo or configure `tea login` automatically.
- Do not support multi-turn scenario conversations.
- Do not require exact argv ordering or exact command sequences.
- Do not use cassettes as the main integration signal.
- Do not build a standalone package in this pass.

## Architecture

```text
pytest host
  └─ generic harness core, no pytest imports
      ├─ scenario loader and templating
      ├─ runner and dependency scheduler
      ├─ agent adapter contract
      ├─ trace event assertions
      ├─ audit event ingestion and budgets
      ├─ state verifier plugin contract
      └─ artifact/reporting model

tea suite plugin
  ├─ Forgejo provisioner and cleanup
  ├─ tea PATH spy
  ├─ action audit log parser
  ├─ tea/action command normalizer
  ├─ Forgejo state verifiers
  ├─ default budgets
  └─ scenario files
```

Suggested in-repo layout:

```text
tests/e2e/
  harness/
    runner.py
    scenarios.py
    fixtures.py
    reporting.py
    agents/
      base.py
      claude_code.py
      pi.py
    audit/
      events.py
      budgets.py
    trace/
      events.py
      skills.py

  suites/
    tea/
      provision.py
      tea_spy.py
      normalize.py
      verify_forgejo.py
      defaults.yml
      scenarios/
        issues.yml
        pulls.yml
        milestones.yml
        labels.yml

  test_agent_e2e.py
```

`test_agent_e2e.py` should be a thin pytest adapter around the generic runner. The core runner should remain reusable outside pytest.

## Scenario lifecycle

Each scenario follows this lifecycle:

1. Preflight verifies a real `tea` binary, configured login, Forgejo API access, and adapter support for skill-load traces.
2. Suite provisioning creates a unique temporary Forgejo org and repo.
3. The harness clones the repo into a temporary workspace.
4. The harness writes minimal repository context, for example:

   ```md
   # Repository context

   This repository is hosted on Forgejo.
   ```

5. Scenario fixtures are rendered into the workspace.
6. The harness clears or segments the audit log.
7. The agent adapter runs one prompt in the workspace with the instrumented environment.
8. The harness parses agent trace events and audit events.
9. The suite verifier independently checks Forgejo state.
10. The harness applies trace, audit, budget, and timeout assertions.
11. Successful scenarios may write named outputs into shared run context.
12. Cleanup deletes the disposable repo and org at suite end.

Scenario prompts should be natural user requests. They must not mention installed skills, `tea`, bundled action paths, expected command roots, or forbidden routes such as raw API/curl.

## Scenario schema sketch

```yaml
name: create issue from body file
tags:
  - skill:create-issue
  - domain:issues
  - smoke

fixtures:
  files:
    issue-body.md: |
      E2E body marker: {{ run.id }}

prompt: |
  Create a Forgejo issue titled "{{ issue_title }}".
  Use issue-body.md as the body.

expect_trace:
  events:
    - kind: skill.loaded
      name: create-issue

expect_state:
  - kind: forgejo.issue
    id: main_issue
    match:
      title: "{{ issue_title }}"
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
    total_commands: { max: 12 }
    total_mutations: { max: 2 }
    per_root:
      tea.labels.list: { min: 0, max: 3 }
      tea.issues.list: { min: 0, max: 3 }

outputs:
  issue_main_number: "{{ state.main_issue.number }}"
```

Tags are metadata for filtering, reporting, and coverage. Tags must not inject instructions into the prompt. Pass/fail behavior comes from explicit `expect_*` fields and resolved defaults.

## Agent adapter contract

Every MVP adapter must support single-turn execution and normalized skill usage evidence.

```python
@dataclass
class AgentRunResult:
    exit_code: int
    stdout_path: Path
    stderr_path: Path
    raw_trace_path: Path | None
    trace_events: list[TraceEvent]
    duration_seconds: float
    timed_out: bool
```

Generic trace events include:

```json
{"kind":"skill.loaded","name":"create-issue"}
{"kind":"tool.call","tool":"bash","summary":"tea issues create ..."}
{"kind":"agent.message","role":"assistant","text":"..."}
```

Adapter responsibilities:

- Run one prompt in the provided workspace.
- Pass through the harness environment, including the instrumented `PATH` and `TEA_SKILLS_AUDIT_LOG`.
- Capture stdout, stderr, and raw trace artifacts.
- Normalize skill-load evidence into trace events.
- Enforce single-turn behavior where the agent supports it.
- Allow the harness to enforce an external wall-clock timeout.

Adapters that cannot prove skill loading are out of scope for the MVP.

## Audit event contract

The harness receives audit JSONL from two sources:

1. A `tea` PATH wrapper that logs agent `tea` invocations and delegates to the real binary.
2. Bundled `actions/*` executables that log to `TEA_SKILLS_AUDIT_LOG` when set.

Normalized audit event shape:

```json
{
  "kind": "command",
  "root": "tea.issues.create",
  "argv": ["issues", "create", "--title", "..."],
  "cwd": "/tmp/run/repo",
  "phase": "finish",
  "exit_code": 0,
  "timestamp": "2026-05-14T12:34:56Z",
  "mutates": true,
  "metadata": {
    "source": "tea"
  }
}
```

Action events use the same shape with roots such as `action.issues.dependency-add` and metadata identifying the action path.

Assertions should use normalized roots, not raw argv. Raw argv remains in artifacts for diagnostics.

## State verifier contract

The generic harness delegates state checks to suite-provided verifiers.

```python
verify(expectation, run_context) -> StateCheckResult
```

The Forgejo suite should include verifiers for:

- repositories
- issues
- issue comments
- issue dependencies
- issue locks
- issue pins
- issue reactions
- labels
- organization labels
- milestones
- pull requests
- pull reviews

Verification should use direct Forgejo API access or another unaudited verifier route, not the agent's `tea` wrapper or bundled action audit path.

## Budgets and timeout

Budgets combine defaults with scenario overrides.

Example defaults:

```yaml
defaults:
  execution:
    timeout_seconds: 300
    max_turns: 1

  command_budgets:
    total_commands: { max: 20 }
    total_mutations: { max: 4 }
    repeated_root_default: { max: 3 }

  roots:
    "*.create": { max: 1 }
    "*.delete": { max: 1 }
    "*.merge": { max: 1 }
    "*.list": { max: 5 }
    "*.show": { max: 5 }
```

Rules:

- No cost budget is included.
- Mutating roots are strict by default.
- Read/list/show roots are flexible but bounded.
- Failed commands still count for confusion budgets.
- Legitimate retries or idempotent operations must be explicitly allowed.
- A timeout terminates the agent process, fails the scenario, and preserves artifacts.

## Pass/fail criteria

A scenario passes only when all of these hold:

1. Required skill-load trace events were observed.
2. Expected Forgejo state was independently verified.
3. Expected audited mutation events explain the state change.
4. Command budgets were not exceeded.
5. The agent completed within the timeout and returned successfully.

Failure classes should include:

```text
agent_timeout
agent_nonzero_exit
expected_skill_not_loaded
state_mismatch
missing_audited_mutation
audit_budget_exceeded
cleanup_failed
```

If the Forgejo state is correct but no expected audited mutation was observed, fail with `missing_audited_mutation`. This catches raw API/curl routes without needing to explicitly forbid them.

## Safety and artifacts

The Forgejo suite must:

- create uniquely named resources with a `tea-e2e-*` run identity;
- delete only resources matching the current run identity;
- refuse cleanup outside those guardrails;
- preserve artifacts on failure;
- optionally preserve remote resources for debugging with an explicit flag such as `--keep-remote`.

Artifacts should include:

- rendered scenario YAML;
- agent stdout/stderr;
- raw agent trace;
- normalized trace events;
- raw audit JSONL;
- normalized audit events;
- Forgejo state snapshots;
- cleanup logs.

## Open implementation choices

These are intentionally left to the implementation plan:

- Which agent adapter is implemented first.
- Whether the default isolation mode is one org/repo per suite, per domain, or per scenario.
- The exact scenario inventory for each current skill.
- The exact Forgejo API helper used by the verifier.
