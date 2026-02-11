---
name: edit-issues
description: Edit Gitea/Forgejo issues — title, labels, milestone, assignees, deadline, and bulk edit operations.
user-invokable: true
---

# Edit Issues

## Single Issue

```bash
tea issues edit 42 --title "New title"
tea issues edit 42 --add-labels "priority:high"
tea issues edit 42 --remove-labels "needs-triage"
tea issues edit 42 --milestone "v2.0"        # change milestone (use "" to clear)
tea issues edit 42 --add-assignees "user1"
tea issues edit 42 --deadline "2025-06-01"
```

## Multiple Issues

```bash
tea issues edit 1 2 3 --add-labels "sprint-5"
```

## Bulk Add Label

```bash
# Add label to all open issues in a milestone
tea issues list --milestones "v1.0" --output json | jq -r '.[].index' | xargs -I{} tea issues edit {} --add-labels "release:v1.0"
```

## Tips

- `--add-labels` / `--remove-labels` are additive/subtractive, not replacing
- Pass multiple issue numbers to edit them in one command
