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

## Find pull requests by branch

Use the lookup action after creating a pull request when an agent needs structured PR data for follow-up steps:

```bash
actions/pull-requests/find-by-branch.py
actions/pull-requests/find-by-branch.py --head feature-branch
actions/pull-requests/find-by-branch.py --head contributor:feature-branch --base main
actions/pull-requests/find-by-branch.py --head feature-branch --state all
```

With no `--head`, the action uses the current git branch. `--head branch` matches the pull request head branch, while `--head owner:branch` matches fork-style head labels exactly. `--base` accepts only a branch name. `--state` accepts `open`, `closed`, or `all` and defaults to `open`.

Output is newline-delimited JSON on stdout, with one pull request object per matching PR and no prose:

```jsonl
{"number":12,"url":"https://forge.example/owner/repo/pulls/12","title":"Feature","state":"open","head":{"owner":"owner","branch":"feature"},"base":{"owner":"owner","branch":"main"}}
```

No matches, missing branch context, invalid arguments, configuration errors, repository-context errors, and API errors are emitted as JSONL error records on stderr with a non-zero exit code.


## Set auto-merge

```bash
actions/pull-requests/set-automerge.py <pr> --enable [--style squash|merge|rebase] [--message "message"]
actions/pull-requests/set-automerge.py <pr> --cancel
```

This configures auto-merge. It does not merge the pull request immediately.
