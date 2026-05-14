# Bundled actions

Bundled actions fill known Gitea/Forgejo gaps in the `tea` CLI. Prefer `tea` whenever it supports the workflow.

Action paths are relative to this installed plugin root. When executing an action for another repository, use the absolute action path while keeping the working directory in the target repository.

Example:

```bash
/path/to/tea-skills/actions/issues/dependency-ready
```

The action derives owner and repo from the target repository's `origin` remote.

## Domains

- [`issues/`](issues/README.md) — issue comment edit, moderation, reactions, dependencies
- [`pull-requests/`](pull-requests/README.md) — pull request auto-merge configuration
- [`milestones/`](milestones/README.md) — milestone edit
- [`org-labels/`](org-labels/README.md) — organization-level labels

## Private internals

`actions/internal/` contains private Python support code. Do not invoke it directly. Use domain actions and README files instead.
