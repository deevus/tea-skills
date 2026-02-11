---
name: issue-comments
description: Add, list, and edit comments on Gitea/Forgejo issues.
user-invokable: true
---

# Issue Comments

## Add Comment

```bash
tea comment 42 "This is a comment"
```

## List Comments

```bash
tea issues 42 --comments
```

## Edit Comment (API)

The tea CLI can't edit comments. Use the API script:

```bash
scripts/tea-issue-comment edit 123 "Updated text"
```

The comment ID (123) can be found in the JSON output of `tea issues <num> --comments` or via the API.
