from __future__ import annotations

from typing import Any
from urllib import parse

from actions.internal.tea_api import TeaConfig
from tests.e2e.tea_suite.provision import api_request


def list_issues(config: TeaConfig, org: str, repo: str) -> list[dict[str, Any]]:
    result = api_request(
        config,
        "GET",
        f"repos/{parse.quote(org, safe='')}/{parse.quote(repo, safe='')}/issues?state=all",
    )
    return result if isinstance(result, list) else []
