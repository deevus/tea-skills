# Issues API

For features not available in `tea` CLI. See `_api-setup.md` for credentials setup.

## Pin / Unpin

```bash
curl -s -X POST "$API/issues/42/pin" -H "Authorization: token $TOKEN"
curl -s -X DELETE "$API/issues/42/pin" -H "Authorization: token $TOKEN"
```

## Reactions

```bash
# Add: +1, -1, laugh, confused, heart, hooray, rocket, eyes
curl -s -X POST "$API/issues/42/reactions" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "+1"}'

# List
curl -s "$API/issues/42/reactions" -H "Authorization: token $TOKEN" | jq '.[] | {user: .user.login, content: .content}'
```

## Lock / Unlock

```bash
curl -s -X POST "$API/issues/42/lock" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"lock_reason": "resolved"}'

curl -s -X DELETE "$API/issues/42/lock" -H "Authorization: token $TOKEN"
```

## Comments

```bash
# Add
curl -s -X POST "$API/issues/42/comments" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"body": "This is a comment"}'

# List
curl -s "$API/issues/42/comments" -H "Authorization: token $TOKEN" | jq '.[] | {id, user: .user.login, body}'

# Edit
curl -s -X PATCH "$API/issues/comments/123" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"body": "Updated comment"}'
```

## Issue Templates

```bash
curl -s "$API/issue_templates" -H "Authorization: token $TOKEN" | jq '.[].name'
```
