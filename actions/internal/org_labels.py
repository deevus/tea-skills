"""Organization-label Forgejo operations for bundled actions."""

from __future__ import annotations

from typing import Any

try:
    from .org_scope import OrgScope
except ImportError:
    from org_scope import OrgScope


def list_labels(org: OrgScope) -> list[dict[str, Any]]:
    result = org.get("labels")
    return result if isinstance(result, list) else []


def create(org: OrgScope, name: str, color: str, description: str = "") -> Any:
    return org.post("labels", {"name": name, "color": color, "description": description})
