---
name: issue-moderation
description: Pin, react to, and lock/unlock Gitea/Forgejo issues via API scripts.
user-invokable: true
---

# Issue Moderation

Features not available in the tea CLI. Use scripts from `scripts/`.

## Pin / Unpin

```bash
scripts/tea-issue-pin pin 42
scripts/tea-issue-pin unpin 42
```

## Reactions

```bash
# Add: +1, -1, laugh, confused, heart, hooray, rocket, eyes
scripts/tea-issue-react add 42 "+1"

# List
scripts/tea-issue-react list 42
```

## Lock / Unlock

```bash
scripts/tea-issue-lock lock 42           # default reason: resolved
scripts/tea-issue-lock lock 42 "spam"    # custom reason
scripts/tea-issue-lock unlock 42
```
