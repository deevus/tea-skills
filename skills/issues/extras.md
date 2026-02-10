# Issues Extras

## Cross-Repo Dependencies

The `tea-dep` script works within the current repo. For cross-repo dependencies, use the API helpers directly:

```bash
source scripts/tea-api
_api_post "issues/10/dependencies" '{"index": 5, "owner": "other-owner", "repo": "other-repo"}'
```

## Bulk Operations

```bash
# Close all issues with a label
tea issues list --labels "wontfix" --output json | jq -r '.[].index' | xargs tea issues close

# Add label to all open issues in a milestone
tea issues list --milestones "v1.0" --output json | jq -r '.[].index' | xargs -I{} tea issues edit {} --add-labels "release:v1.0"

# Export all issues to JSON
tea issues list --state all --output json > issues-backup.json

# Count by state
echo "Open: $(tea issues list --state open --output json | jq length)"
echo "Closed: $(tea issues list --state closed --output json | jq length)"
```
