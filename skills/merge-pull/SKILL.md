---
name: merge-pull
description: Merge Gitea/Forgejo pull requests — all merge styles, auto-merge, mark draft ready, and branch cleanup.
user-invokable: true
---

# Merge Pull Request

## Merge

```bash
tea pulls merge 15                      # merge commit (default)
tea pulls merge 15 --style squash       # squash
tea pulls merge 15 --style rebase       # rebase
tea pulls merge 15 --style rebase-merge # rebase + merge commit
tea pulls merge 15 --style squash --title "feat: add auth" --message "Details"
```

## Auto-Merge (API)

```bash
scripts/tea-pr-automerge enable 15                          # squash (default)
scripts/tea-pr-automerge enable 15 merge                    # merge commit
scripts/tea-pr-automerge enable 15 squash "feat: add auth"  # with message
scripts/tea-pr-automerge cancel 15
```

## Mark Draft Ready (API)

```bash
scripts/tea-pr-draft ready 15
```

## Branch Cleanup

```bash
tea pulls clean 15         # delete local + remote branches after merge
```

## Tips

- Merge styles: `merge`, `squash`, `rebase`, `rebase-merge`
