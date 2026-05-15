#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, run_action
from org_scope import default_org_scope
from org_labels import list_labels


def main(argv: list[str]) -> int:
    if argv:
        print("usage: list", file=sys.stderr)
        return 2
    try:
        labels = list_labels(default_org_scope())
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for label in labels:
        print(f"{label.get('name')} {label.get('color')} {label.get('description') or ''}".rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(run_action(Path(__file__), sys.argv[1:], main))
