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

## Edit Comment

The tea CLI can't edit comments. For the bundled action, see `actions/issues/README.md`.

The comment ID can be found in the JSON output of `tea issues <num> --comments` or via Forgejo/Gitea UI/API details.
