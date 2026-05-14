#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Add an issue dependency. A depends on B; B blocks A.")
    parser.add_argument("issue", type=int)
    parser.add_argument("depends_on", type=int)
    args = parser.parse_args(argv)
    try:
        result = default_adapter().add_issue_dependency(args.issue, args.depends_on)
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if result == "exists":
        print(f"Already exists: #{args.issue} depends on #{args.depends_on}")
    else:
        print(f"Added: #{args.issue} depends on #{args.depends_on}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
