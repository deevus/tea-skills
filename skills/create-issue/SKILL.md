---
name: create-issue
description: Create Gitea/Forgejo issues — interactive or with flags for title, description, labels, assignees, milestone, and deadline.
user-invokable: true
---

# Create Issue

```bash
tea issues create          # interactive
tea issues create --title "Fix bug" --description "Details" \
  --labels "bug,frontend" --assignees "sh" --milestone "v1.0" --deadline "2025-03-01"
```

## Tips

- All flags are optional; omit any to skip or get prompted interactively
- `--labels` accepts comma-separated label names
- `--assignees` accepts comma-separated usernames
- `--deadline` accepts date strings like `2025-03-01`
