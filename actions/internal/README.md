# Internal action support

`tea_api.py` is a private Python Module used by bundled actions. It is not a user-facing command Interface.

Responsibilities:

- discover tea config from `$XDG_CONFIG_HOME/tea/config.yml` or `~/.config/tea/config.yml`
- derive repo owner/name from `git remote get-url origin`
- build repo and org API URLs
- encode query strings and JSON bodies safely
- send authenticated Gitea/Forgejo HTTP requests with Python stdlib only
- expose domain helper functions for action executables

Users and agents should use documented commands in the domain README files instead of importing this Module directly.
