---
name: list-pulls
description: List and show Gitea/Forgejo pull requests — filters, fields, detail views, and finding PRs needing review.
user-invokable: true
---

# List Pull Requests

## List

```bash
tea pulls list -o simple              # open PRs, compact output (recommended)
tea pulls list --state all -o simple  # include closed/merged
tea pulls list --output json          # use json only when parsing with jq
tea pulls list --fields "index,title,state,author,base,head,labels"
```

## Show

```bash
tea pulls 15              # detail view
tea pulls 15 --comments   # with comments
```

## Find PRs Needing Review

```bash
tea pulls list --output json | \
  jq '.[] | select(.labels | map(.name) | index("needs-review")) | {index, title, author: .poster.login}'
```

## Forks and Upstream PRs

See [pull-request-forks](pull-request-forks.md).

## Tips

- Prefer `-o simple` for listing; use `--output json` only when parsing with `jq`
- `tea issues list --kind pulls` searches PRs with all issue filters (labels, milestones, etc.)
