#!/usr/bin/env python3
"""Check README inventory against public plugin resources."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ACTION_DOMAIN_NAMES = {
    "issues": "Issues",
    "milestones": "Milestones",
    "org-labels": "Organization Labels",
    "pull-requests": "Pull Requests",
}

REPOSITORY_TARGETING_DOMAIN_READMES = [
    Path("actions/issues/README.md"),
    Path("actions/pull-requests/README.md"),
    Path("actions/milestones/README.md"),
]
REPOSITORY_TARGETING_SKILLS = [
    Path("skills/issue-comments/SKILL.md"),
    Path("skills/issue-moderation/SKILL.md"),
    Path("skills/issue-dependencies/SKILL.md"),
    Path("skills/create-pull/SKILL.md"),
    Path("skills/review-pull/SKILL.md"),
    Path("skills/merge-pull/SKILL.md"),
    Path("skills/milestones/SKILL.md"),
]
STALE_ORIGIN_FIRST_FILES = [Path("README.md"), Path("actions/README.md"), Path("actions/internal/README.md")]


def skill_names(root: Path) -> list[str]:
    return sorted(path.parent.name for path in (root / "skills").glob("*/SKILL.md"))


def public_action_domain_readmes(root: Path) -> list[Path]:
    return sorted(path for path in (root / "actions").glob("*/README.md") if path.parent.name != "internal")


def check_readme_references_every_skill(root: Path = ROOT) -> list[str]:
    readme = (root / "README.md").read_text(encoding="utf-8")
    errors: list[str] = []

    for name in skill_names(root):
        if f"`{name}`" not in readme:
            errors.append(f"README.md does not reference skill `{name}`")

    return errors


def check_readme_references_public_action_domains(root: Path = ROOT) -> list[str]:
    readme = (root / "README.md").read_text(encoding="utf-8")
    errors: list[str] = []
    expected_relatives = {path.relative_to(root).as_posix() for path in public_action_domain_readmes(root)}
    linked_relatives = set(re.findall(r"actions/[A-Za-z0-9_-]+/README\.md", readme))

    for relative in sorted(expected_relatives):
        domain = Path(relative).parent.name
        expected_label = PUBLIC_ACTION_DOMAIN_NAMES.get(domain, domain)
        if f"]({relative})" not in readme:
            errors.append(f"README.md does not link to {relative}")
        if expected_label not in readme:
            errors.append(f"README.md does not mention action domain label {expected_label!r}")

    for relative in sorted(linked_relatives - expected_relatives):
        errors.append(f"README.md links to unknown public action domain {relative}")
    return errors


def _read_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return text.lower().replace("`", "")


def _contains_stale_origin_first_wording(text: str) -> bool:
    normalized = _normalized(text)
    return (
        "git remote get-url origin" in normalized
        or "origin-first" in normalized
        or "derive" in normalized
        and "origin remote" in normalized
    )


def check_repository_targeting_docs(root: Path = ROOT) -> list[str]:
    errors: list[str] = []

    for relative in STALE_ORIGIN_FIRST_FILES:
        if _contains_stale_origin_first_wording(_read_if_exists(root / relative)):
            errors.append(f"{relative.as_posix()} contains stale origin-first repository targeting wording")

    actions_readme = _read_if_exists(root / "actions" / "README.md")
    actions_readme_normalized = _normalized(actions_readme)
    for required in ["active-host-first", "--login", "--remote", "--repo", "codeberg", "self-hosted"]:
        if required not in actions_readme_normalized:
            errors.append(f"actions/README.md should document {required} repository targeting")

    for relative in REPOSITORY_TARGETING_DOMAIN_READMES:
        text = _normalized(_read_if_exists(root / relative))
        for flag in ["--login", "--remote", "--repo"]:
            if flag not in text:
                errors.append(f"{relative.as_posix()} should document {flag} repository targeting")
        if "active-host-first" not in text:
            errors.append(f"{relative.as_posix()} should mention active-host-first discovery")

    for relative in REPOSITORY_TARGETING_SKILLS:
        text = _normalized(_read_if_exists(root / relative))
        if not all(term in text for term in ["explicit scope flags", "--login", "--remote", "--repo"]):
            errors.append(f"{relative.as_posix()} should tell agents to pass explicit scope flags")

    return errors


def check_readme_matches_plugin_metadata(root: Path = ROOT) -> list[str]:
    readme = (root / "README.md").read_text(encoding="utf-8")
    plugin = json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    marketplace = json.loads((root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    errors: list[str] = []

    marketplace_name = marketplace["name"]
    plugin_name = plugin["name"]
    install_target = f"{plugin_name}@{marketplace_name}"

    if not readme.startswith(f"# {marketplace_name}\n"):
        errors.append(f"README.md title should match marketplace name `{marketplace_name}`")
    if install_target not in readme:
        errors.append(f"README.md should include Claude plugin install target `{install_target}`")
    marketplace_plugins = {entry.get("name") for entry in marketplace.get("plugins", [])}
    if plugin_name not in marketplace_plugins:
        errors.append(f"marketplace.json should include plugin `{plugin_name}`")

    return errors


def all_errors(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    errors.extend(check_readme_references_every_skill(root))
    errors.extend(check_readme_references_public_action_domains(root))
    errors.extend(check_readme_matches_plugin_metadata(root))

    errors.extend(check_repository_targeting_docs(root))
    return errors


def main() -> int:
    errors = all_errors(ROOT)
    if errors:
        for error in errors:
            print(f"README drift: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
