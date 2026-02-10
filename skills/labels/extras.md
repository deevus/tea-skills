# Labels Extras

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
# Export to JSON
tea labels list --output json > labels.json

# Export to CSV
tea labels list --output json | jq -r '.[] | [.name, .color, .description] | @csv' > labels.csv

# Import from tea file
tea labels create --file labels.csv

# Copy between repos
tea labels list -r owner/source-repo --output json | \
  jq -r '.[] | "tea labels create -r owner/target-repo --name \"\(.name)\" --color \"\(.color)\" --description \"\(.description // "")\""' | sh
```

## Bulk Operations

```bash
# Delete all labels
tea labels list --output json | jq -r '.[].id' | xargs -I{} tea labels delete {}

# Rename prefix (e.g., kind: -> type:)
tea labels list --output json | \
  jq -r '.[] | select(.name | startswith("kind:")) | "\(.id) \(.name)"' | \
  while read id name; do
    tea labels update --id "$id" --name "$(echo "$name" | sed 's/^kind:/type:/')"
  done

# Bulk add label to issues
tea issues list --labels "type:bug" --state open --output json | \
  jq -r '.[].index' | xargs -I{} tea issues edit {} --add-labels "sprint:current"
```

## Organization-Level Labels

```bash
scripts/tea-label-org list
scripts/tea-label-org create "org:team-a" "#0052cc" "Owned by Team A"
```
