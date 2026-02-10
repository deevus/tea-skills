# Issue Dependencies Extras

All dependency operations are handled by `scripts/tea-dep`. See that script for implementation details.

## Cross-Repo Dependencies

The `tea-dep` script works within the current repo. For cross-repo dependencies, use the API helpers directly:

```bash
source scripts/tea-api
_api_post "issues/10/dependencies" '{"index": 5, "owner": "other-owner", "repo": "other-repo"}'
```

## Shell Aliases

For convenience, add to `~/.zshrc`:

```bash
alias tea-dep='/path/to/tea-skills/scripts/tea-dep'
```

Then use without path prefix:

```bash
tea-dep add 25 26
tea-dep list 25
tea-dep ready
tea-dep graph
```
