# tea

Claude Code skills for Gitea/Forgejo workflows using the [tea CLI](https://gitea.com/gitea/tea).

## Skills

| Skill | Invocation | Description |
|---|---|---|
| Issues | `tea:issues` | List, create, edit, close, dependencies |
| Pull Requests | `tea:pulls` | Create, review, merge PRs |
| Milestones | `tea:milestones` | Create, close, manage milestone issues |
| Labels | `tea:labels` | Create, update, delete, apply labels |

Each skill has a lean `SKILL.md` loaded into context, with optional companion files:

- `api.md` — API endpoints for features `tea` CLI doesn't support
- `extras.md` — bulk operations, workflow patterns, conventions

## Scripts

Executable scripts for API-only operations (things `tea` CLI can't do):

| Script | Description |
|---|---|
| `tea-api` | Shared credentials and API helpers (sourced by other scripts) |
| `tea-dep` | Issue dependency management (add, rm, list, all, ready, graph) |
| `tea-issue-pin` | Pin/unpin issues |
| `tea-issue-react` | Add/list reactions |
| `tea-issue-lock` | Lock/unlock issues |
| `tea-issue-comment` | Edit comments (add/list use `tea comment` directly) |
| `tea-pr-draft` | Create draft PRs, mark ready |
| `tea-pr-reviewers` | Request/remove reviewers |
| `tea-pr-automerge` | Enable/cancel auto-merge |
| `tea-milestone-edit` | Edit milestone title, deadline, description |
| `tea-label-org` | Manage organization-level labels |

## Prerequisites

- [tea CLI](https://gitea.com/gitea/tea) configured with `tea login`
- `jq` for JSON parsing
- `curl` for API scripts

## Installation

Install as a Claude Code plugin:

```bash
claude mcp add-plugin tea /path/to/tea-skills
```

## Structure

```
tea-skills/
├── .claude-plugin/
│   └── plugin.json
├── scripts/
│   ├── tea-api
│   ├── tea-dep
│   ├── tea-issue-pin
│   ├── tea-issue-react
│   ├── tea-issue-lock
│   ├── tea-issue-comment
│   ├── tea-pr-draft
│   ├── tea-pr-reviewers
│   ├── tea-pr-automerge
│   ├── tea-milestone-edit
│   └── tea-label-org
├── skills/
│   ├── issues/
│   │   ├── SKILL.md
│   │   ├── api.md
│   │   └── extras.md
│   ├── pulls/
│   │   ├── SKILL.md
│   │   ├── api.md
│   │   └── extras.md
│   ├── milestones/
│   │   ├── SKILL.md
│   │   └── extras.md
│   └── labels/
│       ├── SKILL.md
│       └── extras.md
├── README.md
└── LICENSE
```

## License

MIT
