---
name: milestone-issues
description: Manage issues within Gitea/Forgejo milestones — list, add, remove, progress tracking, burndown, bulk assign, and move between milestones.
user-invokable: true
---

# Milestone Issues

## List / Add / Remove

```bash
tea milestones issues "v1.0" -o simple                    # list issues (recommended)
tea milestones issues "v1.0" --state all --kind issue      # filter by state/kind
tea milestones issues "v1.0" --fields "index,title,state,assignees,labels"
tea milestones issues add "v1.0" 42                        # assign issue
tea milestones issues remove "v1.0" 42                     # unassign issue
```

## Bulk Assign

```bash
# By label
tea issues list --labels "release:v1.0" --output json | \
  jq -r '.[].index' | xargs -I{} tea milestones issues add "v1.0" {}

# By range
for i in $(seq 10 20); do tea milestones issues add "v1.0" $i; done
```

## Progress Tracking

```bash
tea milestones list --output json | jq '.[] | {
  title, open: .open_issues, closed: .closed_issues,
  progress: (if (.open_issues + .closed_issues) > 0
    then ((.closed_issues * 100) / (.open_issues + .closed_issues) | round | tostring) + "%"
    else "0%" end)
}'
```

## Burndown

```bash
for ms in $(tea milestones list --output json | jq -r '.[].title'); do
  open=$(tea milestones issues "$ms" --state open --output json | jq length)
  closed=$(tea milestones issues "$ms" --state closed --output json | jq length)
  echo "$ms: $closed done, $open remaining"
done
```

## Move Issues Between Milestones

```bash
tea milestones issues "v1.0" --state open --output json | \
  jq -r '.[].index' | while read idx; do
    tea milestones issues remove "v1.0" $idx
    tea milestones issues add "v1.1" $idx
  done
```
