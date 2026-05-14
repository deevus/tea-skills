from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TraceEvent:
    kind: str
    name: str | None = None
    tool: str | None = None
    text: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AuditEvent:
    root: str
    argv: list[str]
    cwd: str
    exit_code: int
    mutates: bool
    source: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRunResult:
    exit_code: int
    stdout_path: Path
    stderr_path: Path
    raw_trace_path: Path | None
    trace_events: list[TraceEvent]
    duration_seconds: float
    timed_out: bool = False


@dataclass
class Scenario:
    name: str
    prompt: str
    tags: list[str] = field(default_factory=list)
    fixtures: dict[str, Any] = field(default_factory=dict)
    expect_trace: dict[str, Any] = field(default_factory=dict)
    expect_audit: dict[str, Any] = field(default_factory=dict)
    expect_state: list[dict[str, Any]] = field(default_factory=list)
    outputs: dict[str, str] = field(default_factory=dict)
    execution: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)


@dataclass
class RunContext:
    run_id: str
    org: str
    repo: str
    workspace: Path
    artifact_dir: Path | None = None
    outputs: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)

    def template_data(self) -> dict[str, Any]:
        return {
            "run": {"id": self.run_id},
            "org": self.org,
            "repo": self.repo,
            "workspace": str(self.workspace),
            "context": self.outputs,
            "state": self.state,
        }


@dataclass
class ScenarioResult:
    name: str
    passed: bool
    failure_class: str | None = None
    message: str = ""
    trace_events: list[TraceEvent] = field(default_factory=list)
    audit_events: list[AuditEvent] = field(default_factory=list)
