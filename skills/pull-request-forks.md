# Fork and Upstream Pull Requests

## Rule

A fork-originated pull request belongs to the upstream/base repository where it was opened, not to the fork repository checkout. Commands that inspect, review, or comment on that PR must target the upstream repository.

Use `--repo UPSTREAM_OWNER/UPSTREAM_REPO` for the upstream/base repository. If the current checkout's remote identifies the Forgejo server, `tea` can usually infer the login. If not, also pass `--login LOGIN_NAME`.

## Common Commands

Find upstream PRs authored by a fork owner/user:

```bash
tea issues list --kind pulls --author USER --repo UPSTREAM_OWNER/UPSTREAM_REPO -o simple
tea issues list --kind pulls --author USER --login LOGIN_NAME --repo UPSTREAM_OWNER/UPSTREAM_REPO -o simple
```

Show PR conversation comments and review comments on the upstream PR:

```bash
tea pulls PR_NUMBER --repo UPSTREAM_OWNER/UPSTREAM_REPO --comments
tea pulls review-comments PR_NUMBER --repo UPSTREAM_OWNER/UPSTREAM_REPO
tea pulls review-comments PR_NUMBER --login LOGIN_NAME --repo UPSTREAM_OWNER/UPSTREAM_REPO
```

## Agent Check

If `tea pulls list` in a fork checkout shows no relevant PRs, do not stop there. Identify the upstream/base repository from the user request, local remotes, or PR URL, then retry against that repository with `--repo`.
