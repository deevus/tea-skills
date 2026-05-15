# Contributing

Development and test details for this repository live here so the top-level README can stay focused on installing and using the skill plugin.

## Bundled action invocation

Skill docs use `actions/<domain>/<action>` as a bundled plugin resource path. It refers to this plugin's `actions/` directory inside the installed plugin, not to an `actions/` directory in the user's current repository.

When executing from another project, resolve the action to the installed plugin root and run that absolute path while keeping the working directory in the target repository:

```bash
/path/to/tea-skills/actions/issues/dependency-ready.py
```

Do not require users to `cd` into this plugin or add `actions/` to `PATH`. Actions intentionally run from the target repository because the private adapter derives owner and repo from that repository's git remote.

## Development testing

Contributor docs for the AI-backed mock-tea E2E harness live in [`tests/e2e/README.md`](tests/e2e/README.md).

## Development tooling

This repository uses [mise](https://mise.jdx.dev/) to provision `ruff` and [hk](https://hk.jdx.dev/) for hook orchestration.

```bash
mise install
mise run lint
mise run format
```

`mise install` installs hk hooks with `hk install --mise`; `mise run lint` runs `hk check --all`, and `mise run format` runs `hk fix --all`.

## Repository structure

```text
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
├── CONTRIBUTING.md
├── README.md
└── LICENSE
```
