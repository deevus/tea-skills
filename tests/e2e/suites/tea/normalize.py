from __future__ import annotations

from typing import Any

from tests.e2e.harness.model import AuditEvent

_MUTATING_TEA_VERBS = {
    "create", "edit", "close", "reopen", "delete", "del", "rm", "merge", "approve", "reject", "review"
}
_MUTATING_ACTION_WORDS = {
    "add", "remove", "edit", "lock", "unlock", "pin", "unpin", "create", "set", "cancel"
}


def _clean_action_root(action: str) -> str:
    clean = action.removesuffix(".py")
    if clean.startswith("actions/"):
        clean = clean[len("actions/"):]
    return "action." + clean.replace("/", ".")


def _tea_root(argv: list[str]) -> str:
    if not argv:
        return "tea"
    return "tea." + ".".join(part for part in argv[:2] if not part.startswith("-"))


def _tea_mutates(argv: list[str]) -> bool:
    if not argv:
        return False
    return any(part in _MUTATING_TEA_VERBS for part in argv[:3])


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
