---
name: issue-dependencies
description: Manage Gitea/Forgejo issue dependencies via API. Use when adding, removing, or listing dependency relationships between issues.
---

# Tea Issue Dependencies

The `tea` CLI doesn't support dependencies. Use the API directly. See `_api-setup.md` for credentials.

## Terminology

- **"A depends on B"** → B must be done first. B *blocks* A.
- API: POST to `issues/A/dependencies` with B's index = "A depends on B".

## Add / Remove / List

```bash
# List what blocks #25
curl -s "$API/issues/25/dependencies" \
  -H "Authorization: token $TOKEN" | jq '.[] | {number, title, state}'

# Make #25 depend on #26
curl -s -X POST "$API/issues/25/dependencies" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"index": 26, "owner": "'"$OWNER"'", "repo": "'"$REPO"'"}'

# Remove dependency
curl -s -X DELETE "$API/issues/25/dependencies" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"index": 26, "owner": "'"$OWNER"'", "repo": "'"$REPO"'"}'

# Cross-repo: #10 here depends on #5 in another-repo
curl -s -X POST "$API/issues/10/dependencies" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"index": 5, "owner": "other-owner", "repo": "other-repo"}'
```

## Tips

- Dependencies appear in Forgejo web UI on each issue
- Cross-repo dependencies supported via owner/repo in JSON body
- If API calls fail with 401, refresh token with `tea login`

For shell helper functions (tea-dep-add, tea-dep-list, tea-dep-ready, tea-dep-graph), see `extras.md`.
