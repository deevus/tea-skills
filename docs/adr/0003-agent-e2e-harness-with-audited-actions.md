# Add an audited agent E2E harness for Forgejo skills

The project will add an end-to-end integration harness that runs real agent sessions against a real Forgejo server, using disposable Forgejo organizations and repositories. This ADR is the source of truth for the harness architecture. The companion design spec may add examples and implementation notes, but should not contradict these decisions.

## Context

The action-based API gap adapter design requires post-task integration testing against Forgejo/Gitea. A command-only test would verify `tea` and bundled actions, but would not verify that agents discover and use the skills correctly. A pure agent transcript test would verify discoverability, but could miss whether the intended Forgejo state was actually created or whether the agent reached it through unaudited routes.

The harness therefore needs three independent evidence streams:

1. Agent trace events, including proof that expected skills were loaded.
2. Audit events for external operations, including `tea` calls and bundled `actions/*` calls.
3. Independent Forgejo state verification through direct API access or otherwise unaudited verifier routes.

## Decision

Build a generic-but-in-repo agent E2E harness under `tests/e2e/`, with `tea-skills` as the first concrete suite.

### Harness ownership and extraction boundary

- Keep the harness in this repository for now.
- Structure it with a generic core and a Forgejo/tea suite layer so it can be extracted later.
- Use pytest as the initial host, but keep the core runner free of pytest imports.

### Scenario execution model

- Scenarios are single-turn agent runs.
- The harness must not answer clarifying questions. A scenario prompt must include enough information for the agent to act.
- Scenarios may run sequentially and may depend on outputs from earlier scenarios.
- A shared suite context may hold IDs such as issue numbers, pull request numbers, milestone names, branch names, and labels.
- Dependent scenarios are skipped when their prerequisites fail.

### Agent environment

- The harness provisions a disposable Forgejo organization and repository for each run or suite strategy.
- The workspace includes only minimal repository context, such as `AGENTS.md` saying that the repository is hosted on Forgejo.
- Scenario prompts must not explicitly tell the agent to use skills, `tea`, bundled actions, or avoid `curl`.
- Skill discoverability is part of what the harness tests.

### Required agent adapter capability

Every supported MVP agent adapter must expose normalized trace events proving skill usage. A scenario may require events such as:

```json
{"kind":"skill.loaded","name":"create-issue"}
```

If an adapter cannot prove skill loading, it is not suitable for this E2E suite.

### Audit events

The agent process receives an instrumented environment:

- A `tea` wrapper earlier in `PATH` records every agent `tea` invocation and then delegates to the real `tea` binary.
- Bundled `actions/*` support `TEA_SKILLS_AUDIT_LOG` and log their own invocations when the variable is set.
- Old `scripts/*` are assumed not to exist for this harness.
- The harness does not invoke bundled actions directly during setup, verification, or cleanup.

Audit logs are JSONL and normalized into root events such as:

```text
tea.issues.create
action.issues.dependency-add
action.milestones.edit
```

Raw argv and process details are retained for diagnostics, but assertions should prefer normalized roots.

### State verification

The harness independently verifies Forgejo state after each scenario. Verification must not use the agent's audited command path. The Forgejo/tea suite provides state verifiers for issues, comments, dependencies, locks, pins, reactions, labels, org labels, milestones, pull requests, reviews, and repositories.

A scenario passes only when all required evidence agrees:

1. Expected skill load events were observed.
2. Expected Forgejo state exists.
3. Expected audited mutations explain the state change.
4. Command budgets and execution timeout were not exceeded.

If final Forgejo state is correct but no audited mutation explains it, the scenario fails as an unattributed mutation.

### Budgets and loop detection

The harness uses default command budgets with per-scenario overrides.

- Mutating roots are strict by default.
- Read/list/show roots are allowed but bounded.
- Repeated root commands beyond the configured budget fail the scenario as loop/confusion evidence.
- Legitimate retries or idempotent actions must be explicitly allowed by the scenario.
- The harness enforces wall-clock timeouts. No cost budget is included.

### Safety and cleanup

- The harness creates uniquely named disposable organizations and repositories, such as `tea-e2e-*`.
- Cleanup deletes only resources matching the current run identity.
- The harness refuses destructive cleanup for resources outside its naming/run-id guardrails.
- Full artifacts are preserved on failure, including agent stdout/stderr, raw traces, audit logs, normalized events, state snapshots, and cleanup diagnostics.

## Consequences

This design tests agent behavior, skill discoverability, command routing, and real Forgejo state together. It is more complex than command-level tests, but catches failures that unit tests and command-only integration tests cannot catch.

The harness will be slower and more environment-dependent than unit tests because it requires an existing configured `tea` login and a Forgejo server where disposable orgs/repos can be created. It should therefore be opt-in and clearly separated from fast tests.

## Non-goals

- Do not build a generic external package in this pass.
- Do not provision a local Forgejo server or configure `tea login` automatically.
- Do not support adapters that cannot expose skill-load trace evidence.
- Do not make multi-turn clarification handling part of the MVP.
- Do not use VCR/cassettes as the main E2E signal.
- Do not invoke bundled actions manually from the harness to satisfy scenario expectations.
