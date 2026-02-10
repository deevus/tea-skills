# Pulls API

For features not available in `tea` CLI. See `_api-setup.md` for credentials setup.

## Draft PRs

```bash
# Create draft
curl -s -X POST "$API/pulls" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "WIP: Feature", "body": "Work in progress", "head": "feature-branch", "base": "main", "draft": true}'

# Mark ready
curl -s -X PATCH "$API/pulls/15" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"draft": false}'
```

## Request Reviewers

```bash
curl -s -X POST "$API/pulls/15/requested_reviewers" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reviewers": ["user1", "user2"]}'

# Remove
curl -s -X DELETE "$API/pulls/15/requested_reviewers" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reviewers": ["user1"]}'
```

## Auto-Merge

```bash
# Enable (merges when checks pass)
curl -s -X POST "$API/pulls/15/merge" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"Do": "squash", "merge_when_checks_succeed": true, "merge_message_field": "feat: add auth"}'

# Cancel
curl -s -X DELETE "$API/pulls/15/merge" -H "Authorization: token $TOKEN"
```

## Diff / Patch / Files

```bash
curl -s "$API/pulls/15.diff" -H "Authorization: token $TOKEN"
curl -s "$API/pulls/15.patch" -H "Authorization: token $TOKEN"
curl -s "$API/pulls/15/files" -H "Authorization: token $TOKEN" | jq '.[].filename'
```

## Reviews with Inline Comments

```bash
curl -s -X POST "$API/pulls/15/reviews" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "REQUEST_CHANGES",
    "body": "Please fix the noted issues",
    "comments": [{"path": "src/auth.go", "new_position": 15, "body": "Validate token expiry"}]
  }'
```
