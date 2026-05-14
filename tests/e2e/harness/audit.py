from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from .model import AuditEvent


class AuditAssertionError(AssertionError):
    pass


def load_audit_events(path: Path, normalizer: Callable[[dict[str, Any]], AuditEvent]) -> list[AuditEvent]:
    if not path.exists():
        return []
    events: list[AuditEvent] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(normalizer(json.loads(line)))
    return events


def assert_audit(events: list[AuditEvent], expectation: dict[str, Any]) -> None:
    counts = Counter(event.root for event in events)
    for required in expectation.get("events", []):
        root = required["root"]
        actual = counts[root]
        minimum = int(required.get("min", 0))
        maximum = required.get("max")
        if actual < minimum:
            raise AuditAssertionError(f"{root} count {actual} is below min {minimum}")
        if maximum is not None and actual > int(maximum):
            raise AuditAssertionError(f"{root} count {actual} is above max {maximum}")

    budgets = expectation.get("budgets", {})
    total_commands = budgets.get("total_commands", {})
    if "max" in total_commands and len(events) > int(total_commands["max"]):
        raise AuditAssertionError(f"total command count {len(events)} is above max {total_commands['max']}")

    mutation_count = sum(1 for event in events if event.mutates)
    total_mutations = budgets.get("total_mutations", {})
    if "max" in total_mutations and mutation_count > int(total_mutations["max"]):
        raise AuditAssertionError(f"mutation count {mutation_count} is above max {total_mutations['max']}")

    for root, budget in budgets.get("per_root", {}).items():
        actual = counts[root]
        if "min" in budget and actual < int(budget["min"]):
            raise AuditAssertionError(f"{root} count {actual} is below min {budget['min']}")
        if "max" in budget and actual > int(budget["max"]):
            raise AuditAssertionError(f"{root} count {actual} is above max {budget['max']}")
