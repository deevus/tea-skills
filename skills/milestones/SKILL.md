---
name: milestones
description: Manage Gitea/Forgejo milestones using the tea CLI. Use when creating, closing, tracking, or assigning issues to milestones.
---

# Tea Milestones

## List

```bash
tea milestones list                   # open (default)
tea milestones list --state all       # include closed
tea milestones list --output json
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

## Manage Issues in Milestones

```bash
tea milestones issues "v1.0"                              # list issues
tea milestones issues "v1.0" --state all --kind issue     # filter by state/kind
tea milestones issues "v1.0" --fields "index,title,state,assignees,labels"
tea milestones issues add "v1.0" 42                       # assign issue
tea milestones issues remove "v1.0" 42                    # unassign issue
```

## Tips

- Milestones are identified by name in CLI, by ID in the API
- Deadlines accept date strings like `2025-06-01`
- Deleting a milestone doesn't close its issues — they just become unassigned

For editing milestones, bulk assignment, progress tracking, and burndown patterns, see `extras.md`. API setup: `_api-setup.md`.
