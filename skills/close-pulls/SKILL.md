---
name: close-pulls
description: Close and reopen Gitea/Forgejo pull requests — single, multiple, and bulk close stale PRs.
user-invokable: true
---

# Close / Reopen Pull Requests

## Close

```bash
tea pulls close 15         # close without merging
```

## Reopen

```bash
tea pulls reopen 15
```

## Bulk Close Stale PRs

```bash
tea pulls list --state open --output json | \
  jq -r '.[] | select(.updated | fromdateiso8601 < (now - 90*86400)) | .index' | \
  xargs tea pulls close
```
