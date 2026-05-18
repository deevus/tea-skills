#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, run_action
from repo_scope import add_repository_scope_arguments, default_repo_scope, repository_scope_options_from_args
from milestones import edit as edit_milestone


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Edit a Gitea/Forgejo milestone.")
    parser.add_argument("name")
    parser.add_argument("--title")
    parser.add_argument("--deadline")
    parser.add_argument("--description")
    add_repository_scope_arguments(parser)
    args = parser.parse_args(argv)
    if args.title is None and args.deadline is None and args.description is None:
        parser.error("provide at least one of --title, --deadline, or --description")
    try:
        edit_milestone(
            default_repo_scope(options=repository_scope_options_from_args(args)),
            args.name,
            args.title,
            args.deadline,
            args.description,
        )
    except (ApiError, TeaConfigError, RepoContextError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Milestone '{args.name}' updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_action(Path(__file__), sys.argv[1:], main))
