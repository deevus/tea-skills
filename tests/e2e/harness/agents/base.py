from __future__ import annotations

from pathlib import Path
from typing import Protocol

from tests.e2e.harness.model import AgentRunResult


class AgentAdapter(Protocol):
    def run(
        self,
        prompt: str,
        workspace: Path,
        artifact_dir: Path,
        env: dict[str, str],
        timeout_seconds: int,
    ) -> AgentRunResult:
        ...
