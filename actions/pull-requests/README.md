# Pull request actions

Prefer the `tea` CLI for normal pull request workflows:

```bash
tea pulls create --title "WIP: Feature" --head feature-branch
tea pulls edit 15 --title "Feature"
tea pulls edit 15 --add-reviewers user1,user2
tea pulls edit 15 --remove-reviewers user1
tea pulls review 15
tea pulls approve 15 "Looks good"
tea pulls reject 15 "Please fix the failing test"
tea pulls merge 15 --style squash
tea pulls review-comments 15
tea pulls resolve 123
tea pulls unresolve 123
```

Use bundled actions only for pull request features that `tea` does not expose cleanly.

## Set auto-merge

```bash
actions/pull-requests/set-automerge <pr> --enable [--style squash|merge|rebase] [--message "message"]
actions/pull-requests/set-automerge <pr> --cancel
```

This configures auto-merge. It does not merge the pull request immediately.
