# Bundled actions

Bundled actions fill known Gitea/Forgejo gaps in the `tea` CLI. Prefer `tea` whenever it supports the workflow.

Action paths are relative to this installed plugin root. When executing an action for another repository, use the absolute action path while keeping the working directory in the target repository.

Example:

```bash
/path/to/tea-skills/actions/issues/dependency-ready.py
```

## Repository targeting

Repository-scoped bundled actions (issue, pull-request, and milestone actions) use **active-host-first** discovery by default. They select the active `tea` login/backend, then target the single git fetch remote whose host matches that backend. If multiple remotes match, or no remote matches, the action fails clearly instead of guessing.

Use explicit scope flags whenever the user names a backend, login, remote, or repository:

- `--login <tea-login>` selects the exact `tea` login/backend, such as `codeberg` or `forgejo-prod`.
- `--remote <git-remote>` selects the owner/repo from a named git remote, such as `upstream`.
- `--repo <owner>/<repo>` selects an owner/repository slug directly. Combine it with `--login` when the backend is not obvious.

Examples:

```bash
# Codeberg login and explicit repository slug
/path/to/tea-skills/actions/issues/dependency-ready.py --login codeberg --repo owner/project

# Self-hosted Forgejo login with owner/repo from a named remote
/path/to/tea-skills/actions/pull-requests/find-by-branch.py --login forgejo-prod --remote upstream

# Same active tea backend, but explicit owner/repo
/path/to/tea-skills/actions/milestones/edit.py --repo team/service v1.0 --deadline 2026-06-01
```


## Domains

- [`issues/`](issues/README.md) — issue comment edit, moderation, reactions, dependencies
- [`pull-requests/`](pull-requests/README.md) — pull request auto-merge configuration
- [`milestones/`](milestones/README.md) — milestone edit
- [`org-labels/`](org-labels/README.md) — organization-level labels

## Private internals

`actions/internal/` contains private Python support code. Do not invoke it directly. Use domain actions and README files instead.
