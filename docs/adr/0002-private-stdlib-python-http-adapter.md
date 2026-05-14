# Keep the HTTP Adapter private and stdlib-only Python

The Gitea/Forgejo HTTP Adapter will live at `actions/internal/tea_api.py`, use only the Python standard library, and remain a private Module for bundled actions. This gives action Implementations robust JSON, URL, config, HTTP, and error handling without adding plugin dependencies or promising a stable public API to users.

## Considered Options

- Keep a sourced bash helper as the main Adapter.
- Expose a public generic HTTP command for ad-hoc API use.
- Use a private stdlib-only Python Adapter imported by bundled actions.

## Consequences

Action scripts get a deeper shared seam with better locality for transport bugs. Users should be routed to `tea` or documented bundled actions, not to internal Adapter functions.
