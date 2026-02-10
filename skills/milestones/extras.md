# Milestones Extras

## Edit Milestone (API)

The `tea` CLI doesn't have a milestone edit command. Use the script.

```bash
scripts/tea-milestone-edit "v1.0" --title "v1.0.0"
scripts/tea-milestone-edit "v1.0" --deadline "2025-06-15"
scripts/tea-milestone-edit "v1.0" --description "Updated release notes"
```

## Bulk Assign Issues

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
