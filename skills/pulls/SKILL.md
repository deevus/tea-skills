---
name: pulls
description: Manage Gitea/Forgejo pull requests using the tea CLI and API. Use when creating, reviewing, merging, or managing PRs.
---

# Tea Pull Requests

Manage pull requests in Gitea/Forgejo repositories using the `tea` CLI.

## Common Commands

### List Pull Requests

```bash
# List open PRs (default)
tea pulls list

# List all PRs
tea pulls list --state all

# Output as JSON for scripting
tea pulls list --output json

# Custom fields
tea pulls list --fields "index,title,state,author,base,head,labels"

# Pagination
tea pulls list --page 1 --limit 20
```

### Show PR Detail

```bash
# Show PR by index
tea pulls 15

# Show with comments
tea pulls 15 --comments
```

### Create Pull Request

```bash
# From current branch to default branch (interactive)
tea pulls create

# Non-interactive with options
tea pulls create \
  --title "Add user authentication" \
  --description "Implements JWT-based auth" \
  --head "feature/auth" \
  --base "main"

# With metadata
tea pulls create \
  --title "Fix login bug" \
  --description "Resolves #42" \
  --labels "bugfix" \
  --assignees "sh" \
  --milestone "v1.0"

# From a fork (cross-repo PR)
tea pulls create --head "contributor:feature-branch" --base "main"

# Disable maintainer edits
tea pulls create --title "My PR" --allow-maintainer-edits=false
```

### Checkout and Review

```bash
# Checkout a PR locally
tea pulls checkout 15

# Interactive review
tea pulls review 15

# Approve
tea pulls approve 15

# Request changes
tea pulls reject 15
```

### Merge

```bash
# Default merge commit
tea pulls merge 15

# Squash merge
tea pulls merge 15 --style squash

# Rebase merge
tea pulls merge 15 --style rebase

# Rebase-merge (rebase + merge commit)
tea pulls merge 15 --style rebase-merge

# With custom commit message
tea pulls merge 15 --style squash --title "feat: add auth" --message "Implements JWT authentication"
```

### Close / Reopen / Clean

```bash
# Close PR without merging
tea pulls close 15

# Reopen closed PR
tea pulls reopen 15

# Clean up branches after merge
tea pulls clean 15
```

## Workflow Patterns

### Create PR from Current Branch

```bash
# Push current branch then create PR
git push -u origin HEAD
tea pulls create --title "$(git log -1 --format=%s)" --head "$(git branch --show-current)"
```

### Review Checklist Pattern

```bash
# List PRs needing review
tea pulls list --output json | jq '.[] | select(.labels | map(.name) | index("needs-review")) | {index, title, author: .poster.login}'

# Checkout, review, approve in sequence
tea pulls checkout 15
# ... test locally ...
tea pulls approve 15
tea pulls merge 15 --style squash
tea pulls clean 15
```

### Bulk Close Stale PRs

```bash
tea pulls list --state open --output json | \
  jq -r '.[] | select(.updated | fromdateiso8601 < (now - 90*86400)) | .index' | \
  xargs tea pulls close
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

### Draft PRs

The `tea` CLI doesn't support creating draft PRs. Use the API.

```bash
# Create draft PR
curl -s -X POST "$API/pulls" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "WIP: New feature",
    "body": "Work in progress",
    "head": "feature-branch",
    "base": "main",
    "draft": true
  }' | jq '{number: .number, title: .title, draft: .draft}'

# Mark draft as ready for review
curl -s -X PATCH "$API/pulls/15" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"draft": false}'
```

### Request Reviewers

```bash
# Request review from specific users
curl -s -X POST "$API/pulls/15/requested_reviewers" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reviewers": ["user1", "user2"]}'

# Remove review request
curl -s -X DELETE "$API/pulls/15/requested_reviewers" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reviewers": ["user1"]}'
```

### Auto-Merge

```bash
# Enable auto-merge (merges when all checks pass)
curl -s -X POST "$API/pulls/15/merge" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "Do": "squash",
    "merge_when_checks_succeed": true,
    "merge_message_field": "feat: add authentication"
  }'

# Cancel auto-merge
curl -s -X DELETE "$API/pulls/15/merge" \
  -H "Authorization: token $TOKEN"
```

### PR Diff and Patch

```bash
# Get diff
curl -s "$API/pulls/15.diff" -H "Authorization: token $TOKEN"

# Get patch
curl -s "$API/pulls/15.patch" -H "Authorization: token $TOKEN"

# List changed files
curl -s "$API/pulls/15/files" -H "Authorization: token $TOKEN" | jq '.[].filename'
```

### PR Reviews via API

```bash
# List reviews
curl -s "$API/pulls/15/reviews" -H "Authorization: token $TOKEN" | \
  jq '.[] | {id: .id, user: .user.login, state: .state, body: .body}'

# Submit review with comments
curl -s -X POST "$API/pulls/15/reviews" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "REQUEST_CHANGES",
    "body": "Please fix the issues noted in comments",
    "comments": [
      {
        "path": "src/auth.go",
        "new_position": 15,
        "body": "This should validate the token expiry"
      }
    ]
  }'
```

## Notes

- `tea pulls create` defaults to the current branch as `--head` and the repo's default branch as `--base`
- Merge styles: `merge` (merge commit), `squash` (single commit), `rebase` (linear history), `rebase-merge` (rebase + merge commit)
- `tea pulls clean` removes local and remote branches for a closed/merged PR
- `tea pulls checkout` creates a local branch tracking the PR's head
- Use `tea issues list --kind pulls` to search PRs with the same filters as issues (labels, milestones, etc.)
