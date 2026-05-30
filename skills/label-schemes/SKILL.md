---
name: label-schemes
description: Label naming conventions, color schemes, export/import, copy between repos, bulk operations, and org-level labels.
user-invokable: true
---

# Label Schemes

## Naming Conventions

Consistent prefixes make labels scannable and filterable.

```bash
# Type
tea labels create --name "type:bug" --color "#d73a4a" --description "Something isn't working"
tea labels create --name "type:feature" --color "#a2eeef" --description "New feature or request"
tea labels create --name "type:docs" --color "#0075ca" --description "Documentation"
tea labels create --name "type:chore" --color "#e4e669" --description "Maintenance"
tea labels create --name "type:refactor" --color "#d4c5f9" --description "Code restructuring"

# Priority
tea labels create --name "priority:critical" --color "#b60205"
tea labels create --name "priority:high" --color "#d93f0b"
tea labels create --name "priority:medium" --color "#fbca04"
tea labels create --name "priority:low" --color "#0e8a16"

# Status
tea labels create --name "status:blocked" --color "#000000"
tea labels create --name "status:in-progress" --color "#1d76db"
tea labels create --name "status:needs-review" --color "#5319e7"

# Scope
tea labels create --name "scope:frontend" --color "#bfd4f2"
tea labels create --name "scope:backend" --color "#c2e0c6"
tea labels create --name "scope:api" --color "#d4c5f9"
```

## Export / Import

```bash
tea labels list --output json > labels.json
tea labels create --file labels.csv
```

## Bulk Operations

Use `tea labels list --output json` when parsing is necessary, then apply `tea labels update`, `tea labels delete`, or `tea issues edit` to the selected IDs/issues.

## Organization-Level Labels

For organization-level label actions, see `actions/org-labels/README.md`.

When resolving `actions/...` paths, use the `actions/` directory bundled relative to this skill directory.
