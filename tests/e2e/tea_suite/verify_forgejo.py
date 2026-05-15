from __future__ import annotations

from typing import Any
from urllib import parse

from actions.internal.tea_api import TeaConfig
from dokimasia.core.model import RunContext
from tests.e2e.tea_suite.provision import api_request


def list_issues(config: TeaConfig, org: str, repo: str) -> list[dict[str, Any]]:
    result = api_request(
        config,
        "GET",
        f"repos/{parse.quote(org, safe='')}/{parse.quote(repo, safe='')}/issues?state=all",
    )
    return result if isinstance(result, list) else []


def verify_issue_expectation(
    expectation: dict[str, Any], ctx: RunContext, issues: list[dict[str, Any]]
) -> dict[str, Any]:
    match = expectation.get("match", {})
    assertions = expectation.get("assert", {})
    candidates = issues
    if "title" in match:
        candidates = [issue for issue in candidates if issue.get("title") == match["title"]]

    expected_count = assertions.get("count")
    if expected_count is not None:
        expected_count_int = int(expected_count)
        if len(candidates) != expected_count_int:
            return {"passed": False, "message": f"expected {expected_count} issue(s), found {len(candidates)}"}
        if expected_count_int == 0:
            return {"passed": True, "message": ""}
    if not candidates:
        return {"passed": False, "message": "no matching issue found"}

    issue = candidates[0]
    if "state" in assertions and issue.get("state") != assertions["state"]:
        return {"passed": False, "message": f"expected state {assertions['state']}, found {issue.get('state')}"}
    if "body_equals_file" in assertions:
        expected_body = (ctx.workspace / assertions["body_equals_file"]).read_text(encoding="utf-8")
        if issue.get("body", "").strip() != expected_body.strip():
            return {"passed": False, "message": "issue body did not match file"}
    if expectation.get("id"):
        ctx.state[expectation["id"]] = issue
    return {"passed": True, "message": ""}


def verify_state(expectations: list[dict[str, Any]], ctx: RunContext, config: TeaConfig) -> list[dict[str, Any]]:
    issues_cache: list[dict[str, Any]] | None = None
    results: list[dict[str, Any]] = []
    for expectation in expectations:
        kind = expectation["kind"]
        if kind == "forgejo.issue":
            if issues_cache is None:
                issues_cache = list_issues(config, ctx.org, ctx.repo)
            results.append(verify_issue_expectation(expectation, ctx, issues_cache))
        else:
            results.append({"passed": False, "message": f"unsupported state verifier: {kind}"})
    return results
