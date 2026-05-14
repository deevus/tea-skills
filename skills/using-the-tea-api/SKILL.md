---
name: using-the-tea-api
description: Direct Gitea/Forgejo API access guidance — prefer tea CLI and bundled actions for known gaps.
user-invokable: true
---

# Using the Tea API

Direct use of the internal Gitea/Forgejo HTTP Adapter is not a user-facing workflow.

Prefer the `tea` CLI for supported operations. For known CLI gaps, use the bundled action README files:

- `actions/issues/README.md`
- `actions/pull-requests/README.md`
- `actions/milestones/README.md`
- `actions/org-labels/README.md`

The private Adapter lives at `actions/internal/tea_api.py` and is used by bundled actions. Do not source or invoke it directly from user workflows.

The full Swagger docs remain available at `$BASE_URL/api/swagger` on your Gitea/Forgejo instance for manual investigation.
