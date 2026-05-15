#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter, run_action


VALID_STATES = {"open", "closed", "all"}


class JsonlArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        write_error("invalid_arguments", message)
        raise SystemExit(2)


def write_jsonl(record: dict[str, Any], stream=None) -> None:
    print(json.dumps(record, sort_keys=True, separators=(",", ":")), file=stream or sys.stdout)


def write_error(code: str, message: str) -> None:
    write_jsonl({"error": code, "message": message}, stream=sys.stderr)


def current_branch() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "branch", "--show-current"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    branch = completed.stdout.strip()
    return branch or None


def main(argv: list[str]) -> int:
    parser = JsonlArgumentParser(description="Find pull requests by head branch and emit JSONL records.")
    parser.add_argument("--head", help="Head branch, or owner:branch for fork pull requests")
    parser.add_argument("--base", help="Optional target base branch name")
    parser.add_argument("--state", choices=sorted(VALID_STATES), default="open")
    args = parser.parse_args(argv)

    base = args.base.strip() if args.base is not None else None
    if base == "" or (base is not None and ":" in base):
        write_error("invalid_base", "--base accepts a branch name, not owner:branch")
        return 1

    head = args.head.strip() if args.head is not None else current_branch()
    if args.head is not None and (not head or (":" in head and "" in head.split(":", 1))):
        write_error("invalid_head", "--head accepts a branch name or owner:branch")
        return 1
    if not head:
        write_error("head_required", "--head is required when the current git branch cannot be determined")
        return 1

    try:
        matches = default_adapter().find_pull_requests_by_branch(head, base=base, state=args.state)
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        write_error("api_error", str(exc))
        return 1

    if not matches:
        write_error("not_found", f"no {args.state} pull request found for head branch {head}")
        return 1

    for match in matches:
        write_jsonl(match)
    return 0


if __name__ == "__main__":
    raise SystemExit(run_action(Path(__file__), sys.argv[1:], main))
