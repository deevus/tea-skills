#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, run_action
from repo_scope import default_repo_scope
from issues import unpin


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Unpin a Gitea/Forgejo issue.")
    parser.add_argument("issue", type=int)
    args = parser.parse_args(argv)
    try:
        unpin(default_repo_scope(), args.issue)
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Unpinned #{args.issue}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_action(Path(__file__), sys.argv[1:], main))
