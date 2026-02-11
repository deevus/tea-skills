---
name: issue-dependencies
description: Manage Gitea/Forgejo issue dependencies — add, remove, list, find ready issues, and visualize dependency graphs.
user-invokable: true
---

# Issue Dependencies

"A depends on B" means B must be done first. B *blocks* A. The tea CLI has no dependency support — use `scripts/tea-dep`.

## Commands

```bash
scripts/tea-dep add 25 26       # #25 depends on #26
scripts/tea-dep rm 25 26        # remove dependency
scripts/tea-dep list 25         # what blocks #25
scripts/tea-dep all             # all dependencies for open issues
scripts/tea-dep ready           # issues with no open blockers
scripts/tea-dep graph           # text visualization of all deps
```

## Cross-Repo Dependencies

The `tea-dep` script works within the current repo. For cross-repo dependencies, use the API helpers directly:

```bash
source scripts/tea-api
_api_post "issues/10/dependencies" '{"index": 5, "owner": "other-owner", "repo": "other-repo"}'
```
