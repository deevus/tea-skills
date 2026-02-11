---
name: labels
description: List, create, update, and delete Gitea/Forgejo issue labels.
user-invokable: true
---

# Labels

## List

```bash
tea labels list -o simple          # all labels, compact output (recommended)
tea labels list --output json      # use json only when parsing with jq
tea labels list --save             # export to file (tea internal format)
```

## Create

```bash
tea labels create --name "bug" --color "#d73a4a"
tea labels create --name "enhancement" --color "#a2eeef" --description "New feature or request"
tea labels create --file labels.csv   # bulk import from file
```

## Update

```bash
# Get label ID (requires json for parsing)
tea labels list --output json | jq '.[] | {id, name, color}'

tea labels update --id 5 --name "bugfix" --color "#d73a4a"
tea labels update --id 5 --description "Updated description"
```

## Delete

```bash
tea labels delete 5
```

## Apply to Issues

```bash
tea issues create --title "Fix login" --labels "type:bug,priority:high"
tea issues edit 42 --add-labels "status:in-progress"
tea issues edit 42 --remove-labels "status:needs-triage"
```

## Tips

- Labels identified by name in `tea issues`, by ID in `tea labels update/delete`
- Colors need `#` prefix (e.g., `#d73a4a`)
- Names are case-sensitive
- Deleting a label removes it from all issues/PRs
