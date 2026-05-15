# Internal action support

Internal Python Modules support bundled actions. They are not user-facing command Interfaces.

Responsibilities:

- `tea_api.py` discovers tea config, sends authenticated Gitea/Forgejo HTTP requests, translates transport errors, and records action audit events
- `repo_scope.py` derives repo-scoped Forgejo API access from `git remote get-url origin`
- `org_scope.py` derives organization-scoped Forgejo API access from the current repository owner
- domain Modules (`issues.py`, `pulls.py`, `milestones.py`, `org_labels.py`) expose domain operations for action executables

Users and agents should use documented commands in the domain README files instead of importing this Module directly.
