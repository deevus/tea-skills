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

## Repository targeting

Milestone actions use active-host-first discovery by default. Pass explicit scope flags when the user names a login, remote, backend, or repository:

```bash
actions/milestones/edit.py --login codeberg --repo owner/project v1.0 --deadline 2026-06-01
actions/milestones/edit.py --remote upstream v1.0 --title "Version 1"
actions/milestones/edit.py --login forgejo-prod --repo team/service v1.0 --description "Stable release"
```

Use `--login` for an exact `tea` login, `--remote` for owner/repo from a git remote, and `--repo` for an explicit `owner/repo` slug.


## Edit milestone

```bash
actions/milestones/edit.py <milestone-name> [--title <title>] [--deadline YYYY-MM-DD] [--description <text>]
```

Milestones are identified by name in `tea`, but by ID in the Gitea/Forgejo API. This action looks up the ID before editing.
