# tea-skills

A set of agent skills, packaged for Claude Code and usable by other CLI agents such as Pi, that helps agents operate Gitea/Forgejo projects through tea CLI workflows and focused bundled actions.

## Language

**Bundled action**:
An executable shipped inside the plugin for a specific Gitea/Forgejo capability that `tea` does not expose cleanly.
_Avoid_: script, helper, broad command

**Pull request lookup action**:
An API-backed bundled action that finds an existing pull request from structured repository data without parsing human CLI output.
_Avoid_: PR creation helper, internal helper, output parser, tea output parser

**Agent E2E prompt**:
A natural user request used in AI-backed E2E tests to verify skill routing and workflow behavior. It should describe the user's goal without naming the skill or dictating exact command syntax.
_Avoid_: skill invocation script, command recipe, over-specified prompt

**Agent E2E assertion**:
The deterministic checks around an AI-backed E2E run: loaded skills, required command classes, mock state, and workspace artifacts. Assertions should prove the important behavior without making the prompt overly directive.
_Avoid_: prompt-as-assertion, exact-command-only proof

**Repository scope**:
A private internal Module that derives repo-scoped Forgejo API access from the current git remote and exposes repository-rooted request operations to domain Implementations.
_Avoid_: repo helper, public API, repository command


**PRD artifact**:
A product requirements document captured outside the repository, normally in the issue tracker, for feature planning and agent handoff. Use this instead of committing design documents to the repo unless the user explicitly asks for an in-repo design/spec file.
_Avoid_: committed brainstorming design docs, repo-local planning artifacts by default

## Relationships

- A **Bundled action** belongs to exactly one domain folder under `actions/`.
- A **Pull request lookup action** is a **Bundled action** in the pull-requests domain.
- An **Agent E2E prompt** expresses intent; an **Agent E2E assertion** verifies the routed skill, command behavior, and resulting artifacts.
- When a workflow needs a detail command, assert the command class was used, but prove the specific data via state or files rather than pinning the prompt to an exact issue number or command form.

- Planning artifacts for substantive behavior changes should be **PRD artifacts** in the issue tracker rather than committed design docs, unless the user explicitly requests an in-repo spec/design file.

## Example dialogue

> **Dev:** "Should the agent parse the text printed by `tea pulls create` to find the PR URL?"
> **Domain expert:** "No — use a **Pull request lookup action** so the workflow depends on structured repository data."

> **Dev:** "Should an issue-domain E2E prompt say 'Use the list-issues skill, list open issues, then run `tea issues show 1`?'"
> **Domain expert:** "No — ask like a user: 'List open issues and save the body of the first issue to first-issue-body.txt.' Then assert the list skill loaded, an issue list command ran, an issue detail command ran, and the file contains the expected body."

## Flagged ambiguities

- "helper" was used for the pull-request branch lookup work — resolved: this is a user-facing **Pull request lookup action**, not an internal helper or PR creation replacement.
