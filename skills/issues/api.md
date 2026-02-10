# Issues API

Features not available in `tea` CLI. Use scripts from `scripts/`.

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

## Comments

```bash
scripts/tea-issue-comment add 42 "This is a comment"
scripts/tea-issue-comment list 42
scripts/tea-issue-comment edit 123 "Updated comment"
```
