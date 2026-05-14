#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Create a Gitea/Forgejo organization label.")
    parser.add_argument("name")
    parser.add_argument("color")
    parser.add_argument("description", nargs="?", default="")
    args = parser.parse_args(argv)
    try:
        label = default_adapter().create_org_label(args.name, args.color, args.description)
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Created org label: {label.get('name', args.name)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
