#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "internal"))
from tea_api import ApiError, TeaConfigError, RepoContextError, default_adapter, run_action


def main(argv: list[str]) -> int:
    if argv:
        print("usage: dependency-graph", file=sys.stderr)
        return 2
    try:
        edges = default_adapter().dependency_graph_edges()
    except (ApiError, TeaConfigError, RepoContextError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("Dependency graph (A -> B means A depends on B):")
    print("---")
    for issue, depends_on in edges:
        print(f"  #{issue} -> #{depends_on}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_action(Path(__file__), sys.argv[1:], main))
