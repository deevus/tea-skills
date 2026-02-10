---
name: issue-dependencies
description: Manage Gitea/Forgejo issue dependencies via API. Use when adding, removing, listing, or visualizing issue dependency chains.
---

# Tea Issue Dependencies

The `tea` CLI doesn't support issue dependencies natively. Use the Forgejo/Gitea API directly.

## Setup

```bash
# Extract config from tea
TOKEN=$(grep 'token:' ~/.config/tea/config.yml | head -1 | awk '{print $2}')
BASE_URL=$(grep 'url:' ~/.config/tea/config.yml | head -1 | awk '{print $2}')
OWNER=$(git remote get-url origin | sed -E 's|.*[:/]([^/]+)/([^/]+?)(\.git)?$|\1|')
REPO=$(git remote get-url origin | sed -E 's|.*[:/]([^/]+)/([^/]+?)(\.git)?$|\2|' | sed 's/\.git$//')
API="$BASE_URL/api/v1/repos/$OWNER/$REPO"
```

## Terminology

- **"A depends on B"** means B must be done before A. B *blocks* A.
- **"A is blocked by B"** is the same relationship from A's perspective.
- In the API: posting to issue A's `/dependencies` with B's index means "A depends on B".

## API Endpoints

### List Dependencies

```bash
# What does issue #25 depend on? (what blocks #25)
curl -s "$API/issues/25/dependencies" \
  -H "Authorization: token $TOKEN" | jq '.[] | {number, title, state}'
```

### Add Dependency

```bash
# Make issue #25 depend on issue #26 (do #26 first)
curl -s -X POST "$API/issues/25/dependencies" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"index": 26, "owner": "'"$OWNER"'", "repo": "'"$REPO"'"}'
```

### Remove Dependency

```bash
curl -s -X DELETE "$API/issues/25/dependencies" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"index": 26, "owner": "'"$OWNER"'", "repo": "'"$REPO"'"}'
```

### Cross-Repo Dependencies

```bash
# Issue #10 in this repo depends on issue #5 in another-repo
curl -s -X POST "$API/issues/10/dependencies" \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"index": 5, "owner": "other-owner", "repo": "other-repo"}'
```

## Shell Functions

Convenient wrappers for common operations. Source these or add to `~/.zshrc`.

```bash
# Helper: extract tea config (used by all functions below)
_tea_api_setup() {
  TOKEN=$(grep 'token:' ~/.config/tea/config.yml | head -1 | awk '{print $2}')
  BASE_URL=$(grep 'url:' ~/.config/tea/config.yml | head -1 | awk '{print $2}')
  OWNER=$(git remote get-url origin | sed -E 's|.*[:/]([^/]+)/([^/]+?)(\.git)?$|\1|')
  REPO=$(git remote get-url origin | sed -E 's|.*[:/]([^/]+)/([^/]+?)(\.git)?$|\2|' | sed 's/\.git$//')
  API="$BASE_URL/api/v1/repos/$OWNER/$REPO"
}

# Add dependency: tea-dep-add <issue> <depends-on>
# Example: tea-dep-add 25 26  →  #25 now depends on #26
tea-dep-add() {
  _tea_api_setup
  local result=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/issues/$1/dependencies" \
    -H "Authorization: token $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"index": '"$2"', "owner": "'"$OWNER"'", "repo": "'"$REPO"'"}')
  if [ "$result" = "201" ]; then
    echo "Added: #$1 depends on #$2"
  elif [ "$result" = "409" ]; then
    echo "Already exists: #$1 depends on #$2"
  else
    echo "Error (HTTP $result): could not add dependency"
  fi
}

# List dependencies: tea-dep-list <issue>
tea-dep-list() {
  _tea_api_setup
  local deps=$(curl -s "$API/issues/$1/dependencies" -H "Authorization: token $TOKEN")
  local count=$(echo "$deps" | jq 'length')
  if [ "$count" = "0" ] || [ "$count" = "null" ]; then
    echo "Issue #$1 has no dependencies"
  else
    echo "Issue #$1 depends on:"
    echo "$deps" | jq -r '.[] | "  #\(.number) [\(.state)] \(.title)"'
  fi
}

# Remove dependency: tea-dep-rm <issue> <depends-on>
tea-dep-rm() {
  _tea_api_setup
  local result=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$API/issues/$1/dependencies" \
    -H "Authorization: token $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"index": '"$2"', "owner": "'"$OWNER"'", "repo": "'"$REPO"'"}')
  if [ "$result" = "200" ]; then
    echo "Removed: #$1 no longer depends on #$2"
  else
    echo "Error (HTTP $result): could not remove dependency"
  fi
}

# Show all dependencies for open issues: tea-dep-all
tea-dep-all() {
  _tea_api_setup
  local found=0
  for i in $(tea issues list --output json | jq -r '.[].index'); do
    local deps=$(curl -s "$API/issues/$i/dependencies" \
      -H "Authorization: token $TOKEN" | jq -r '.[].number' 2>/dev/null)
    if [ -n "$deps" ]; then
      echo "#$i depends on: $(echo $deps | tr '\n' ' ')"
      found=1
    fi
  done
  [ "$found" = "0" ] && echo "No dependencies found for open issues"
}

# Find issues ready to work on (no open blockers): tea-dep-ready
tea-dep-ready() {
  _tea_api_setup
  echo "Issues with no open blockers:"
  for i in $(tea issues list --output json | jq -r '.[].index'); do
    local open_blockers=$(curl -s "$API/issues/$i/dependencies" \
      -H "Authorization: token $TOKEN" | jq '[.[] | select(.state == "open")] | length')
    if [ "$open_blockers" = "0" ] || [ "$open_blockers" = "null" ]; then
      local title=$(tea issues list --output json | jq -r ".[] | select(.index == $i) | .title")
      echo "  #$i $title"
    fi
  done
}

# Visualize dependency graph: tea-dep-graph
# Outputs a simple text graph of all dependencies
tea-dep-graph() {
  _tea_api_setup
  echo "Dependency graph (A → B means A depends on B):"
  echo "---"
  for i in $(tea issues list --state all --output json | jq -r '.[].index'); do
    local deps=$(curl -s "$API/issues/$i/dependencies" \
      -H "Authorization: token $TOKEN" | jq -r '.[].number' 2>/dev/null)
    if [ -n "$deps" ]; then
      for d in $deps; do
        echo "  #$i → #$d"
      done
    fi
  done
}
```

## Usage Examples

```bash
# Issue #25 depends on #26 (do #26 first)
tea-dep-add 25 26

# List what #25 depends on
tea-dep-list 25

# Remove dependency
tea-dep-rm 25 26

# Show all dependency relationships
tea-dep-all

# Find unblocked issues ready to work on
tea-dep-ready

# See the full dependency graph
tea-dep-graph

# Bulk add dependencies
for pair in "25 26" "9 26" "23 22" "14 15"; do
  tea-dep-add $pair
done
```

## Notes

- Dependencies appear in the Forgejo web UI on each issue
- "A depends on B" means B blocks A — complete B first
- Cross-repo dependencies are supported by specifying different owner/repo in the JSON body
- The `tea-dep-ready` function finds issues with zero open blockers — ideal for picking up next work
- `tea-dep-graph` outputs a simple text representation; pipe to `sort` for cleaner output
- If API calls fail with 401, refresh your token with `tea login`
- The `_tea_api_setup` helper avoids repeating config extraction in every function
