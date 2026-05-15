"""Organization-scoped Forgejo API access for bundled action domain modules."""

from __future__ import annotations

from typing import Any, Mapping
from urllib import parse

try:
    from .tea_api import GiteaAdapter, discover_repo_context
except ImportError:
    from tea_api import GiteaAdapter, discover_repo_context


class OrgScope:
    def __init__(self, api: GiteaAdapter | None = None, owner: str | None = None):
        self.api = api or GiteaAdapter()
        self.owner = owner or discover_repo_context().owner

    @property
    def root_url(self) -> str:
        owner = parse.quote(self.owner, safe="")
        return f"{self.api.api_root}/orgs/{owner}"

    def url(self, endpoint: str, query: Mapping[str, Any] | None = None) -> str:
        clean_endpoint = endpoint.strip("/")
        url = f"{self.root_url}/{clean_endpoint}" if clean_endpoint else self.root_url
        if query:
            url = f"{url}?{parse.urlencode(query)}"
        return url

    def get(self, endpoint: str, query: Mapping[str, Any] | None = None) -> Any:
        return self.api.request_json("GET", self.url(endpoint, query))

    def post(self, endpoint: str, body: Mapping[str, Any] | None = None) -> Any:
        return self.api.request_json("POST", self.url(endpoint), body)


def default_org_scope() -> OrgScope:
    return OrgScope()
