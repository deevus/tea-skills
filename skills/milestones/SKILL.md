---
name: milestones
description: List, show, create, close, reopen, delete, and edit Gitea/Forgejo milestones.
user-invokable: true
---

# Milestones

Script paths in this skill follow the bundled-script convention: `scripts/<name>` means the script bundled with this plugin. Resolve it to the installed plugin path before executing from a project repo.

## List

```bash
tea milestones list -o simple              # open milestones, compact output (recommended)
tea milestones list --state all -o simple   # include closed
tea milestones list --output json           # use json only when parsing with jq
tea milestones list --fields "title,state,items_open,items_closed,duedate,description"
```

## Show

```bash
tea milestones "v1.0"
```

## Create

```bash
tea milestones create                                          # interactive
tea milestones create --title "v1.0" --description "First stable release"
tea milestones create --title "v1.0" --deadline "2025-06-01"   # with due date
```

## Close / Reopen / Delete

```bash
tea milestones close "v1.0"          # or multiple: close "v0.8" "v0.9"
tea milestones reopen "v1.0"
tea milestones delete "v1.0"
```

## Edit (API)

The tea CLI doesn't have a milestone edit command. Use the script:

```bash
scripts/tea-milestone-edit "v1.0" --title "v1.0.0"
scripts/tea-milestone-edit "v1.0" --deadline "2025-06-15"
scripts/tea-milestone-edit "v1.0" --description "Updated release notes"
```

## Tips

- Milestones are identified by name in CLI, by ID in the API
- Deadlines accept date strings like `2025-06-01`
- Deleting a milestone doesn't close its issues — they just become unassigned
