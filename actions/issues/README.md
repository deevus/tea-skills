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

## Comment edit

```bash
actions/issues/comment-edit <comment-id> <body>
```

Edits an existing issue comment. Add and list comments with `tea comment` and `tea issues <issue> --comments`.

## Locking

```bash
actions/issues/lock <issue> [reason]
actions/issues/unlock <issue>
```

Default lock reason is `resolved`.

## Pinning

```bash
actions/issues/pin <issue>
actions/issues/unpin <issue>
```

## Reactions

```bash
actions/issues/reaction-add <issue> <reaction>
actions/issues/reaction-list <issue>
```

Common reactions: `+1`, `-1`, `laugh`, `confused`, `heart`, `hooray`, `rocket`, `eyes`.

## Dependencies

“A depends on B” means B blocks A.

```bash
actions/issues/dependency-add <issue> <depends-on>
actions/issues/dependency-remove <issue> <depends-on>
actions/issues/dependency-list <issue>
actions/issues/dependency-all
actions/issues/dependency-ready
actions/issues/dependency-graph
```
