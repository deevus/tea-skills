# Pulls API

Features not available in `tea` CLI. Use scripts from `scripts/`.

## Draft PRs

```bash
scripts/tea-pr-draft create "WIP: Feature" feature-branch         # draft to main
scripts/tea-pr-draft create "WIP: Feature" feature-branch develop  # draft to develop
scripts/tea-pr-draft ready 15                                      # mark ready
```

## Request Reviewers

```bash
scripts/tea-pr-reviewers add 15 "user1,user2"
scripts/tea-pr-reviewers remove 15 "user1"
```

## Auto-Merge

```bash
scripts/tea-pr-automerge enable 15                          # squash (default)
scripts/tea-pr-automerge enable 15 merge                    # merge commit
scripts/tea-pr-automerge enable 15 squash "feat: add auth"  # with message
scripts/tea-pr-automerge cancel 15
```

## Diff / Patch / Files

These are lightweight enough to use inline via `scripts/tea-api`.

```bash
source scripts/tea-api
_api_get "pulls/15.diff"
_api_get "pulls/15.patch"
_api_get "pulls/15/files" | jq '.[].filename'
```

## Reviews with Inline Comments

Complex reviews use the API helpers from `scripts/tea-api`.

```bash
source scripts/tea-api
_api_post "pulls/15/reviews" '{
  "event": "REQUEST_CHANGES",
  "body": "Please fix the noted issues",
  "comments": [{"path": "src/auth.go", "new_position": 15, "body": "Validate token expiry"}]
}'
```
