# tea

Claude Code skills for Gitea/Forgejo workflows using the [tea CLI](https://gitea.com/gitea/tea).

## Skills

Each skill is a focused, user-invokable `skills/<name>/SKILL.md` file.

| Domain | Skills |
|---|---|
| Issues | `list-issues`, `create-issue`, `edit-issues`, `close-issues`, `issue-comments`, `issue-dependencies`, `issue-moderation` |
| Pull Requests | `list-pulls`, `create-pull`, `review-pull`, `merge-pull`, `close-pulls` |
| Milestones | `milestones`, `milestone-issues` |
| Labels | `labels`, `label-schemes` |
| API | `using-the-tea-api` |

## Scripts

Executable bundled scripts cover API-only operations (things `tea` CLI can't do):

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

### Bundled script invocation

Skill docs use `scripts/<name>` as a bundled plugin resource path. It refers to this plugin's `scripts/` directory inside the installed plugin, not to a `scripts/` directory in the user's current repository.

When executing from another project, resolve `scripts/<name>` to the installed plugin root and run that absolute path while keeping the working directory in the target repository:

```bash
/path/to/tea-skills/scripts/tea-dep ready
```

Do not require users to `cd` into this plugin or add `scripts/` to `PATH`. The scripts intentionally run from the target repository because `scripts/tea-api` derives `OWNER` and `REPO` from that repository's git remote.

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
│   ├── marketplace.json
│   └── plugin.json
├── hooks/
│   ├── hooks.json
│   ├── run-hook.cmd
│   └── session-start.sh
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
│   ├── create-issue/
│   ├── create-pull/
│   ├── issue-dependencies/
│   ├── merge-pull/
│   └── ...
├── README.md
└── LICENSE
```

## License

MIT
