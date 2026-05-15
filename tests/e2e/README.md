# tea-skills E2E tests

This directory contains the tea-skills opt-in live agent E2E harness. These docs are for contributors testing this repository, not for users installing or consuming the skill plugin.

The harness runs a real agent against a real Forgejo server using disposable `tea-e2e-*` organizations and repositories.

## Requirements

- `tea` is installed and already logged in to a Forgejo/Gitea server.
- The logged-in account can create and delete organizations and repositories.
- Claude Code is installed and authenticated.
- `uv` is installed. The E2E test commands install Dokimasia from `git+ssh://git@forgejo.tail9a847c.ts.net/sh/dokimasia.git`.

## Commands

Run the non-live tests:

```bash
uv run --with 'dokimasia @ git+ssh://git@forgejo.tail9a847c.ts.net/sh/dokimasia.git' python -m unittest discover -s tests -v
```

Run the live create-issue agent E2E scenario:

```bash
TEA_SKILLS_E2E=1 uv run --with 'dokimasia @ git+ssh://git@forgejo.tail9a847c.ts.net/sh/dokimasia.git' python -m unittest tests.e2e.test_agent_e2e -v
```

Run with Pi instead of Claude Code:

```bash
TEA_SKILLS_E2E=1 TEA_SKILLS_E2E_AGENT=pi uv run --with 'dokimasia @ git+ssh://git@forgejo.tail9a847c.ts.net/sh/dokimasia.git' python -m unittest tests.e2e.test_agent_e2e -v
```

Live run artifacts are stored under `.e2e-artifacts/<run-id>/` by default. Override the artifact directory:

```bash
TEA_SKILLS_E2E=1 TEA_SKILLS_E2E_ARTIFACT_DIR=/tmp/tea-skills-e2e uv run --with 'dokimasia @ git+ssh://git@forgejo.tail9a847c.ts.net/sh/dokimasia.git' python -m unittest tests.e2e.test_agent_e2e -v
```

Preserve the disposable remote resources for debugging:

```bash
TEA_SKILLS_E2E=1 TEA_SKILLS_E2E_KEEP_REMOTE=1 python -m unittest tests.e2e.test_agent_e2e -v
```

The harness records agent traces, `tea` calls, and bundled action calls under the run artifact directory, then verifies Forgejo state against the live server. Failure messages include the scenario artifact path. Scenario prompts do not mention skills, `tea`, bundled actions, or forbidden alternatives; skill discovery is part of what the test verifies.

## Dokimasia suite boundary

The live E2E harness uses Dokimasia suite helpers for generic suite assembly mechanics:

- `dokimasia.suite.layout` creates run ids and artifact directories.
- `dokimasia.suite.spy` creates the audited command wrapper used to observe host CLI calls.
- `dokimasia.suite.safety` enforces caller-supplied disposable-resource cleanup policy.
- `dokimasia.suite.env` prepends spy directories to `PATH` and discovers required executables.

Forgejo provisioning, tea audit normalization, and state verification remain in tea-skills under `tests/e2e/tea_suite/`. Tea-skills owns the project-specific resource names, executable choices, audit roots, and Forgejo assertions; Dokimasia owns only the generic helpers those pieces compose with.
