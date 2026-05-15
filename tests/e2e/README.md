# tea-skills E2E tests

This directory contains the tea-skills opt-in AI agent E2E harness. These docs are for contributors testing this repository, not for users installing or consuming the skill plugin.

The harness runs Pi against a local mock `tea` executable with this checkout's skills and local Pi extensions disabled. It does not require a host `tea` binary, configured login, or Forgejo/Gitea server.

## Requirements

- Pi is installed and configured.
- `uv` is installed. E2E dependencies are declared in `pyproject.toml` under the `e2e` dependency group and locked in `uv.lock`.

Runtime skill actions remain dependency-free; the `e2e` dependency group is only for contributor tests.

## Commands

Run the non-AI tests:

```bash
uv run --group e2e pytest
```

Run the AI-backed create-issue E2E test with Pi:

```bash
TEA_SKILLS_E2E=1 uv run --group e2e pytest tests/e2e/test_agent_e2e.py -v
```

Run the same test with a specific model through Dokimasia's generic model env var:

```bash
TEA_SKILLS_E2E=1 DOKIMASIA_MODEL=deepseek/deepseek-v4-flash uv run --group e2e pytest tests/e2e/test_agent_e2e.py -v
```

Artifacts are stored under `.e2e-artifacts/<run-id>/` by default. Override the artifact directory:

```bash
TEA_SKILLS_E2E=1 TEA_SKILLS_E2E_ARTIFACT_DIR=/tmp/tea-skills-e2e uv run --group e2e pytest tests/e2e/test_agent_e2e.py -v
```

## Mock tea behavior

The test creates a local executable named `tea` before constructing the Dokimasia run. Dokimasia's `cmd.spy("tea")` wraps that mock executable, so `result.commands` and `assert_command_ran(...)` use the normal Dokimasia command assertion path without delegating to a system executable.

The mock stores issue state in JSON under the run artifact root and renders output from a versioned fixture pack. It supports the commands needed by the create-issue skill scenario and session-start hook checks:

- `tea logins`
- `tea login list`
- `tea login list -o csv`
- `tea issues create --title ... --description ...`
- `tea issues create --title ... --body issue-body.md`
- `tea issues list -o simple`
- `tea issues show <number>`

Issue command aliases such as `tea issue c ...`, `tea i ls`, and `tea issue <number>` are also handled when they are part of the tested workflow. The E2E assertion verifies local mock state instead of querying a remote service.

## Fixture pack maintenance

Versioned output fixtures live under:

```text
tests/e2e/tea_suite/fixtures/tea/fixture-pack-v1/
```

Keep fixture output as plain text files so changes are easy to review. If a future suite needs to model a different `tea` output style, add a new fixture pack directory such as `fixture-pack-v2/` and point the mock to it; do not silently rewrite old fixture semantics.

When adding mock command behavior, update both the fixture pack manifest and focused harness unit tests so expected stdout, stderr, exit codes, and state mutations stay documented.

## Dokimasia suite boundary

The E2E harness uses Dokimasia only for generic pytest-first suite mechanics:

- `dokimasia.pytest.doki_factory` creates run artifacts, materializes command spies, and returns `result.commands`.
- `dokimasia.pytest.cmd` declares executable spies and command matchers.
- `dokimasia.pytest.assert_command_ran` asserts observed command invocations.
- `dokimasia.suite.layout` creates run ids and artifact directories.

Mock `tea` behavior, fixture packs, local issue state, executable choices, and state assertions remain in tea-skills under `tests/e2e/`. Dokimasia stays domain-neutral.
