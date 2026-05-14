---
name: create-pull
description: Create Gitea/Forgejo pull requests — interactive, with flags, from forks, draft PRs, and quick patterns.
user-invokable: true
---

# Create Pull Request

Script paths in this skill follow the bundled-script convention: `scripts/<name>` means the script bundled with this plugin. Resolve it to the installed plugin path before executing from a project repo.

## Create

```bash
tea pulls create           # interactive, current branch -> default branch
tea pulls create --title "Add auth" --description "Implements JWT" \
  --head "feature/auth" --base "main" \
  --labels "bugfix" --assignees "sh" --milestone "v1.0"
tea pulls create --head "contributor:feature-branch" --base "main"  # from fork
```

## Draft PR (API)

```bash
scripts/tea-pr-draft create "WIP: Feature" feature-branch         # draft to main
scripts/tea-pr-draft create "WIP: Feature" feature-branch develop  # draft to develop
```

## Quick Pattern

```bash
# PR from current branch
git push -u origin HEAD
tea pulls create --title "$(git log -1 --format=%s)" --head "$(git branch --show-current)"
```
