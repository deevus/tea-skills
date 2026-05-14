---
name: review-pull
description: Review Gitea/Forgejo pull requests — checkout, approve, reject, request reviewers, inline comments, and diff/patch/files.
user-invokable: true
---

# Review Pull Request

Script paths in this skill follow the bundled-script convention: `scripts/<name>` means the script bundled with this plugin. Resolve it to the installed plugin path before executing from a project repo.

## Checkout and Review

```bash
tea pulls checkout 15      # checkout PR locally
tea pulls review 15        # interactive review
tea pulls approve 15       # approve
tea pulls reject 15        # request changes
```

## Request Reviewers (API)

```bash
scripts/tea-pr-reviewers add 15 "user1,user2"
scripts/tea-pr-reviewers remove 15 "user1"
```

## Diff / Patch / Files (API)

```bash
source scripts/tea-api
_api_get "pulls/15.diff"
_api_get "pulls/15.patch"
_api_get "pulls/15/files" | jq '.[].filename'
```

## Reviews with Inline Comments (API)

```bash
source scripts/tea-api
_api_post "pulls/15/reviews" '{
  "event": "REQUEST_CHANGES",
  "body": "Please fix the noted issues",
  "comments": [{"path": "src/auth.go", "new_position": 15, "body": "Validate token expiry"}]
}'
```

## Review Checklist Pattern

```bash
tea pulls checkout 15
# ... test locally ...
tea pulls approve 15
tea pulls merge 15 --style squash
tea pulls clean 15
```

## Tips

- `tea pulls checkout` creates a local tracking branch
