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

When resolving `actions/...` paths, use the `actions/` directory bundled relative to this skill directory.


Pass explicit scope flags (`--login`, `--remote`, or `--repo`) to bundled actions when the user names a login, remote, backend, or repository. Otherwise, bundled actions use active-host-first discovery.

The comment ID can be found in the JSON output of `tea issues <num> --comments` or via Forgejo/Gitea UI/API details.
