"""MCP server (stdio): `python -m resume_agent.mcp_server`. Thin wrappers over the checker and evals."""
from __future__ import annotations

import json
import os
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from . import checker
from .evals import load_cases, misses, run_cases, score
from .profile import load_profile
from .skills import load_taxonomy

ROOT = Path(__file__).resolve().parents[1]

server = MCPServer("resume-agent")


def profile_path() -> Path:
    if env := os.environ.get("RESUME_AGENT_PROFILE"):
        return Path(env)
    real = ROOT / "profile/facts.yaml"
    return real if real.exists() else ROOT / "profile/facts.example.yaml"


@server.tool()
def check_resume(resume_json: str) -> dict:
    """Check a resume (JSON string) against the profile. Errors block the resume; warnings need review."""
    try:
        resume = json.loads(resume_json)
    except json.JSONDecodeError as e:
        raise ToolError(f"resume_json must be a JSON object: {e}") from e
    if not isinstance(resume, dict):
        raise ToolError("resume_json must be a JSON object")
    report = checker.check_resume(resume, load_profile(profile_path()),
                                  load_taxonomy(ROOT / "data/skills.yaml"))
    return {"issues": [{"level": i.level, "code": i.code, "where": i.where, "message": i.message}
                       for i in report.issues],
            "errors": len(report.errors), "warnings": len(report.issues) - len(report.errors)}


@server.tool()
def list_facts(status: str | None = None) -> list[dict]:
    """List profile facts (id, entity, text, status), optionally filtered by status."""
    return [{"id": f.id, "entity": f.entity, "text": f.text, "status": f.status}
            for f in load_profile(profile_path()).facts.values() if status in (None, f.status)]


@server.tool()
def run_evals() -> dict:
    """Run the checker evals (evals/cases.yaml against evals/profile.yaml) and return the score."""
    results = run_cases(load_cases(ROOT / "evals/cases.yaml"), load_profile(ROOT / "evals/profile.yaml"),
                        load_taxonomy(ROOT / "data/skills.yaml"))
    return {**score(results), "misses": misses(results)}


if __name__ == "__main__":
    server.run("stdio")
