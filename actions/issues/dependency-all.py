#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter, run_action


def main(argv: list[str]) -> int:
    if argv:
        print("usage: dependency-all", file=sys.stderr)
        return 2
    try:
        rows = default_adapter().all_issue_dependencies()
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not rows:
        print("No dependencies found for open issues")
    for issue, deps in rows:
        numbers = " ".join(f"#{dep.get('number')}" for dep in deps)
        print(f"#{issue} depends on: {numbers}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_action(Path(__file__), sys.argv[1:], main))
