# Milestone actions

Prefer the `tea` CLI for normal milestone workflows:

```bash
tea milestones list -o simple
tea milestones create --title "v1.0" --description "First stable release"
tea milestones close "v1.0"
tea milestones reopen "v1.0"
tea milestones delete "v1.0"
tea milestones issues add "v1.0" 42
tea milestones issues remove "v1.0" 42
```

Use bundled actions only for milestone features that `tea` does not expose cleanly.

## Edit milestone

```bash
actions/milestones/edit.py <milestone-name> [--title <title>] [--deadline YYYY-MM-DD] [--description <text>]
```

Milestones are identified by name in `tea`, but by ID in the Gitea/Forgejo API. This action looks up the ID before editing.
