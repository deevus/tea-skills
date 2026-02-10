---
name: milestones
description: Manage Gitea/Forgejo milestones using the tea CLI and API. Use when creating, closing, tracking, or assigning issues to milestones.
---

# Tea Milestones

Manage milestones in Gitea/Forgejo repositories using the `tea` CLI.

## Common Commands

### List Milestones

```bash
# List open milestones (default)
tea milestones list

# List all milestones
tea milestones list --state all

# List closed milestones
tea milestones list --state closed

# Custom fields
tea milestones list --fields "title,state,items_open,items_closed,duedate,description"

# Output as JSON
tea milestones list --output json

# Pagination
tea milestones list --page 1 --limit 50
```

### Show Milestone Detail

```bash
# Show by name
tea milestones "v1.0"
```

### Create Milestone

```bash
# Interactive
tea milestones create

# Non-interactive
tea milestones create --title "v1.0" --description "First stable release"

# With deadline
tea milestones create --title "v1.0" --deadline "2025-06-01"

# Create as closed
tea milestones create --title "v0.9" --state closed
```

### Close / Reopen / Delete

```bash
# Close milestone
tea milestones close "v1.0"

# Close multiple
tea milestones close "v0.8" "v0.9"

# Reopen
tea milestones reopen "v1.0"

# Delete
tea milestones delete "v1.0"
```

### Manage Issues in Milestones

```bash
# List issues in a milestone
tea milestones issues "v1.0"

# Filter by state
tea milestones issues "v1.0" --state all
tea milestones issues "v1.0" --state closed

# Filter by kind (issues or pulls)
tea milestones issues "v1.0" --kind issue
tea milestones issues "v1.0" --kind pull

# Custom fields
tea milestones issues "v1.0" --fields "index,title,state,assignees,labels"

# Add issue to milestone
tea milestones issues add "v1.0" 42

# Remove issue from milestone
tea milestones issues remove "v1.0" 42
```

## Workflow Patterns

### Progress Tracking

```bash
# Show milestone progress as JSON
tea milestones list --output json | jq '.[] | {
  title,
  open: .open_issues,
  closed: .closed_issues,
  total: (.open_issues + .closed_issues),
  progress: (if (.open_issues + .closed_issues) > 0
    then ((.closed_issues * 100) / (.open_issues + .closed_issues) | round | tostring) + "%"
    else "0%" end)
}'
```

### Bulk Assign Issues to Milestone

```bash
# Assign all issues with a label to a milestone
tea issues list --labels "release:v1.0" --output json | \
  jq -r '.[].index' | \
  xargs -I{} tea milestones issues add "v1.0" {}

# Assign a range of issues
for i in $(seq 10 20); do
  tea milestones issues add "v1.0" $i
done
```

### Milestone Burndown

```bash
# Count open vs closed per milestone
for ms in $(tea milestones list --output json | jq -r '.[].title'); do
  open=$(tea milestones issues "$ms" --state open --output json | jq length)
  closed=$(tea milestones issues "$ms" --state closed --output json | jq length)
  echo "$ms: $closed done, $open remaining"
done
```

### Move Issues Between Milestones

```bash
# Move all open issues from v1.0 to v1.1
tea milestones issues "v1.0" --state open --output json | \
  jq -r '.[].index' | while read idx; do
    tea milestones issues remove "v1.0" $idx
    tea milestones issues add "v1.1" $idx
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

### Edit Milestone

The `tea` CLI doesn't have a milestone edit command. Use the API.

```bash
# Get milestone ID by title
MS_ID=$(curl -s "$API/milestones?name=v1.0" -H "Authorization: token $TOKEN" | jq '.[0].id')

# Update title
curl -s -X PATCH "$API/milestones/$MS_ID" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "v1.0.0"}'

# Update deadline
curl -s -X PATCH "$API/milestones/$MS_ID" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"due_on": "2025-06-15T00:00:00Z"}'

# Update description
curl -s -X PATCH "$API/milestones/$MS_ID" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"description": "Updated release notes"}'
```

### Assign Issue to Milestone via API

An alternative to `tea milestones issues add` — useful when you have the milestone ID.

```bash
# Get milestone ID
MS_ID=$(curl -s "$API/milestones?name=v1.0" -H "Authorization: token $TOKEN" | jq '.[0].id')

# Assign issue #42 to milestone
curl -s -X PATCH "$API/issues/42" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"milestone\": $MS_ID}"

# Remove issue from milestone
curl -s -X PATCH "$API/issues/42" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"milestone": 0}'
```

## Notes

- Milestones are identified by name in `tea` commands, by ID in the API
- `tea milestones issues add/remove` uses the issue index number
- Deadlines accept date strings like `2025-06-01`; the API expects ISO 8601
- Progress is calculated from open/closed issue counts
- Deleting a milestone does not close or delete its issues — they become unassigned
