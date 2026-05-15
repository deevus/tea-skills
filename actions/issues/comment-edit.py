#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, run_action
from repo_scope import default_repo_scope
from issues import edit_comment


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Edit a Gitea/Forgejo issue comment.")
    parser.add_argument("comment_id", type=int)
    parser.add_argument("body")
    args = parser.parse_args(argv)
    try:
        comment = edit_comment(default_repo_scope(), args.comment_id, args.body)
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Comment #{comment.get('id', args.comment_id)} updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_action(Path(__file__), sys.argv[1:], main))
