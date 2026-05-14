# Organization label actions

Use `tea labels` for repository labels:

```bash
tea labels list -o simple
tea labels create --name "type:bug" --color "#d73a4a"
tea labels update --id 5 --description "Updated description"
tea labels delete 5
```

Use bundled actions for organization-level labels.

## List organization labels

```bash
actions/org-labels/list.py
```

## Create organization label

```bash
actions/org-labels/create.py <name> <color> [description]
```
