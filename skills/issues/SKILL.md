---
name: issues
description: Manage Gitea/Forgejo issues using the tea CLI. Use when creating, editing, listing, closing, or bulk-operating on issues.
---

# Tea Issues

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

## Create

```bash
tea issues create          # interactive
tea issues create --title "Fix bug" --description "Details" \
  --labels "bug,frontend" --assignees "sh" --milestone "v1.0" --deadline "2025-03-01"
```

## Edit

```bash
tea issues edit 42 --title "New title"
tea issues edit 42 --add-labels "priority:high"
tea issues edit 42 --remove-labels "needs-triage"
tea issues edit 42 --milestone "v2.0"        # change milestone (use "" to clear)
tea issues edit 42 --add-assignees "user1"
tea issues edit 42 --deadline "2025-06-01"
tea issues edit 1 2 3 --add-labels "sprint-5" # edit multiple
```

## Close / Reopen

```bash
tea issues close 42        # or: tea issues close 1 2 3
tea issues reopen 42
```

## Tips

- Prefer `-o simple` for listing; use `--output json` only when parsing with `jq`
- `--kind pulls` searches PRs with the same filters as issues
- `--add-labels` / `--remove-labels` are additive/subtractive, not replacing

For bulk operations, see `extras.md`. For API features (pin, reactions, lock, comments), see `api.md` — backed by scripts in `scripts/`.
