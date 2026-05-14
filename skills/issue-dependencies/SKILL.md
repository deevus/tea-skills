---
name: issue-dependencies
description: Manage Gitea/Forgejo issue dependencies — add, remove, list, find ready issues, and visualize dependency graphs.
user-invokable: true
---

# Issue Dependencies

"A depends on B" means B must be done first. B *blocks* A. The tea CLI has no dependency support. For bundled actions and exact arguments, see `actions/issues/README.md`.

Cross-repo dependencies are not supported by the bundled actions in this version.
