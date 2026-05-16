---
name: list-issues
description: List and show Gitea/Forgejo issues — filters, fields, pagination, detail views, comments, export, and counts.
user-invokable: true
---

# List Issues

## List

```bash
# Repository-scoped listing: prefer an explicit remote or repo/login.
tea issues list --remote <git-remote> -o simple           # e.g. --remote self-hosted
tea issues list --repo <owner>/<repo> --login <login> -o simple

# Add filters to the same repository-scoped command.
tea issues list --remote <git-remote> --state all -o simple              # include closed
tea issues list --remote <git-remote> --labels "bug,critical" -o simple  # by label
tea issues list --remote <git-remote> --milestones "v1.0" -o simple      # by milestone
tea issues list --remote <git-remote> --assignee "user" --author "user"  # by person
tea issues list --remote <git-remote> --keyword "search term"            # text search
tea issues list --remote <git-remote> --from "2025-01-01" --until "2025-06-01"
tea issues list --remote <git-remote> --output json                      # use json only when parsing with jq
tea issues list --remote <git-remote> --fields "index,title,state,labels,assignees"
tea issues list --remote <git-remote> --page 2 --limit 50
```

## Show

```bash
tea issues --remote <git-remote> 42              # detail view
tea issues --remote <git-remote> 42 --comments   # with comments
```

## Export / Count

```bash
# Export all issues in this repository to JSON
tea issues list --remote <git-remote> --state all --output json > issues-backup.json

# Count by state in this repository
echo "Open: $(tea issues list --remote <git-remote> --state open --output json | jq length)"
echo "Closed: $(tea issues list --remote <git-remote> --state closed --output json | jq length)"
```

## Tips

- Do not use bare `tea issues list` when the user asks for issues for the current repository; in multi-repo logins it can return issues across repositories.

- Prefer `-o simple` for listing; use `--output json` only when parsing with `jq`
- `--kind pulls` searches PRs with the same filters as issues
