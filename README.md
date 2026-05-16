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

## Example prompts

- "List open issues and summarize the top three that look ready to work on."
- "Create an issue for the failing login redirect and label it as a bug."
- "Show pull requests that need review and summarize the current blockers."
- "Create a WIP pull request from my current branch."
- "Add this issue to the v1.0 milestone."
- "Find issues that are ready because their dependencies are closed."

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

## Contributing

Development and test details live in [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

MIT
