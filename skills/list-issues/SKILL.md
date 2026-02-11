---
name: list-issues
description: List and show Gitea/Forgejo issues — filters, fields, pagination, detail views, comments, export, and counts.
user-invokable: true
---

# List Issues

## List

```bash
tea issues list -o simple                          # open issues, compact output (recommended)
tea issues list --state all -o simple              # include closed
tea issues list --labels "bug,critical" -o simple  # by label
tea issues list --milestones "v1.0" -o simple      # by milestone
tea issues list --assignee "user" --author "user"  # by person
tea issues list --keyword "search term"            # text search
tea issues list --from "2025-01-01" --until "2025-06-01"
tea issues list --output json                      # use json only when parsing with jq
tea issues list --fields "index,title,state,labels,assignees"
tea issues list --page 2 --limit 50
```

## Show

```bash
tea issues 42              # detail view
tea issues 42 --comments   # with comments
```

## Export / Count

```bash
# Export all issues to JSON
tea issues list --state all --output json > issues-backup.json

# Count by state
echo "Open: $(tea issues list --state open --output json | jq length)"
echo "Closed: $(tea issues list --state closed --output json | jq length)"
```

## Tips

- Prefer `-o simple` for listing; use `--output json` only when parsing with `jq`
- `--kind pulls` searches PRs with the same filters as issues
