# Dokimasia File Spies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update tea-skills to latest Dokimasia and use Dokimasia's general invocation/file-spy API for bundled action E2E assertions.

**Architecture:** Keep tea-skills' mock Forgejo and action-domain assertions project-owned, but move action invocation observation into Dokimasia's normalized `result.commands`. Create file spy wrappers in the disposable plugin root for copied bundled actions, then assert them with `assert_invoked`.

**Tech Stack:** Python 3.10+, pytest, uv dependency groups, Dokimasia `assert_invoked`, `cmd.match`, and `create_file_spy`.

---

### Task 1: Update Dokimasia lock

**Files:**
- Modify: `uv.lock`

- [x] **Step 1: Update dependency resolution**

Run:

```bash
uv lock --upgrade-package dokimasia
```

Expected: `uv.lock` changes Dokimasia git source from `562b599...` to latest `main`.

- [x] **Step 2: Verify import surface**

Run:

```bash
uv run --group e2e python - <<'PY'
from dokimasia.pytest import assert_invoked, cmd
from dokimasia.suite import create_file_spy
print(assert_invoked.__name__, cmd.__name__, create_file_spy.__name__)
PY
```

Expected: prints `assert_invoked dokimasia.pytest.cmd create_file_spy` or equivalent names without import errors.

### Task 2: Add failing tests for file spy wiring

**Files:**
- Modify: `tests/e2e/test_harness_unit.py`
- Modify: `tests/e2e/test_agent_e2e.py`

- [x] **Step 1: Write tests first**

Add unit tests that expect `test_agent_e2e` to expose `DEPENDENCY_ADD_ACTION`, `LOCK_ACTION`, and `install_action_file_spies`, and that `install_action_file_spies` replaces plugin action files with wrappers that append normalized events to `DOKIMASIA_COMMAND_LOG`.

- [x] **Step 2: Run tests and verify red**

Run:

```bash
uv run --group e2e pytest tests/e2e/test_harness_unit.py::test_action_matchers_accept_file_spy_invocations tests/e2e/test_harness_unit.py::test_install_action_file_spies_wraps_workspace_actions -v
```

Expected: FAIL because the new matcher/helper names do not exist yet.

### Task 3: Implement file spy wiring

**Files:**
- Modify: `tests/e2e/test_agent_e2e.py`
- Modify: `tests/e2e/test_harness_unit.py`

- [x] **Step 1: Import latest APIs**

Replace `assert_command_ran` with `assert_invoked` and import `create_file_spy` from `dokimasia.suite`.

- [x] **Step 2: Add action matchers**

Define:

```python
DEPENDENCY_ADD_ACTION = cmd.match("actions/issues/dependency-add.py", pattern=["2", "1"], mode="exact")
LOCK_ACTION = cmd.match("actions/issues/lock.py", pattern=["1", "spam"], mode="exact")
```

- [x] **Step 3: Add spy installation helper**

Create `install_action_file_spies(plugin_root: Path) -> None` that wraps `actions/issues/dependency-add.py` and `actions/issues/lock.py` in the disposable plugin copy, forwarding to the real repository actions with `source="tea-skills-action"`.

- [x] **Step 4: Use action spies in E2E fixture**

Copy skills and action files into the disposable plugin root, call `install_action_file_spies(plugin_root)`, and let Dokimasia load file-spy events from `DOKIMASIA_COMMAND_LOG`.

- [x] **Step 5: Assert action invocations through Dokimasia**

Replace manual `action_audit_events(...)` checks with:

```python
assert_invoked(result, DEPENDENCY_ADD_ACTION, times=1)
assert_invoked(result, LOCK_ACTION, times=1)
```

Keep independent mock Forgejo state assertions unchanged.

### Task 4: Update docs and verify

**Files:**
- Modify: `tests/e2e/README.md`

- [x] **Step 1: Document new boundary**

Update the Dokimasia boundary section to mention `assert_invoked` and file spies for bundled actions.

- [x] **Step 2: Run focused tests**

Run:

```bash
uv run --group e2e pytest tests/e2e/test_harness_unit.py -v
```

Expected: PASS.

- [x] **Step 3: Run full non-AI tests**

Run:

```bash
uv run --group e2e pytest
```

Expected: PASS with AI-backed E2E tests skipped unless `TEA_SKILLS_E2E=1` is set.
