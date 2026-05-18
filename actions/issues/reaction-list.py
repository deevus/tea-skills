#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, run_action
from repo_scope import add_repository_scope_arguments, default_repo_scope, repository_scope_options_from_args
from issues import list_reactions


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="List reactions on a Gitea/Forgejo issue.")
    parser.add_argument("issue", type=int)
    add_repository_scope_arguments(parser)
    args = parser.parse_args(argv)
    try:
        reactions = list_reactions(default_repo_scope(options=repository_scope_options_from_args(args)), args.issue)
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for reaction in reactions:
        user = reaction.get("user", {}).get("login", "unknown")
        print(f"{user}: {reaction.get('content', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_action(Path(__file__), sys.argv[1:], main))
