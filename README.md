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

## Actions

Bundled actions cover API-only operations: features Gitea/Forgejo supports but the `tea` CLI does not expose cleanly. Actions supplement `tea`; they do not replace it.

See [`actions/README.md`](actions/README.md) and the domain README files for exact commands and arguments.

| Domain | Reference |
|---|---|
| Issues | `actions/issues/README.md` |
| Pull Requests | `actions/pull-requests/README.md` |
| Milestones | `actions/milestones/README.md` |
| Organization Labels | `actions/org-labels/README.md` |

## Prerequisites

- [tea CLI](https://gitea.com/gitea/tea) configured with `tea login`
- Python 3

## Installation

Install as a Claude Code plugin:

```bash
claude mcp add-plugin tea /path/to/tea-skills
```

## Contributing

Development and test details live in [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

MIT
