#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, run_action
from repo_scope import add_repository_scope_arguments, default_repo_scope, repository_scope_options_from_args
from issues import add_dependency


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Add an issue dependency. A depends on B; B blocks A.")
    parser.add_argument("issue", type=int)
    parser.add_argument("depends_on", type=int)
    add_repository_scope_arguments(parser)
    args = parser.parse_args(argv)
    try:
        result = add_dependency(
            default_repo_scope(options=repository_scope_options_from_args(args)), args.issue, args.depends_on
        )
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if result == "exists":
        print(f"Already exists: #{args.issue} depends on #{args.depends_on}")
    else:
        print(f"Added: #{args.issue} depends on #{args.depends_on}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_action(Path(__file__), sys.argv[1:], main))
