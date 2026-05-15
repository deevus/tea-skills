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

### Bundled action invocation

Skill docs use `actions/<domain>/<action>` as a bundled plugin resource path. It refers to this plugin's `actions/` directory inside the installed plugin, not to an `actions/` directory in the user's current repository.

When executing from another project, resolve the action to the installed plugin root and run that absolute path while keeping the working directory in the target repository:

```bash
/path/to/tea-skills/actions/issues/dependency-ready.py
```

Do not require users to `cd` into this plugin or add `actions/` to `PATH`. Actions intentionally run from the target repository because the private Adapter derives owner and repo from that repository's git remote.

## Prerequisites

- [tea CLI](https://gitea.com/gitea/tea) configured with `tea login`
- Python 3

## Development testing

Contributor docs for the opt-in live agent E2E harness live in [`tests/e2e/README.md`](tests/e2e/README.md).

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
├── actions/
│   ├── README.md
│   ├── internal/
│   │   ├── README.md
│   │   └── tea_api.py
│   ├── issues/
│   ├── pull-requests/
│   ├── milestones/
│   └── org-labels/
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
