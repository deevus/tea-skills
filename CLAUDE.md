# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude Code **plugin** providing skills for Gitea/Forgejo workflows via the [tea CLI](https://gitea.com/gitea/tea). Installed with `claude mcp add-plugin tea /path/to/tea-skills`. There is no build system or package manager — this is markdown plus Python bundled actions.

## Architecture

### Focused Single-File Skills

Each skill lives in its own directory with a single `skills/<name>/SKILL.md` file. Skills are action-specific (e.g., `create-issue`, `merge-pull`) rather than domain-broad, keeping each skill focused and readable.

**Issues domain:** `list-issues`, `create-issue`, `edit-issues`, `close-issues`, `issue-comments`, `issue-dependencies`, `issue-moderation`
**Pulls domain:** `list-pulls`, `create-pull`, `review-pull`, `merge-pull`, `close-pulls`
**Milestones domain:** `milestones`, `milestone-issues`
**Labels domain:** `labels`, `label-schemes`

### Skill Routing

Skills are user-invokable directly from `skills/<name>/SKILL.md`. There is currently no `commands/` directory; keep any future command stubs thin and route behavior back to the corresponding skill.

### Actions for API Gaps

`actions/` contains bundled Python actions for Gitea/Forgejo features the tea CLI lacks. Skill docs refer to them as `actions/<domain>/<action>` following the bundled-resource convention: resolve that path relative to this installed plugin, then execute the absolute action path while keeping the working directory in the target repository. Do not require users to `cd` into the plugin root or put `actions/` on `PATH`.

Actions are action-specific and organized by domain folders. Domain README files document normal `tea` CLI commands first and bundled actions second. Prefer `tea` wherever it supports the workflow.

Private HTTP support lives in `actions/internal/tea_api.py`. It is stdlib-only Python and is not a user-facing Interface.

### Plugin Registration

- `.claude-plugin/plugin.json` — Plugin metadata (name, version, author)
- `.claude-plugin/marketplace.json` — Marketplace listing wrapper

### Session Hooks

`hooks/session-start.sh` runs on every session start/resume/clear/compact. It checks:
- Whether tea CLI is installed
- Whether tea logins are configured
- Whether we're in a git worktree (tea doesn't auto-detect logins there, so it advises appending `--login <server>`)

`hooks/run-hook.cmd` is a polyglot wrapper (batch + bash) for cross-platform hook execution.

## Key Conventions

- Skills prefer `-o simple` for listing output; `--output json` only when parsing is necessary
- Issue dependencies use the semantic "A depends on B" (B blocks A), managed through bundled actions under `actions/issues/` since tea CLI has no dependency support
- In skill docs, `actions/<domain>/<action>` means the bundled plugin action path, not a path in the user's repo
- Labels are referenced by **name** in `tea issues` but by **ID** in `tea labels update/delete`
- Milestones are referenced by **name** in CLI but by **ID** in the API-backed milestone edit action
- Repository-targeting behavior is origin-first: prefer `origin` unless the user states or requests another backend, login, remote, or repository. API-backed actions may accept explicit scope flags for non-origin targets.

## Adding a New Skill

1. Create `skills/<name>/SKILL.md` with YAML frontmatter (`name`, `description`, `user-invokable: true`) and command reference
2. Prefer documenting `tea` CLI commands directly when `tea` supports the workflow
3. Reference `actions/<domain>/README.md` for bundled action usage when the workflow is an API gap

## Adding a New Action

1. Confirm the workflow cannot be handled cleanly by `tea`; if `tea` supports it, document the `tea` command instead.
2. Create an executable Python file under `actions/<domain>/<action>` with `#!/usr/bin/env python3`.
3. Use `actions/internal/tea_api.py` for API access; do not shell out to external HTTP or JSON command-line tools.
4. Add or update the domain `actions/<domain>/README.md` with purpose, usage, arguments, and `tea` alternatives.
5. Make it executable: `chmod +x actions/<domain>/<action>`.
