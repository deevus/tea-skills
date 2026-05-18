"""Repository-scoped Forgejo API access for bundled action domain modules."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any, Mapping
from urllib import parse

try:
    from .tea_api import GiteaAdapter, RepoContext, discover_repo_context
except ImportError:
    from tea_api import GiteaAdapter, RepoContext, discover_repo_context


@dataclass(frozen=True)
class RepositoryScopeOptions:
    """Common repository targeting options accepted by bundled actions."""

    login: str | None = None
    remote: str | None = None
    repo: str | None = None


def add_repository_scope_arguments(parser: argparse.ArgumentParser) -> None:
    """Add tea-compatible repository targeting flags to an action parser."""
    group = parser.add_argument_group("repository scope")
    group.add_argument(
        "--login",
        "-l",
        help="Use a different Gitea/Forgejo login. Optional.",
    )
    group.add_argument(
        "--remote",
        "-R",
        help="Discover repository context from a named git remote. Optional.",
    )
    group.add_argument(
        "--repo",
        "-r",
        help="Override local repository discovery with an owner/repository slug. Optional.",
    )


def repository_scope_options_from_args(args: argparse.Namespace) -> RepositoryScopeOptions:
    """Extract shared repository targeting options from parsed action args."""
    return RepositoryScopeOptions(
        login=getattr(args, "login", None),
        remote=getattr(args, "remote", None),
        repo=getattr(args, "repo", None),
    )


class RepositoryScope:
    def __init__(
        self,
        api: GiteaAdapter | None = None,
        repo: RepoContext | None = None,
        scope_options: RepositoryScopeOptions | None = None,
    ):
        self.api = api or GiteaAdapter()
        self.scope_options = scope_options or RepositoryScopeOptions()
        self.repo = repo or discover_repo_context(self.api.config.base_url)

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


def default_repo_scope(
    api: GiteaAdapter | None = None,
    options: RepositoryScopeOptions | None = None,
) -> RepositoryScope:
    return RepositoryScope(api=api, scope_options=options)
