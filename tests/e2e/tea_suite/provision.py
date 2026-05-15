from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import parse, request

from actions.internal.tea_api import TeaConfig, read_tea_config


@dataclass
class ForgejoRun:
    run_id: str
    org: str
    repo: str
    clone_url: str
    workspace: Path
    artifact_dir: Path
    config: TeaConfig




def assert_safe_e2e_resource(name: str, run_id: str) -> None:
    if not name.startswith("tea-e2e-") or run_id not in name:
        raise ValueError(f"refusing to delete non-e2e resource: {name}")


def api_request(config: TeaConfig, method: str, endpoint: str, body: bytes | None = None) -> Any:
    url = f"{config.base_url.rstrip('/')}/api/v1/{endpoint.lstrip('/')}"
    headers = {"Authorization": f"token {config.token}", "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=body, headers=headers, method=method)
    with request.urlopen(req) as response:
        raw = response.read()
    if not raw:
        return None
    return json.loads(raw.decode("utf-8"))


def create_org_and_repo(root: Path, run_id: str) -> ForgejoRun:
    config = read_tea_config()
    org = f"tea-e2e-{run_id}"
    repo = "repo"
    artifact_dir = root / "artifacts"
    workspace = root / "workspace" / repo
    artifact_dir.mkdir(parents=True, exist_ok=True)

    org_created = False
    repo_created = False
    try:
        api_request(config, "POST", "orgs", json.dumps({"username": org, "full_name": org}).encode("utf-8"))
        org_created = True
        created = api_request(
            config,
            "POST",
            f"orgs/{parse.quote(org, safe='')}/repos",
            json.dumps({"name": repo, "auto_init": True}).encode("utf-8"),
        )
        repo_created = True
        clone_url = created.get("clone_url") or created.get("ssh_url")
        if not clone_url:
            raise RuntimeError("created repository did not include a clone_url or ssh_url")
        workspace.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", clone_url, str(workspace)], check=True)
        (workspace / "AGENTS.md").write_text("# Repository context\n\nThis repository is hosted on Forgejo.\n", encoding="utf-8")
        return ForgejoRun(run_id, org, repo, clone_url, workspace, artifact_dir, config)
    except Exception:
        if org_created:
            assert_safe_e2e_resource(org, run_id)
            if repo_created:
                try:
                    api_request(config, "DELETE", f"repos/{parse.quote(org, safe='')}/{parse.quote(repo, safe='')}")
                except Exception:
                    pass
            try:
                api_request(config, "DELETE", f"orgs/{parse.quote(org, safe='')}")
            except Exception:
                pass
        raise


def cleanup_run(run: ForgejoRun, keep_remote: bool = False) -> None:
    if run.workspace.exists():
        shutil.rmtree(run.workspace.parent, ignore_errors=True)
    if keep_remote:
        return
    assert_safe_e2e_resource(run.org, run.run_id)
    try:
        api_request(run.config, "DELETE", f"repos/{parse.quote(run.org, safe='')}/{parse.quote(run.repo, safe='')}")
    finally:
        api_request(run.config, "DELETE", f"orgs/{parse.quote(run.org, safe='')}")
