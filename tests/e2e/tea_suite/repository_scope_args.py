from __future__ import annotations

REPOSITORY_SCOPE_FLAGS_WITH_VALUES = {"--login", "--remote", "--repo", "-l", "-R", "-r"}


def without_repository_scope_args(argv: list[str]) -> list[str]:
    """Return argv without repository-targeting flags and their values."""
    cleaned: list[str] = []
    skip_next = False
    for arg in argv:
        if skip_next:
            skip_next = False
            continue
        if arg in REPOSITORY_SCOPE_FLAGS_WITH_VALUES:
            skip_next = True
            continue
        if any(arg.startswith(f"{flag}=") for flag in REPOSITORY_SCOPE_FLAGS_WITH_VALUES):
            continue
        cleaned.append(arg)
    return cleaned
