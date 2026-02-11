---
name: close-issues
description: Close and reopen Gitea/Forgejo issues — single, multiple, and bulk close-by-label.
user-invokable: true
---

# Close / Reopen Issues

## Close

```bash
tea issues close 42
tea issues close 1 2 3     # close multiple
```

## Reopen

```bash
tea issues reopen 42
```

## Bulk Close by Label

```bash
tea issues list --labels "wontfix" --output json | jq -r '.[].index' | xargs tea issues close
```
