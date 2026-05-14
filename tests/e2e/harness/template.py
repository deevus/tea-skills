from __future__ import annotations

import re
from typing import Any

_TOKEN = re.compile(r"{{\s*([A-Za-z0-9_.-]+)\s*}}")


def resolve_dotted(path: str, data: dict[str, Any]) -> Any:
    value: Any = data
    for part in path.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
            continue
        raise KeyError(path)
    return value


def render_template(text: str, data: dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return str(resolve_dotted(key, data))

    return _TOKEN.sub(replace, text)
