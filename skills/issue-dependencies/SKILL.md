---
name: issue-dependencies
description: Manage Gitea/Forgejo issue dependencies via API. Use when adding, removing, or listing dependency relationships between issues.
---

# Tea Issue Dependencies

The `tea` CLI doesn't support dependencies. Use `scripts/tea-dep`.

## Terminology

- **"A depends on B"** -> B must be done first. B *blocks* A.

## Commands

```bash
scripts/tea-dep add 25 26       # #25 depends on #26
scripts/tea-dep rm 25 26        # remove dependency
scripts/tea-dep list 25         # what blocks #25
scripts/tea-dep all             # all dependencies for open issues
scripts/tea-dep ready           # issues with no open blockers
scripts/tea-dep graph           # text visualization of all deps

# Bulk
for pair in "25 26" "9 26" "23 22"; do scripts/tea-dep add $pair; done
```

## Tips

- Dependencies appear in Forgejo web UI on each issue
- Cross-repo dependencies supported (edit script for different owner/repo)
- If API calls fail with 401, refresh token with `tea login`
