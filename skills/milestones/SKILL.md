---
name: milestones
description: List, show, create, close, reopen, delete, and edit Gitea/Forgejo milestones.
user-invokable: true
---

# Milestones

## List

```bash
tea milestones list -o simple              # open milestones, compact output (recommended)
tea milestones list --state all -o simple   # include closed
tea milestones list --output json           # use json only when parsing is necessary
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

## Edit

The tea CLI doesn't have a milestone edit command. For the bundled action, see `actions/milestones/README.md`.

When resolving `actions/...` paths, use the `actions/` directory bundled relative to this skill directory.


Pass explicit scope flags (`--login`, `--remote`, or `--repo`) to bundled actions when the user names a login, remote, backend, or repository. Otherwise, bundled actions use active-host-first discovery.

## Tips

- Milestones are identified by name in CLI, by ID in the API-backed milestone edit action
- Deadlines accept date strings like `2025-06-01`
- Deleting a milestone doesn't close its issues — they just become unassigned
