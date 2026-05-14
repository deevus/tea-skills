#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter


def main(argv: list[str]) -> int:
    if argv:
        print("usage: dependency-ready", file=sys.stderr)
        return 2
    try:
        issues = default_adapter().ready_issues()
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("Issues with no open blockers:")
    for issue in issues:
        number = issue.get("number") or issue.get("index")
        print(f"  #{number} {issue.get('title')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
