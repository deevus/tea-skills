---
name: create-pull
description: Create Gitea/Forgejo pull requests — interactive, with flags, from forks, WIP conventions, and quick patterns.
user-invokable: true
---

# Create Pull Request

Use `tea pulls create` for pull request creation. Bundled actions are only for CLI gaps and are documented under `actions/pull-requests/README.md`.

When resolving `actions/...` paths, use the `actions/` directory bundled relative to this skill directory.


Pass explicit scope flags (`--login`, `--remote`, or `--repo`) to bundled actions when the user names a login, remote, backend, or repository. Otherwise, bundled actions use active-host-first discovery.

## Create

```bash
tea pulls create           # interactive, current branch -> default branch
tea pulls create --title "Add auth" --description "Implements JWT" \
  --head "feature/auth" --base "main" \
  --labels "bugfix" --assignees "sh" --milestone "v1.0"
tea pulls create --head "contributor:feature-branch" --base "main"  # from fork
```

## WIP PR Convention

Use the normal tea CLI and prefix the title with `WIP:` when a Forgejo/Gitea workflow treats WIP titles as draft-like pull requests.

```bash
tea pulls create --title "WIP: Feature" --head feature-branch
tea pulls create --title "WIP: Feature" --head feature-branch --base develop
```

## Quick Pattern

```bash
# PR from current branch
git push -u origin HEAD
tea pulls create --title "$(git log -1 --format=%s)" --head "$(git branch --show-current)"
```

## Rediscover Created PR

`tea pulls create` output is human-oriented. When you need the created PR number or URL for automation, use the structured branch lookup action instead of parsing command output:

```bash
actions/pull-requests/find-by-branch.py
actions/pull-requests/find-by-branch.py --head "$(git branch --show-current)"
actions/pull-requests/find-by-branch.py --head "contributor:feature-branch" --base main
```

The action emits one JSON object per matching pull request as JSONL, suitable for `jq` or direct agent parsing.
