# API Setup

Extract credentials and repo context from `tea` config and git remote.

```bash
TOKEN=$(grep 'token:' ~/.config/tea/config.yml | head -1 | awk '{print $2}')
BASE_URL=$(grep 'url:' ~/.config/tea/config.yml | head -1 | awk '{print $2}')
OWNER=$(git remote get-url origin | sed -E 's|.*[:/]([^/]+)/([^/]+?)(\.git)?$|\1|')
REPO=$(git remote get-url origin | sed -E 's|.*[:/]([^/]+)/([^/]+?)(\.git)?$|\2|' | sed 's/\.git$//')
API="$BASE_URL/api/v1/repos/$OWNER/$REPO"
```

As a shell function (for use in scripts):

```bash
_tea_api_setup() {
  TOKEN=$(grep 'token:' ~/.config/tea/config.yml | head -1 | awk '{print $2}')
  BASE_URL=$(grep 'url:' ~/.config/tea/config.yml | head -1 | awk '{print $2}')
  OWNER=$(git remote get-url origin | sed -E 's|.*[:/]([^/]+)/([^/]+?)(\.git)?$|\1|')
  REPO=$(git remote get-url origin | sed -E 's|.*[:/]([^/]+)/([^/]+?)(\.git)?$|\2|' | sed 's/\.git$//')
  API="$BASE_URL/api/v1/repos/$OWNER/$REPO"
}
```

If API calls fail with 401, refresh your token with `tea login`.
