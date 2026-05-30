---
name: issue-moderation
description: Pin, react to, and lock/unlock Gitea/Forgejo issues via bundled actions.
user-invokable: true
---

# Issue Moderation

Features not available in the tea CLI. For exact bundled action commands and arguments, see `actions/issues/README.md`.

When resolving `actions/...` paths, use the `actions/` directory bundled relative to this skill directory.


Pass explicit scope flags (`--login`, `--remote`, or `--repo`) to bundled actions when the user names a login, remote, backend, or repository. Otherwise, bundled actions use active-host-first discovery.
