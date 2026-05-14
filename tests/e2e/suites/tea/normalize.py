from __future__ import annotations

from typing import Any

from tests.e2e.harness.model import AuditEvent

_MUTATING_TEA_VERBS = {
    "create", "edit", "close", "reopen", "delete", "del", "rm", "merge", "approve", "reject", "review"
}
_MUTATING_ACTION_WORDS = {
    "add", "remove", "edit", "lock", "unlock", "pin", "unpin", "create", "set", "cancel"
}
_TEA_VALUE_OPTIONS = {
    "--add-assignees", "--add-labels", "--assignee", "--assignees", "--author", "--base", "--body",
    "--deadline", "--description", "--fields", "--head", "--keyword", "--kind", "--labels", "--login",
    "--milestone", "--milestones", "--output", "--remote", "--remove-assignees", "--remove-labels",
    "--repo", "--state", "--title", "-R", "-o", "-r",
}
_TEA_COMMAND_ALIASES = {
    "i": "issues",
    "issue": "issues",
    "pr": "pulls",
    "pull": "pulls",
}
_TEA_VERB_ALIASES = {
    "c": "create",
    "m": "merge",
}


def _clean_action_root(action: str) -> str:
    clean = action.removesuffix(".py")
    if clean.startswith("actions/"):
        clean = clean[len("actions/"):]
    return "action." + clean.replace("/", ".")


def _tea_command_parts(argv: list[str]) -> list[str]:
    parts: list[str] = []
    skip_next = False
    for arg in argv:
        if skip_next:
            skip_next = False
            continue
        if arg == "--":
            break
        if arg.startswith("-"):
            option = arg.split("=", 1)[0]
            if option in _TEA_VALUE_OPTIONS and "=" not in arg:
                skip_next = True
            continue
        if not parts:
            parts.append(_TEA_COMMAND_ALIASES.get(arg, arg))
        else:
            parts.append(_TEA_VERB_ALIASES.get(arg, arg))
        if len(parts) == 2:
            break
    return parts


def _tea_root(argv: list[str]) -> str:
    parts = _tea_command_parts(argv)
    if not parts:
        return "tea"
    return "tea." + ".".join(parts)


def _tea_mutates(argv: list[str]) -> bool:
    return any(part in _MUTATING_TEA_VERBS for part in _tea_command_parts(argv))


def _action_mutates(root: str) -> bool:
    tail = root.rsplit(".", 1)[-1]
    return any(word in tail.split("-") for word in _MUTATING_ACTION_WORDS)


def normalize_raw_audit_event(raw: dict[str, Any]) -> AuditEvent:
    source = str(raw.get("source") or "tea")
    argv = [str(arg) for arg in raw.get("argv", [])]
    cwd = str(raw.get("cwd") or "")
    exit_code = int(raw.get("exit_code", 0))

    if source == "tea-skills-action":
        root = _clean_action_root(str(raw.get("action") or "actions/unknown"))
        mutates = _action_mutates(root)
    else:
        root = _tea_root(argv)
        mutates = _tea_mutates(argv)

    return AuditEvent(root=root, argv=argv, cwd=cwd, exit_code=exit_code, mutates=mutates, source=source, raw=raw)
