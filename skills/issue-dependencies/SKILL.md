---
name: issue-dependencies
description: Manage Gitea/Forgejo issue dependencies — add, remove, list, find ready issues, and visualize dependency graphs.
user-invokable: true
---

# Issue Dependencies

"A depends on B" means B must be done first. B *blocks* A. The tea CLI has no dependency support. For bundled actions and exact arguments, see `actions/issues/README.md`.

When resolving `actions/...` paths, use the `actions/` directory bundled relative to this skill directory.


Pass explicit scope flags (`--login`, `--remote`, or `--repo`) to bundled actions when the user names a login, remote, backend, or repository. Otherwise, bundled actions use active-host-first discovery.

Cross-repo dependencies are not supported by the bundled actions in this version.
