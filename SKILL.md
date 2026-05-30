---
name: tea-skills
description: Installable container for the tea-skills package. Use the focused skills under skills/ for Gitea/Forgejo issue, pull request, milestone, and label workflows.
disable-model-invocation: true
---

# tea-skills Package

This root skill exists so `npx skills` installs the complete tea-skills repository as one namespaced package at `~/.agents/skills/tea-skills` when users run:

```bash
npx skills add deevus/tea-skills --skill '*' --agent universal
```

Do not use this container as the workflow guide. Use the focused skills in `skills/<name>/SKILL.md` instead. Those skills can resolve bundled resources such as `actions/` and shared references relative to this installed package root.
