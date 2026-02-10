---
name: issues
description: Manage Gitea/Forgejo issues using the tea CLI and API. Use when creating, editing, listing, closing, or bulk-operating on issues.
---

# Tea Issues

Manage issues in Gitea/Forgejo repositories using the `tea` CLI.

## Setup

```bash
# Ensure tea is configured
tea login list

# Verify repo context (run from a git repo with a Forgejo/Gitea remote)
tea issues list --limit 1
```

## Common Commands

### List Issues

```bash
# List open issues (default)
tea issues list

# List all issues including closed
tea issues list --state all

# Filter by label
tea issues list --labels "bug"
tea issues list --labels "bug,critical"

# Filter by milestone
tea issues list --milestones "v1.0"

# Filter by assignee
tea issues list --assignee "username"

# Filter by author
tea issues list --author "username"

# Filter by date range
tea issues list --from "2025-01-01" --until "2025-06-01"

# Search by keyword
tea issues list --keyword "authentication"

# Combine filters
tea issues list --state open --labels "bug" --assignee "sh" --milestones "v1.0"

# Control output format
tea issues list --output json
tea issues list --output yaml
tea issues list --output csv
tea issues list --output simple    # just index and title

# Custom fields
tea issues list --fields "index,title,state,labels,assignees"

# Pagination
tea issues list --page 2 --limit 50
```

### Show Issue Detail

```bash
# Show issue by index
tea issues 42

# Show with comments
tea issues 42 --comments
```

### Create Issue

```bash
# Interactive (prompts for title/description)
tea issues create

# Non-interactive
tea issues create --title "Fix login bug" --description "Login fails on mobile"

# With metadata
tea issues create \
  --title "Fix login bug" \
  --description "Login fails on mobile browsers" \
  --labels "bug,frontend" \
  --assignees "sh" \
  --milestone "v1.0" \
  --deadline "2025-03-01"
```

### Edit Issue

```bash
# Edit title
tea issues edit 42 --title "Updated title"

# Add labels
tea issues edit 42 --add-labels "priority:high"

# Remove labels
tea issues edit 42 --remove-labels "needs-triage"

# Change milestone
tea issues edit 42 --milestone "v2.0"

# Clear milestone
tea issues edit 42 --milestone ""

# Add assignees
tea issues edit 42 --add-assignees "user1,user2"

# Set deadline
tea issues edit 42 --deadline "2025-06-01"

# Edit multiple issues at once
tea issues edit 1 2 3 --add-labels "sprint-5"
```

### Close / Reopen

```bash
# Close one issue
tea issues close 42

# Close multiple
tea issues close 1 2 3

# Reopen
tea issues reopen 42
```

## Bulk Operations

```bash
# Close all issues with a label
tea issues list --labels "wontfix" --output json | jq -r '.[].index' | xargs tea issues close

# Add label to all open issues in a milestone
tea issues list --milestones "v1.0" --output json | jq -r '.[].index' | xargs -I{} tea issues edit {} --add-labels "release:v1.0"

# Export issues to JSON
tea issues list --state all --output json > issues-backup.json

# List all issue indices
tea issues list --output simple | awk '{print $1}'

# Count issues by state
echo "Open: $(tea issues list --state open --output json | jq length)"
echo "Closed: $(tea issues list --state closed --output json | jq length)"
```

## API for Unsupported Features

Some features aren't available in `tea` CLI. Use the API directly.

```bash
# Setup
TOKEN=$(grep 'token:' ~/.config/tea/config.yml | head -1 | awk '{print $2}')
BASE_URL=$(grep 'url:' ~/.config/tea/config.yml | head -1 | awk '{print $2}')
OWNER=$(git remote get-url origin | sed -E 's|.*[:/]([^/]+)/([^/]+?)(\.git)?$|\1|')
REPO=$(git remote get-url origin | sed -E 's|.*[:/]([^/]+)/([^/]+?)(\.git)?$|\2|' | sed 's/\.git$//')
API="$BASE_URL/api/v1/repos/$OWNER/$REPO"
```

### Pin / Unpin Issue

```bash
# Pin issue
curl -s -X POST "$API/issues/42/pin" -H "Authorization: token $TOKEN"

# Unpin issue
curl -s -X DELETE "$API/issues/42/pin" -H "Authorization: token $TOKEN"
```

### Reactions

```bash
# Add reaction to issue
curl -s -X POST "$API/issues/42/reactions" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "+1"}'
# Available: +1, -1, laugh, confused, heart, hooray, rocket, eyes

# List reactions
curl -s "$API/issues/42/reactions" -H "Authorization: token $TOKEN" | jq '.[] | {user: .user.login, content: .content}'
```

### Lock / Unlock Issue

```bash
# Lock
curl -s -X POST "$API/issues/42/lock" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"lock_reason": "resolved"}'

# Unlock
curl -s -X DELETE "$API/issues/42/lock" -H "Authorization: token $TOKEN"
```

### Issue Comments via API

```bash
# Add comment
curl -s -X POST "$API/issues/42/comments" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"body": "This is a comment"}'

# List comments
curl -s "$API/issues/42/comments" -H "Authorization: token $TOKEN" | jq '.[] | {id: .id, user: .user.login, body: .body}'

# Edit comment
curl -s -X PATCH "$API/issues/comments/123" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"body": "Updated comment"}'
```

### Issue Templates

```bash
# List available issue templates
curl -s "$API/issue_templates" -H "Authorization: token $TOKEN" | jq '.[].name'
```

## Notes

- `tea issues list` defaults to open issues; use `--state all` for everything
- The `--kind` flag can be `issues`, `pulls`, or `all` to search across types
- `--output json` is essential for scripting and piping to `jq`
- Multiple issues can be closed/reopened/edited in a single command
- `tea issues edit` with `--add-labels` and `--remove-labels` are additive/subtractive; they don't replace existing labels
