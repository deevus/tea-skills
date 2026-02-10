---
name: pulls
description: Manage Gitea/Forgejo pull requests using the tea CLI. Use when creating, reviewing, merging, or managing PRs.
---

# Tea Pull Requests

## List

```bash
tea pulls list -o simple           # open PRs, compact output (recommended)
tea pulls list --state all -o simple  # include closed/merged
tea pulls list --output json       # use json only when parsing with jq
tea pulls list --fields "index,title,state,author,base,head,labels"
```

## Show

```bash
tea pulls 15              # detail view
tea pulls 15 --comments   # with comments
```

## Create

```bash
tea pulls create           # interactive, current branch → default branch
tea pulls create --title "Add auth" --description "Implements JWT" \
  --head "feature/auth" --base "main" \
  --labels "bugfix" --assignees "sh" --milestone "v1.0"
tea pulls create --head "contributor:feature-branch" --base "main"  # from fork
```

## Review

```bash
tea pulls checkout 15      # checkout PR locally
tea pulls review 15        # interactive review
tea pulls approve 15       # approve
tea pulls reject 15        # request changes
```

## Merge

```bash
tea pulls merge 15                      # merge commit (default)
tea pulls merge 15 --style squash       # squash
tea pulls merge 15 --style rebase       # rebase
tea pulls merge 15 --style rebase-merge # rebase + merge commit
tea pulls merge 15 --style squash --title "feat: add auth" --message "Details"
```

## Close / Reopen / Clean

```bash
tea pulls close 15         # close without merging
tea pulls reopen 15
tea pulls clean 15         # delete local + remote branches after merge
```

## Quick Patterns

```bash
# PR from current branch
git push -u origin HEAD
tea pulls create --title "$(git log -1 --format=%s)" --head "$(git branch --show-current)"
```

## Tips

- `tea issues list --kind pulls` searches PRs with all issue filters (labels, milestones, etc.)
- Merge styles: `merge`, `squash`, `rebase`, `rebase-merge`
- `tea pulls checkout` creates a local tracking branch

For draft PRs, reviewers, auto-merge, and review comments via API, see `api.md` — backed by scripts in `scripts/`.
