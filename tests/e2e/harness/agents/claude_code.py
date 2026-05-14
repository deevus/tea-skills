from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Iterable

from tests.e2e.harness.model import AgentRunResult, TraceEvent

_SKILL_TEXT = re.compile(r"\bUsing\s+([A-Za-z0-9_-]+)\b")


def _extract_texts(obj: object) -> Iterable[str]:
    if isinstance(obj, dict):
        if obj.get("type") == "text" and isinstance(obj.get("text"), str):
            yield obj["text"]
        for value in obj.values():
            yield from _extract_texts(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _extract_texts(item)


def _decode_subprocess_output(output: str | bytes | None) -> str:
    if isinstance(output, str):
        return output
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return ""


def parse_claude_stream_json(lines: list[str]) -> list[TraceEvent]:
    events: list[TraceEvent] = []
    seen_skills: set[str] = set()
    for line in lines:
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue

        for text in _extract_texts(raw):
            events.append(TraceEvent(kind="agent.message", text=text, raw=raw))
            match = _SKILL_TEXT.search(text)
            if match and match.group(1) not in seen_skills:
                seen_skills.add(match.group(1))
                events.append(TraceEvent(kind="skill.loaded", name=match.group(1), raw=raw))

        for content in raw.get("message", {}).get("content", []) if isinstance(raw, dict) else []:
            if isinstance(content, dict) and content.get("type") == "tool_use":
                tool_name = str(content.get("name"))
                events.append(TraceEvent(kind="tool.call", tool=tool_name, raw=raw))
                tool_input = content.get("input", {})
                if tool_name.lower() == "skill" and isinstance(tool_input, dict):
                    skill = tool_input.get("skill") or tool_input.get("name")
                    if isinstance(skill, str) and skill not in seen_skills:
                        seen_skills.add(skill)
                        events.append(TraceEvent(kind="skill.loaded", name=skill, raw=raw))
    return events


class ClaudeCodeAdapter:
    def __init__(self, claude_bin: str = "claude", plugin_dir: Path | None = None):
        self.claude_bin = claude_bin
        self.plugin_dir = plugin_dir

    def run(
        self,
        prompt: str,
        workspace: Path,
        artifact_dir: Path,
        env: dict[str, str],
        timeout_seconds: int,
    ) -> AgentRunResult:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = artifact_dir / "agent.stdout.jsonl"
        stderr_path = artifact_dir / "agent.stderr.txt"
        command = [
            self.claude_bin,
            "--print",
            "--output-format",
            "stream-json",
            "--verbose",
            "--permission-mode",
            "bypassPermissions",
        ]
        if self.plugin_dir is not None:
            command.extend(["--plugin-dir", str(self.plugin_dir)])
        command.append(prompt)

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
        lines = stdout.splitlines()
        return AgentRunResult(
            exit_code=exit_code,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            raw_trace_path=stdout_path,
            trace_events=parse_claude_stream_json(lines),
            duration_seconds=time.monotonic() - started,
            timed_out=timed_out,
        )
