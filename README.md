# tea-skills

Agent skills for Gitea/Forgejo workflows using the [tea CLI](https://gitea.com/gitea/tea).

`tea-skills` helps coding agents list and create issues, manage pull requests, work with milestones and labels, and use a few bundled actions for Gitea/Forgejo API features that `tea` does not expose cleanly. The skills are packaged as a Claude Code plugin and as standard `SKILL.md` files that should work with any agent CLI that supports agent skills.

## Prerequisites

- [tea CLI](https://gitea.com/gitea/tea) installed and available on `PATH`
- A configured tea login:

  ```bash
  tea login add
  tea login list
  ```

- Python 3.10 or newer for bundled actions
- Git, with the target Gitea/Forgejo repository checked out locally

## Installation

### Claude Code plugin

Claude Code installs plugins from marketplaces. Add the GitHub repository as a marketplace, then install the `tea` plugin from it:

```text
/plugin marketplace add deevus/tea-skills
/plugin install tea@tea-skills
```

For non-interactive setup, use the equivalent CLI commands:

```bash
claude plugin marketplace add deevus/tea-skills
claude plugin install tea@tea-skills
```

### Other agents with `npx skills`

The skills live in `skills/<name>/SKILL.md`, so they can also be installed with the open agent skills CLI for agents that support skills.

From GitHub:

```bash
npx skills add deevus/tea-skills --skill '*'
```

To target a specific agent, pass the agent name supported by `npx skills`:

```bash
npx skills add deevus/tea-skills --skill '*' --agent codex
npx skills add deevus/tea-skills --skill '*' --agent pi
```

Compatibility depends on the agent's skill support. Claude Code plugin hooks are Claude-specific, but the skill instructions themselves are plain `SKILL.md` files.

## Verify setup

From a Gitea/Forgejo repository where you want the agent to work, confirm tea can see your server and repository:

```bash
tea login list
tea issues list -o simple
```

If you installed with `npx skills`, you can also ask it to list installed skills:

```bash
npx skills list
```

Then try a small prompt in your agent:

> List the open issues in this repository.

## Troubleshooting

- **`tea` is missing or not on `PATH`:** install the [tea CLI](https://gitea.com/gitea/tea), restart your shell or agent session, then confirm `tea --version` works from the target repository.
- **No tea login is configured:** run `tea login add`, then `tea login list`. Bundled actions read the same tea authentication configuration.
- **Bundled actions fail with Python errors:** confirm `python3 --version` reports Python 3.10 or newer. The bundled actions are Python scripts and use the `python3` found on `PATH`.
- **A skill does not work as expected:** please create an issue with the prompt you used, the command or error the agent reported, and your agent/tea-skills installation method.

For more detail, see [`actions/README.md`](actions/README.md) and [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Example prompts

- "List open issues and summarize the top three that look ready to work on."
- "Create an issue for the failing login redirect and label it as a bug."
- "Show pull requests that need review and summarize the current blockers."
- "Create a WIP pull request from my current branch."
- "Add this issue to the v1.0 milestone."
- "Find issues that are ready because their dependencies are closed."

## Supported workflows

`tea-skills` keeps `tea` as the primary workflow engine. Skills should use normal `tea` commands whenever `tea` supports the task, then fall back to bundled actions only for known Gitea/Forgejo API gaps.

Each skill is a focused, user-invokable `skills/<name>/SKILL.md` file. The current inventory is grouped by workflow domain:

| Domain | What users can ask an agent to do | Skills |
|---|---|---|
| Issues | List and inspect issues, create and edit issues, close or reopen issues, manage comments, manage dependencies, and moderate issues with pins, locks, and reactions. | `list-issues`, `create-issue`, `edit-issues`, `close-issues`, `issue-comments`, `issue-dependencies`, `issue-moderation` |
| Pull Requests | List and inspect PRs, create PRs, request or perform reviews, resolve review threads, merge PRs, configure merge behavior, and close or reopen PRs. | `list-pulls`, `create-pull`, `review-pull`, `merge-pull`, `close-pulls` |
| Milestones | List, create, edit, close, reopen, and delete milestones, plus move issues into or out of milestones. | `milestones`, `milestone-issues` |
| Labels | Manage repository labels, label schemes, bulk label operations, and organization-level labels. | `labels`, `label-schemes` |

## Bundled actions and trust model

Bundled actions are small Python executables shipped with this plugin. They supplement `tea`; they do not replace it. Use them for API-only operations that Gitea/Forgejo supports but `tea` does not expose cleanly, such as issue dependencies, issue moderation, pull-request auto-merge configuration, milestone edit gaps, and organization labels.

Actions run on your machine with your user privileges, read the authentication configured by `tea login`, and derive the target owner/repository from the `origin` remote of the repository where the action is executed. When an agent runs a bundled action for your project, it should resolve the action path from the installed plugin and keep its working directory in your target repository.

See [`actions/README.md`](actions/README.md) and the domain references for exact commands and arguments:

| Domain | Reference |
|---|---|
| Issues | [`actions/issues/README.md`](actions/issues/README.md) |
| Pull Requests | [`actions/pull-requests/README.md`](actions/pull-requests/README.md) |
| Milestones | [`actions/milestones/README.md`](actions/milestones/README.md) |
| Organization Labels | [`actions/org-labels/README.md`](actions/org-labels/README.md) |

## Contributing

Development and test details live in [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

MIT
