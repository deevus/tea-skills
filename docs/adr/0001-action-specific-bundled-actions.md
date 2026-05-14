# Use action-specific bundled actions

Bundled plugin actions will be named and organized by the exact missing capability they provide, such as `actions/milestones/edit`, rather than broad domain commands with subcommands. This favors an honest Interface for agents: seeing an action path should not imply broader coverage than the Implementation actually supports.

## Considered Options

- Broad domain commands such as `actions/milestones` or `actions/pull-requests` with subcommands.
- Action-specific commands inside domain folders.

## Consequences

There will be more executable files, but each file path is a clearer routing signal. This reduces the risk that agents use bundled actions where the `tea` CLI should be used instead.
