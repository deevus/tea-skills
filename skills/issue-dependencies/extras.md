# Issue Dependencies Extras

## Shell Functions

Source these or add to `~/.zshrc`. All use `_tea_api_setup` from `_api-setup.md`.

```bash
_tea_api_setup() {
  TOKEN=$(grep 'token:' ~/.config/tea/config.yml | head -1 | awk '{print $2}')
  BASE_URL=$(grep 'url:' ~/.config/tea/config.yml | head -1 | awk '{print $2}')
  OWNER=$(git remote get-url origin | sed -E 's|.*[:/]([^/]+)/([^/]+?)(\.git)?$|\1|')
  REPO=$(git remote get-url origin | sed -E 's|.*[:/]([^/]+)/([^/]+?)(\.git)?$|\2|' | sed 's/\.git$//')
  API="$BASE_URL/api/v1/repos/$OWNER/$REPO"
}

# tea-dep-add <issue> <depends-on>
tea-dep-add() {
  _tea_api_setup
  local result=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/issues/$1/dependencies" \
    -H "Authorization: token $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"index": '"$2"', "owner": "'"$OWNER"'", "repo": "'"$REPO"'"}')
  if [ "$result" = "201" ]; then echo "Added: #$1 depends on #$2"
  elif [ "$result" = "409" ]; then echo "Already exists: #$1 depends on #$2"
  else echo "Error (HTTP $result)"; fi
}

# tea-dep-list <issue>
tea-dep-list() {
  _tea_api_setup
  local deps=$(curl -s "$API/issues/$1/dependencies" -H "Authorization: token $TOKEN")
  local count=$(echo "$deps" | jq 'length')
  if [ "$count" = "0" ] || [ "$count" = "null" ]; then echo "Issue #$1 has no dependencies"
  else echo "Issue #$1 depends on:"; echo "$deps" | jq -r '.[] | "  #\(.number) [\(.state)] \(.title)"'; fi
}

# tea-dep-rm <issue> <depends-on>
tea-dep-rm() {
  _tea_api_setup
  local result=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$API/issues/$1/dependencies" \
    -H "Authorization: token $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"index": '"$2"', "owner": "'"$OWNER"'", "repo": "'"$REPO"'"}')
  if [ "$result" = "200" ]; then echo "Removed: #$1 no longer depends on #$2"
  else echo "Error (HTTP $result)"; fi
}

# tea-dep-all — show all dependencies for open issues
tea-dep-all() {
  _tea_api_setup
  local found=0
  for i in $(tea issues list --output json | jq -r '.[].index'); do
    local deps=$(curl -s "$API/issues/$i/dependencies" \
      -H "Authorization: token $TOKEN" | jq -r '.[].number' 2>/dev/null)
    if [ -n "$deps" ]; then echo "#$i depends on: $(echo $deps | tr '\n' ' ')"; found=1; fi
  done
  [ "$found" = "0" ] && echo "No dependencies found for open issues"
}

# tea-dep-ready — find issues with no open blockers
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

# tea-dep-graph — text visualization of all dependencies
tea-dep-graph() {
  _tea_api_setup
  echo "Dependency graph (A → B means A depends on B):"
  echo "---"
  for i in $(tea issues list --state all --output json | jq -r '.[].index'); do
    local deps=$(curl -s "$API/issues/$i/dependencies" \
      -H "Authorization: token $TOKEN" | jq -r '.[].number' 2>/dev/null)
    if [ -n "$deps" ]; then for d in $deps; do echo "  #$i → #$d"; done; fi
  done
}
```

## Usage

```bash
tea-dep-add 25 26      # #25 depends on #26
tea-dep-list 25        # what blocks #25
tea-dep-rm 25 26       # remove
tea-dep-all            # all relationships
tea-dep-ready          # unblocked issues
tea-dep-graph          # full graph

# Bulk
for pair in "25 26" "9 26" "23 22"; do tea-dep-add $pair; done
```
