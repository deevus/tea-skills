# Action-based API Gap Adapter Design

Date: 2026-05-14

## Summary

Replace the current shallow `scripts/tea-api` sourced bash helper and fragmented `scripts/tea-*` commands with an action-oriented structure under `actions/`. Bundled actions should exist only for Gitea/Forgejo workflows that the `tea` CLI cannot express cleanly. Normal workflows should route to `tea` and be documented beside the gap-filling actions.

The private HTTP Adapter will live at `actions/internal/tea_api.py`. It will be Python stdlib-only and will own transport mechanics: config discovery, repo context, URL/query encoding, JSON encoding/decoding, HTTP status handling, and consistent errors. User-facing action files will be thin Python executables that parse arguments, call domain helper functions, and print concise human-readable output.

## Goals

- Make the user-facing command Interface honest: command paths name the exact missing capability.
- Avoid broad command names that imply unsupported coverage, such as a milestone command that only edits milestones.
- Remove bash JSON quoting, raw `curl`, and `jq` dependencies from bundled API-gap actions.
- Centralize HTTP and Gitea/Forgejo API mechanics behind one private Adapter seam.
- Keep skills lean by routing agents to domain README files for exact command syntax.
- Prefer `tea` everywhere it already supports the workflow.

## Non-goals

- Do not implement the full `tea` API.
- Do not preserve compatibility wrappers for old `scripts/tea-*` names.
- Do not expose `actions/internal/tea_api.py` as a public user-facing API.
- Do not add `--login`, `--repo`, or `--remote` support in this pass.
- Do not add a non-interactive pull request review submission action while `tea` has review, approve, reject, review-comments, resolve, and unresolve commands.

## Architecture

### Directory layout

```text
actions/
  README.md
  internal/
    README.md
    tea_api.py

  issues/
    README.md
    comment-edit
    lock
    unlock
    pin
    unpin
    reaction-add
    reaction-list
    dependency-add
    dependency-remove
    dependency-list
    dependency-all
    dependency-ready
    dependency-graph

  pull-requests/
    README.md
    set-automerge

  milestones/
    README.md
    edit

  org-labels/
    README.md
    list
    create
```

The old `scripts/` directory is replaced by `actions/`. The old `scripts/tea-api` helper and old `scripts/tea-*` executables are removed without compatibility wrappers. Agents will read updated skills and action README files fresh.

### Naming rules

- Use `actions/<domain>/<action>`.
- Use one domain folder level for now.
- Do not use subcommands in user-facing actions.
- Do not use broad filenames unless the action truly covers the broad domain.
- Include the mutation or intent when a shorter name would imply the final outcome. For example, `pull-requests/set-automerge` sets or cancels the auto-merge configuration; it does not merge the pull request immediately.
- Keep paired tiny operations as separate files where the action is clearer, e.g. `issues/lock` and `issues/unlock`, `issues/pin` and `issues/unpin`.

This makes the Interface deeper and clearer: agents can infer intended use from the path itself, while the Implementation hides transport details behind the internal Adapter.

## Documentation model

README files are part of the command Interface.

### `actions/README.md`

Document global rules:

- Prefer the `tea` CLI.
- Use bundled actions only for known CLI gaps.
- Resolve action paths relative to the installed plugin root.
- `actions/internal/` is private.
- Domain README files are the authoritative command references.

### Domain README files

Each domain README should document `tea` commands first, then bundled actions.

- `actions/issues/README.md`
  - Document common `tea` issue commands: list, show, create, edit, close/reopen, add comment, list comments.
  - Document bundled actions for gaps: comment edit, lock/unlock, pin/unpin, reactions, dependencies.

- `actions/pull-requests/README.md`
  - Document `tea pulls create`, `edit`, `review`, `approve`, `reject`, `merge`, `review-comments`, `resolve`, and `unresolve`.
  - Document bundled `set-automerge` only.

- `actions/milestones/README.md`
  - Document `tea milestones list`, `create`, `close`, `reopen`, `delete`, and `issues`.
  - Document bundled `edit` only.

- `actions/org-labels/README.md`
  - Document that repo labels use `tea labels`.
  - Document org-level label `list` and `create` actions.

### Skill docs

Skill docs should stop inlining full bundled action syntax. They should reference the relevant domain README, with a short routing note when useful. They should no longer document `source scripts/tea-api` or direct `_api_*` calls.

Top-level `README.md` should introduce bundled actions, explain that they supplement rather than replace `tea`, and point to `actions/README.md`.

## Capability audit and final action surface

Keep bundled actions only for workflows where `tea` is insufficient.

### Keep and migrate

Issue actions:

```text
actions/issues/comment-edit
actions/issues/lock
actions/issues/unlock
actions/issues/pin
actions/issues/unpin
actions/issues/reaction-add
actions/issues/reaction-list
actions/issues/dependency-add
actions/issues/dependency-remove
actions/issues/dependency-list
actions/issues/dependency-all
actions/issues/dependency-ready
actions/issues/dependency-graph
```

Pull request actions:

```text
actions/pull-requests/set-automerge
```

Milestone actions:

```text
actions/milestones/edit
```

Org label actions:

```text
actions/org-labels/list
actions/org-labels/create
```

### Remove instead of migrate

- `scripts/tea-pr-draft`
  - Use `tea pulls create` with the WIP title convention where appropriate.
- `scripts/tea-pr-reviewers`
  - Use `tea pulls edit <pr> --add-reviewers ...` and `tea pulls edit <pr> --remove-reviewers ...`.

### Route raw API examples to `tea`

The current raw `_api_get` / `_api_post` examples in pull request review docs should be removed where `tea` exists:

- PR diff/patch: use `tea pulls <pr> --fields diff,patch`.
- PR file listing: remove the raw API example in this refactor; do not add a bundled action unless a later workflow proves `tea` lacks a required file-listing path.
- PR review comments: use `tea pulls review-comments`.
- Resolve/unresolve: use `tea pulls resolve` / `tea pulls unresolve`.
- Approve/reject/review: use `tea pulls approve`, `tea pulls reject`, and `tea pulls review`.

No `actions/pull-requests/review-submit` action is included in this design.

## Internal Adapter

`actions/internal/tea_api.py` is the private HTTP Adapter Module.

### Context responsibilities

- Discover tea config in this order:
  1. `$XDG_CONFIG_HOME/tea/config.yml` when `XDG_CONFIG_HOME` is set.
  2. `~/.config/tea/config.yml` otherwise.
- Read the token and base URL needed for API requests.
- Derive `OWNER` and `REPO` from `git remote get-url origin` for this pass.
- Construct repo and org API roots.
- Keep the design structured so later `--login`, `--repo`, or `--remote` support can be added without changing every action.

### HTTP responsibilities

- Use only the Python standard library, including `urllib.request` and `urllib.parse` for HTTP and URL handling.
- Support GET, POST, PATCH, and DELETE.
- Encode JSON request bodies safely.
- Decode JSON responses where needed.
- Encode query parameters centrally.
- Apply consistent authentication and content headers.

### Error responsibilities

- Include method, endpoint, and HTTP status in errors.
- Include response body when useful and safe.
- Let action scripts print human-readable errors to stderr and exit nonzero.
- Preserve idempotent domain handling where useful, such as dependency add returning a clear “already exists” message on conflict.

### Domain helper responsibilities

The Adapter should expose Python functions for the action scripts, including:

- edit issue comment
- lock/unlock issue
- pin/unpin issue
- add/list issue reactions
- add/remove/list issue dependencies
- list all dependencies, ready issues, and dependency graph data
- lookup milestone by name and edit milestone fields
- list/create org labels
- enable/cancel pull request auto-merge

Action files should stay thin: argument parsing, one Adapter call, and concise output formatting.

## Testing and verification

### Unit-style Adapter tests

Add tests for `actions/internal/tea_api.py` without real network access:

- Config discovery via `XDG_CONFIG_HOME` and fallback to `~/.config`.
- Repo context parsing from a controlled git remote.
- URL and query parameter encoding.
- JSON payload encoding.
- HTTP error formatting and non-2xx handling.
- Domain status handling, especially idempotent dependency operations.

### Post-task integration test

After the migration, run a real integration test against a Forgejo/Gitea repository. Cover at least one representative action from each domain:

- issue lock/unlock or pin/unpin
- issue dependency add/remove
- milestone edit
- org label list; org label create only against a disposable test org or with explicit approval for a temporary label
- pull request set-automerge if a suitable PR exists

### Acceptance criteria

- `actions/` replaces `scripts/` for bundled gap-filling commands.
- No user-facing action shells out to `curl` or `jq`.
- No user-facing action depends on the old sourced `tea-api` Interface.
- `actions/internal/tea_api.py` is private and stdlib-only.
- Domain README files document both normal `tea` routes and bundled actions.
- Skill docs reference `actions/<domain>/README.md` rather than duplicating action syntax.
- Workflows supported by `tea` route to `tea`, not bundled actions.
