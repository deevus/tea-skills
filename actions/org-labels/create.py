#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, run_action
from org_scope import default_org_scope
from org_labels import create as create_org_label


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Create a Gitea/Forgejo organization label.")
    parser.add_argument("name")
    parser.add_argument("color")
    parser.add_argument("description", nargs="?", default="")
    args = parser.parse_args(argv)
    try:
        label = create_org_label(default_org_scope(), args.name, args.color, args.description)
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Created org label: {label.get('name', args.name)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_action(Path(__file__), sys.argv[1:], main))
