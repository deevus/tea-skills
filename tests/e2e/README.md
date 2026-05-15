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
uv run --with 'dokimasia @ git+ssh://git@forgejo.tail9a847c.ts.net/sh/dokimasia.git' pytest
```

Run the live create-issue agent E2E test:

```bash
TEA_SKILLS_E2E=1 uv run --with 'dokimasia @ git+ssh://git@forgejo.tail9a847c.ts.net/sh/dokimasia.git' pytest tests/e2e/test_agent_e2e.py -v
```

Run with Pi instead of Claude Code:

```bash
TEA_SKILLS_E2E=1 TEA_SKILLS_E2E_AGENT=pi uv run --with 'dokimasia @ git+ssh://git@forgejo.tail9a847c.ts.net/sh/dokimasia.git' pytest tests/e2e/test_agent_e2e.py -v
```

Live run artifacts are stored under `.e2e-artifacts/<run-id>/` by default. Override the artifact directory:

```bash
TEA_SKILLS_E2E=1 TEA_SKILLS_E2E_ARTIFACT_DIR=/tmp/tea-skills-e2e uv run --with 'dokimasia @ git+ssh://git@forgejo.tail9a847c.ts.net/sh/dokimasia.git' pytest tests/e2e/test_agent_e2e.py -v
```

Preserve the disposable remote resources for debugging:

```bash
TEA_SKILLS_E2E=1 TEA_SKILLS_E2E_KEEP_REMOTE=1 pytest tests/e2e/test_agent_e2e.py -v
```

The live test is ordinary pytest code. It provisions and cleans up Forgejo resources in tea-skills fixtures, writes the prompt body file through the Dokimasia `doki_factory` fixture, registers `TEA = cmd.spy("tea")`, asserts command behavior with `TEA.match(...)` and `assert_command_ran(...)`, checks the plain Python command budget with `len(result.commands)`, and verifies Forgejo state through project-owned API assertions. The prompt does not mention skills, `tea`, bundled actions, or forbidden alternatives; skill discovery is part of what the test verifies.

## Dokimasia suite boundary

The live E2E harness uses Dokimasia only for generic pytest-first suite assembly mechanics:

- `dokimasia.pytest.doki_factory` creates run artifacts, materializes command spies, and returns `result.commands`.
- `dokimasia.pytest.cmd` declares executable spies and command matchers.
- `dokimasia.pytest.assert_command_ran` asserts observed command invocations.
- `dokimasia.suite.layout` creates run ids and artifact directories.
- `dokimasia.suite.safety` enforces caller-supplied disposable-resource cleanup policy.
- `dokimasia.suite.env` discovers required executables.

Forgejo provisioning, cleanup, live-test gating, executable choices, and state assertions remain in tea-skills under `tests/e2e/`. Dokimasia stays domain-neutral.
