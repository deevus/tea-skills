# tea-skills

A set of agent skills, packaged for Claude Code and usable by other CLI agents such as Pi, that helps agents operate Gitea/Forgejo projects through tea CLI workflows and focused bundled actions.

## Language

**Bundled action**:
An executable shipped inside the plugin for a specific Gitea/Forgejo capability that `tea` does not expose cleanly.
_Avoid_: script, helper, broad command

**Pull request lookup action**:
An API-backed bundled action that finds an existing pull request from structured repository data without parsing human CLI output.
_Avoid_: PR creation helper, internal helper, output parser, tea output parser

## Relationships

- A **Bundled action** belongs to exactly one domain folder under `actions/`.
- A **Pull request lookup action** is a **Bundled action** in the pull-requests domain.

## Example dialogue

> **Dev:** "Should the agent parse the text printed by `tea pulls create` to find the PR URL?"
> **Domain expert:** "No — use a **Pull request lookup action** so the workflow depends on structured repository data."

## Flagged ambiguities

- "helper" was used for the pull-request branch lookup work — resolved: this is a user-facing **Pull request lookup action**, not an internal helper or PR creation replacement.
