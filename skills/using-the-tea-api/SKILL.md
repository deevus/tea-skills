---
name: using-the-tea-api
description: Direct Gitea/Forgejo API access — shared helpers, authentication, and ad-hoc API call patterns for anything the tea CLI doesn't cover.
user-invokable: true
---

# Using the Tea API

Direct Gitea/Forgejo API access for anything the tea CLI or existing scripts don't cover.

## Setup

```bash
source scripts/tea-api
```

## Available Helpers

| Function | Purpose |
|----------|---------|
| `_api_get <endpoint>` | GET request, returns JSON |
| `_api_post <endpoint> '<json>'` | POST request with JSON body |
| `_api_patch <endpoint> '<json>'` | PATCH request with JSON body |
| `_api_delete <endpoint> [json]` | DELETE request, optional body |
| `_api_post_status <endpoint> '<json>'` | POST, returns HTTP status code |
| `_api_delete_status <endpoint> '<json>'` | DELETE, returns HTTP status code |

## How Context Is Derived

- `TOKEN` / `BASE_URL` — extracted from `~/.config/tea/config.yml`
- `OWNER` / `REPO` — parsed from the git remote URL
- `API` = `$BASE_URL/api/v1/repos/$OWNER/$REPO`

## Common Patterns

```bash
source scripts/tea-api

# GET
_api_get "issues/42" | jq '.title'

# POST
_api_post "issues" '{"title": "New issue"}'

# PATCH
_api_patch "issues/42" '{"state": "closed"}'

# DELETE
_api_delete "labels/5"

# Status check for error handling
status=$(_api_post_status "issues/42/labels" '{"labels":[1]}')
```

## API Documentation

The full Swagger docs are available at `$BASE_URL/api/swagger` on your Gitea/Forgejo instance.
