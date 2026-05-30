---
name: review-pull
description: Review Gitea/Forgejo pull requests — checkout, approve, reject, request reviewers, inline comments, and diff/patch/files.
user-invokable: true
---

# Review Pull Request

Prefer `tea pulls` commands for review workflows. Bundled actions are only for CLI gaps and are documented under `actions/pull-requests/README.md`.

When resolving `actions/...` paths, use the `actions/` directory bundled relative to this skill directory.


Pass explicit scope flags (`--login`, `--remote`, or `--repo`) to bundled actions when the user names a login, remote, backend, or repository. Otherwise, bundled actions use active-host-first discovery.

## Checkout and Review

```bash
tea pulls checkout 15      # checkout PR locally
tea pulls review 15        # interactive review
tea pulls approve 15       # approve
tea pulls reject 15        # request changes
```

## Request Reviewers

```bash
tea pulls edit 15 --add-reviewers user1,user2
tea pulls edit 15 --remove-reviewers user1
```

## Diff / Patch / Review Comments

```bash
tea pulls 15 --fields diff,patch
tea pulls review-comments 15
tea pulls resolve 123
tea pulls unresolve 123
```

## Forks and Upstream PRs

See [pull-request-forks](pull-request-forks.md).

For interactive inline review, use:

```bash
tea pulls review 15
```

## Review Checklist Pattern

```bash
tea pulls checkout 15
# ... test locally ...
tea pulls approve 15
tea pulls merge 15 --style squash
tea pulls clean 15
```

## Tips

- `tea pulls checkout` creates a local tracking branch
