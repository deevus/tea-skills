from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_STATE: dict[str, Any] = {"dependencies": {}, "locks": {}}


@dataclass(frozen=True)
class MockForgejo:
    root: Path
    state_path: Path
    xdg_config_home: Path
    server: ThreadingHTTPServer
    thread: threading.Thread

    @property
    def base_url(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    def env(self) -> dict[str, str]:
        return {"XDG_CONFIG_HOME": str(self.xdg_config_home)}

    def load_state(self) -> dict[str, Any]:
        return load_mock_forgejo_state(self.state_path)

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class MockForgejoUsageError(ValueError):
    pass


def create_mock_forgejo(root: Path) -> MockForgejo:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    state_path = root / "state.json"
    save_mock_forgejo_state(state_path, dict(DEFAULT_STATE))

    handler = _handler_for(state_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, name="mock-forgejo", daemon=True)
    thread.start()

    xdg_config_home = root / "xdg"
    config_dir = xdg_config_home / "tea"
    config_dir.mkdir(parents=True, exist_ok=True)
    host, port = server.server_address
    (config_dir / "config.yml").write_text(
        f"logins:\n  - name: mock-forgejo\n    url: http://{host}:{port}\n    token: mock-token\n",
        encoding="utf-8",
    )

    return MockForgejo(root=root, state_path=state_path, xdg_config_home=xdg_config_home, server=server, thread=thread)


def load_mock_forgejo_state(state_path: Path) -> dict[str, Any]:
    return json.loads(Path(state_path).read_text(encoding="utf-8"))


def save_mock_forgejo_state(state_path: Path, state: dict[str, Any]) -> None:
    Path(state_path).write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _handler_for(state_path: Path):
    class MockForgejoHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            try:
                payload = self._json_body()
                response, status = handle_post(self.path, payload, state_path)
            except MockForgejoUsageError as error:
                self._write_json({"message": str(error)}, status=404)
                return
            self._write_json(response, status=status)

        def log_message(self, format: str, *args) -> None:  # noqa: A002
            return

        def _json_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length == 0:
                return {}
            raw = self.rfile.read(length).decode("utf-8")
            return json.loads(raw) if raw else {}

        def _write_json(self, payload: Any, *, status: int) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return MockForgejoHandler


def handle_post(path: str, payload: dict[str, Any], state_path: Path) -> tuple[Any, int]:
    parts = [part for part in urlparse(path).path.split("/") if part]
    prefix = ["api", "v1", "repos", "sh", "mock-repo", "issues"]
    if parts[: len(prefix)] != prefix or len(parts) < len(prefix) + 2:
        raise MockForgejoUsageError(f"unsupported POST path: {path}")

    issue = parts[len(prefix)]
    action = parts[len(prefix) + 1]
    state = load_mock_forgejo_state(state_path)

    if action == "dependencies":
        depends_on = int(payload["index"])
        dependencies = state.setdefault("dependencies", {})
        issue_dependencies = dependencies.setdefault(issue, [])
        if depends_on not in issue_dependencies:
            issue_dependencies.append(depends_on)
        save_mock_forgejo_state(state_path, state)
        return {"ok": True}, 201

    if action == "lock":
        state.setdefault("locks", {})[issue] = payload.get("lock_reason", "resolved")
        save_mock_forgejo_state(state_path, state)
        return {"ok": True}, 200

    raise MockForgejoUsageError(f"unsupported issue action: {action}")


__all__ = ["MockForgejo", "create_mock_forgejo", "load_mock_forgejo_state"]
