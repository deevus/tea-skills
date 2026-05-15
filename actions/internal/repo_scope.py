"""Repository-scoped Forgejo API access for bundled action domain modules."""

from __future__ import annotations

from typing import Any, Mapping
from urllib import parse

try:
    from .tea_api import GiteaAdapter, RepoContext, discover_repo_context
except ImportError:
    from tea_api import GiteaAdapter, RepoContext, discover_repo_context


class RepositoryScope:
    def __init__(self, api: GiteaAdapter | None = None, repo: RepoContext | None = None):
        self.api = api or GiteaAdapter()
        self.repo = repo or discover_repo_context()

    @property
    def owner(self) -> str:
        return self.repo.owner

    @property
    def name(self) -> str:
        return self.repo.repo

    @property
    def root_url(self) -> str:
        owner = parse.quote(self.owner, safe="")
        repo = parse.quote(self.name, safe="")
        return f"{self.api.api_root}/repos/{owner}/{repo}"

    @property
    def web_url(self) -> str:
        owner = parse.quote(self.owner, safe="")
        repo = parse.quote(self.name, safe="")
        return f"{self.api.config.base_url}/{owner}/{repo}"

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

    def patch(self, endpoint: str, body: Mapping[str, Any]) -> Any:
        return self.api.request_json("PATCH", self.url(endpoint), body)

    def delete(self, endpoint: str, body: Mapping[str, Any] | None = None) -> Any:
        return self.api.request_json("DELETE", self.url(endpoint), body)


def default_repo_scope() -> RepositoryScope:
    return RepositoryScope()
