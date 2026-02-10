---
name: labels
description: Manage Gitea/Forgejo issue labels using the tea CLI and API. Use when creating, updating, deleting, or bulk-managing labels.
---

# Tea Labels

Manage issue labels in Gitea/Forgejo repositories using the `tea` CLI.

## Common Commands

### List Labels

```bash
# List all labels
tea labels list

# Output as JSON
tea labels list --output json

# Save labels to file (for backup/transfer)
tea labels list --save
# Creates labels file in current directory

# Pagination
tea labels list --page 1 --limit 50
```

### Create Label

```bash
# Create with name and color
tea labels create --name "bug" --color "#d73a4a"

# With description
tea labels create --name "enhancement" --color "#a2eeef" --description "New feature or request"

# Create from file (bulk import)
tea labels create --file labels.csv
```

### Update Label

```bash
# Get label ID first
tea labels list --output json | jq '.[] | {id, name, color}'

# Update by ID
tea labels update --id 5 --name "bugfix" --color "#d73a4a"

# Update just the color
tea labels update --id 5 --color "#ff0000"

# Update description
tea labels update --id 5 --description "Updated description"
```

### Delete Label

```bash
# Delete by ID
tea labels delete 5
```

## Label Conventions

### Recommended Prefixes

Consistent prefixes make labels scannable and filterable.

```bash
# Type labels
tea labels create --name "type:bug" --color "#d73a4a" --description "Something isn't working"
tea labels create --name "type:feature" --color "#a2eeef" --description "New feature or request"
tea labels create --name "type:docs" --color "#0075ca" --description "Documentation improvements"
tea labels create --name "type:chore" --color "#e4e669" --description "Maintenance tasks"
tea labels create --name "type:refactor" --color "#d4c5f9" --description "Code restructuring"

# Priority labels
tea labels create --name "priority:critical" --color "#b60205" --description "Must fix immediately"
tea labels create --name "priority:high" --color "#d93f0b" --description "Fix before next release"
tea labels create --name "priority:medium" --color "#fbca04" --description "Fix when possible"
tea labels create --name "priority:low" --color "#0e8a16" --description "Nice to have"

# Status labels
tea labels create --name "status:blocked" --color "#000000" --description "Blocked by another issue"
tea labels create --name "status:in-progress" --color "#1d76db" --description "Actively being worked on"
tea labels create --name "status:needs-review" --color "#5319e7" --description "Waiting for review"
tea labels create --name "status:needs-triage" --color "#e99695" --description "Needs prioritization"

# Scope labels
tea labels create --name "scope:frontend" --color "#bfd4f2" --description "Frontend changes"
tea labels create --name "scope:backend" --color "#c2e0c6" --description "Backend changes"
tea labels create --name "scope:api" --color "#d4c5f9" --description "API changes"
tea labels create --name "scope:infra" --color "#f9d0c4" --description "Infrastructure changes"
```

### Apply Labels to Issues

```bash
# Add labels when creating an issue
tea issues create --title "Fix login" --labels "type:bug,priority:high"

# Add labels to existing issue
tea issues edit 42 --add-labels "status:in-progress"

# Remove labels
tea issues edit 42 --remove-labels "status:needs-triage"

# Bulk add label to issues
tea issues list --labels "type:bug" --state open --output json | \
  jq -r '.[].index' | xargs -I{} tea issues edit {} --add-labels "sprint:current"
```

## Bulk Operations

### Export Labels

```bash
# Export to JSON
tea labels list --output json > labels.json

# Export to CSV (name,color,description)
tea labels list --output json | \
  jq -r '.[] | [.name, .color, .description] | @csv' > labels.csv
```

### Import Labels

```bash
# From a saved labels file
tea labels create --file labels.csv

# From JSON (recreate in another repo)
cat labels.json | jq -r '.[] | "tea labels create --name \"\(.name)\" --color \"\(.color)\" --description \"\(.description // "")\""' | sh

# Copy labels from one repo to another
tea labels list -r owner/source-repo --output json | \
  jq -r '.[] | "tea labels create -r owner/target-repo --name \"\(.name)\" --color \"\(.color)\" --description \"\(.description // "")\""' | sh
```

### Delete All Labels

```bash
# Delete all labels (use with caution)
tea labels list --output json | jq -r '.[].id' | xargs -I{} tea labels delete {}
```

### Rename Label Prefix

```bash
# Rename all "kind:" labels to "type:"
tea labels list --output json | \
  jq -r '.[] | select(.name | startswith("kind:")) | "\(.id) \(.name)"' | \
  while read id name; do
    new_name=$(echo "$name" | sed 's/^kind:/type:/')
    tea labels update --id "$id" --name "$new_name"
  done
```

## API for Unsupported Features

```bash
# Setup
TOKEN=$(grep 'token:' ~/.config/tea/config.yml | head -1 | awk '{print $2}')
BASE_URL=$(grep 'url:' ~/.config/tea/config.yml | head -1 | awk '{print $2}')
OWNER=$(git remote get-url origin | sed -E 's|.*[:/]([^/]+)/([^/]+?)(\.git)?$|\1|')
REPO=$(git remote get-url origin | sed -E 's|.*[:/]([^/]+)/([^/]+?)(\.git)?$|\2|' | sed 's/\.git$//')
API="$BASE_URL/api/v1/repos/$OWNER/$REPO"
```

### Organization-Level Labels

```bash
ORG_API="$BASE_URL/api/v1/orgs/$OWNER"

# List org labels
curl -s "$ORG_API/labels" -H "Authorization: token $TOKEN" | jq '.[].name'

# Create org label (applies across all repos)
curl -s -X POST "$ORG_API/labels" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "org:team-a", "color": "#0052cc", "description": "Owned by Team A"}'
```

### Label Search by Name

```bash
# Find label ID by name
curl -s "$API/labels?name=type:bug" -H "Authorization: token $TOKEN" | jq '.[0].id'
```

### List Issues by Label via API

```bash
# More flexible than tea CLI filtering
curl -s "$API/issues?labels=type:bug,priority:high&state=open" \
  -H "Authorization: token $TOKEN" | jq '.[].number'
```

## Notes

- Labels are identified by name in `tea issues` commands, by ID in `tea labels update/delete`
- Colors should include the `#` prefix (e.g., `#d73a4a`)
- `tea labels list --save` exports labels in tea's internal format for `tea labels create --file`
- Label names are case-sensitive in Gitea/Forgejo
- Organization labels appear alongside repo-level labels but are managed separately
- Deleting a label removes it from all issues/PRs in that repo
