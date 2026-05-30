---
name: merge-pull
description: Merge Gitea/Forgejo pull requests — all merge styles, auto-merge, mark WIP ready, and branch cleanup.
user-invokable: true
---

# Merge Pull Request

Prefer `tea pulls` commands for merge workflows. Bundled actions are only for CLI gaps and are documented under `actions/pull-requests/README.md`.

When resolving `actions/...` paths, use the `actions/` directory bundled relative to this skill directory.


Pass explicit scope flags (`--login`, `--remote`, or `--repo`) to bundled actions when the user names a login, remote, backend, or repository. Otherwise, bundled actions use active-host-first discovery.

## Merge

```bash
tea pulls merge 15                      # merge commit (default)
tea pulls merge 15 --style squash       # squash
tea pulls merge 15 --style rebase       # rebase
tea pulls merge 15 --style rebase-merge # rebase + merge commit
tea pulls merge 15 --style squash --title "feat: add auth" --message "Details"
```

## Auto-Merge

The tea CLI does not expose auto-merge configuration. For the bundled action, see `actions/pull-requests/README.md`.

## Mark WIP Ready

If this repository uses `WIP:` titles as draft-like pull requests, remove the prefix with tea:

```bash
tea pulls edit 15 --title "Feature"
```

## Branch Cleanup

```bash
tea pulls clean 15         # delete local + remote branches after merge
```

## Tips

- Merge styles: `merge`, `squash`, `rebase`, `rebase-merge`
