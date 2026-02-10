# Pulls Extras

## Review Checklist Pattern

```bash
tea pulls checkout 15
# ... test locally ...
tea pulls approve 15
tea pulls merge 15 --style squash
tea pulls clean 15
```

## Bulk Close Stale PRs

```bash
tea pulls list --state open --output json | \
  jq -r '.[] | select(.updated | fromdateiso8601 < (now - 90*86400)) | .index' | \
  xargs tea pulls close
```

## List PRs Needing Review

```bash
tea pulls list --output json | \
  jq '.[] | select(.labels | map(.name) | index("needs-review")) | {index, title, author: .poster.login}'
```
