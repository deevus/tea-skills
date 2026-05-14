#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter, run_action


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Enable or cancel pull request auto-merge.")
    parser.add_argument("pr", type=int)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--enable", action="store_true")
    mode.add_argument("--cancel", action="store_true")
    parser.add_argument("--style", choices=["merge", "squash", "rebase"], default="squash")
    parser.add_argument("--message", default="")
    args = parser.parse_args(argv)
    try:
        adapter = default_adapter()
        if args.enable:
            adapter.enable_pull_request_automerge(args.pr, args.style, args.message)
            print(f"Auto-merge enabled on PR #{args.pr} ({args.style})")
        else:
            adapter.cancel_pull_request_automerge(args.pr)
            print(f"Auto-merge cancelled on PR #{args.pr}")
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run_action(Path(__file__), sys.argv[1:], main))
