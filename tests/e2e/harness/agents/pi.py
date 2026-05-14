from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from tests.e2e.harness.model import AgentRunResult, TraceEvent


def _decode_subprocess_output(output: str | bytes | None) -> str:
    if isinstance(output, str):
        return output
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return ""


def _content_texts(content: Any) -> list[str]:
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        texts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                texts.append(item["text"])
        return texts
    return []


def _skill_from_read_path(path: str, skills_dir: Path) -> str | None:
    try:
        relative = Path(path).resolve().relative_to(skills_dir.resolve())
    except ValueError:
        return None
    parts = relative.parts
    if len(parts) == 2 and parts[1] == "SKILL.md":
        return parts[0]
    return None


def parse_pi_json_events(lines: list[str], skills_dir: Path) -> list[TraceEvent]:
    events: list[TraceEvent] = []
    seen_skills: set[str] = set()
    for line in lines:
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue

        event_type = raw.get("type") if isinstance(raw, dict) else None
        if event_type == "tool_execution_start":
            tool_name = str(raw.get("toolName") or "")
            events.append(TraceEvent(kind="tool.call", tool=tool_name, raw=raw))
            args = raw.get("args", {})
            path = args.get("path") if isinstance(args, dict) else None
            if tool_name == "read" and isinstance(path, str):
                skill = _skill_from_read_path(path, skills_dir)
                if skill and skill not in seen_skills:
                    seen_skills.add(skill)
                    events.append(TraceEvent(kind="skill.loaded", name=skill, raw=raw))

        if event_type in {"message_start", "message_update", "message_end"}:
            message = raw.get("message", {})
            if isinstance(message, dict):
                for text in _content_texts(message.get("content")):
                    events.append(TraceEvent(kind="agent.message", text=text, raw=raw))
            assistant_event = raw.get("assistantMessageEvent")
            if isinstance(assistant_event, dict) and isinstance(assistant_event.get("delta"), str):
                events.append(TraceEvent(kind="agent.message", text=assistant_event["delta"], raw=raw))
    return events


class PiAdapter:
    def __init__(self, pi_bin: str = "pi", skills_dir: Path | None = None):
        self.pi_bin = pi_bin
        self.skills_dir = skills_dir

    def run(
        self,
        prompt: str,
        workspace: Path,
        artifact_dir: Path,
        env: dict[str, str],
        timeout_seconds: int,
    ) -> AgentRunResult:
        if self.skills_dir is None:
            raise ValueError("PiAdapter requires skills_dir so tests use the current checkout's skills")

        artifact_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = artifact_dir / "agent.stdout.jsonl"
        stderr_path = artifact_dir / "agent.stderr.txt"
        command = [
            self.pi_bin,
            "--print",
            "--mode",
            "json",
            "--no-session",
            "--no-skills",
            "--skill",
            str(self.skills_dir),
            prompt,
        ]

        started = time.monotonic()
        merged_env = os.environ.copy()
        merged_env.update(env)
        try:
            completed = subprocess.run(
                command,
                cwd=workspace,
                env=merged_env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_seconds,
                check=False,
            )
            timed_out = False
            stdout = _decode_subprocess_output(completed.stdout)
            stderr = _decode_subprocess_output(completed.stderr)
            exit_code = completed.returncode
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout = _decode_subprocess_output(exc.stdout)
            stderr = _decode_subprocess_output(exc.stderr)
            exit_code = 124

        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        return AgentRunResult(
            exit_code=exit_code,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            raw_trace_path=stdout_path,
            trace_events=parse_pi_json_events(stdout.splitlines(), self.skills_dir),
            duration_seconds=time.monotonic() - started,
            timed_out=timed_out,
        )
