# Issue actions

Prefer the `tea` CLI for normal issue workflows:

```bash
tea issues list -o simple
tea issues 42 --comments
tea issues create --title "Fix login" --description "Details"
tea issues edit 42 --title "New title"
tea issues close 42
tea issues reopen 42
tea comment 42 "This is a comment"
```

Use bundled actions only for Gitea/Forgejo issue features that `tea` does not expose cleanly.

## Repository targeting

Issue actions use active-host-first discovery by default. Pass explicit scope flags when the user names a login, remote, backend, or repository:

```bash
actions/issues/dependency-ready.py --login codeberg --repo owner/project
actions/issues/pin.py --remote upstream 42
actions/issues/comment-edit.py --login forgejo-prod --repo team/service 1234 "Updated comment"
```

Use `--login` for an exact `tea` login, `--remote` for owner/repo from a git remote, and `--repo` for an explicit `owner/repo` slug.


## Comment edit

```bash
actions/issues/comment-edit.py <comment-id> <body>
```

Edits an existing issue comment. Add and list comments with `tea comment` and `tea issues <issue> --comments`.

## Locking

```bash
actions/issues/lock.py <issue> [reason]
actions/issues/unlock.py <issue>
```

Default lock reason is `resolved`.

## Pinning

```bash
actions/issues/pin.py <issue>
actions/issues/unpin.py <issue>
```

## Reactions

```bash
actions/issues/reaction-add.py <issue> <reaction>
actions/issues/reaction-list.py <issue>
```

Common reactions: `+1`, `-1`, `laugh`, `confused`, `heart`, `hooray`, `rocket`, `eyes`.

## Dependencies

“A depends on B” means B blocks A.

```bash
actions/issues/dependency-add.py <issue> <depends-on>
actions/issues/dependency-remove.py <issue> <depends-on>
actions/issues/dependency-list.py <issue>
actions/issues/dependency-all.py
actions/issues/dependency-ready.py
actions/issues/dependency-graph.py
```
