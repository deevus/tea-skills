# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude Code **plugin** providing skills for Gitea/Forgejo workflows via the [tea CLI](https://gitea.com/gitea/tea). Installed with `claude mcp add-plugin tea /path/to/tea-skills`. There is no build system, test suite, or package manager — this is pure markdown + bash.

## Architecture

### Three-Layer Skill Design

Each skill (issues, pulls, labels, milestones) follows a consistent three-file pattern:

1. **`skills/<name>/SKILL.md`** — Primary context loaded into Claude's prompt. Contains the core tea CLI commands for that domain. This is what Claude reads when the skill is invoked.
2. **`skills/<name>/api.md`** (optional) — API-only features that tea CLI doesn't support, backed by scripts in `scripts/`.
3. **`skills/<name>/extras.md`** — Bulk operations, workflow patterns, and advanced recipes.

### Slash Commands → Skills Routing

`commands/*.md` files are thin stubs with YAML frontmatter. Each just tells Claude to invoke the corresponding `tea:<name>` skill. The actual content lives in `skills/`.

### Scripts for API Gaps

`scripts/` contains bash scripts for Gitea API features the tea CLI lacks. All scripts `source "$(dirname "$0")/tea-api"` which extracts credentials from `~/.config/tea/config.yml` and derives `OWNER`/`REPO` from the git remote. Scripts use `_api_get`, `_api_post`, `_api_patch`, `_api_delete` helpers and their `_status` variants for error handling.

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

- Skills prefer `-o simple` for listing output; `--output json` only when piping to `jq`
- Issue dependencies use the semantic "A depends on B" (B blocks A), managed entirely through `scripts/tea-dep` since tea CLI has no dependency support
- Labels are referenced by **name** in `tea issues` but by **ID** in `tea labels update/delete`
- Milestones are referenced by **name** in CLI but by **ID** in the API
- All API scripts derive repo context from the git remote URL automatically

## Adding a New Skill

1. Create `skills/<name>/SKILL.md` with YAML frontmatter (`name`, `description`) and command reference
2. Create `commands/<name>.md` stub that invokes `tea:<name>`
3. Add API scripts to `scripts/` if needed (source `tea-api` for shared helpers)
4. Add optional `api.md` and `extras.md` companion files

## Adding a New Script

1. Create `scripts/tea-<name>` with `#!/usr/bin/env bash`
2. Source shared helpers: `source "$(dirname "$0")/tea-api"`
3. Use `_api_*` functions for API calls; use `_api_*_status` variants when you need HTTP status codes for error handling
4. Make it executable: `chmod +x scripts/tea-<name>`
