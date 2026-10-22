import asyncio
from pathlib import Path
import pytest
from mcp.server.mcpserver.exceptions import ToolError
from resume_agent import mcp_server

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture(autouse=True)
def example_profile(monkeypatch):
    monkeypatch.setenv("RESUME_AGENT_PROFILE", str(ROOT / "profile/facts.example.yaml"))

def test_check_resume_reports_example_errors():
    out = mcp_server.check_resume((ROOT / "examples/example_resume.json").read_text(encoding="utf-8"))
    assert out["errors"] == 2 and out["warnings"] == 1
    assert {i["code"] for i in out["issues"]} == {"SCOPE_VIOLATION", "ESCALATION_WORD", "FACT_NOT_VERIFIED"}
    assert set(out["issues"][0]) == {"level", "code", "where", "message"}

@pytest.mark.parametrize("bad", ["{not json", "[1, 2]"])
def test_check_resume_rejects_bad_input(bad):
    with pytest.raises(ToolError, match="JSON object"):
        mcp_server.check_resume(bad)

def test_list_facts_filters_by_status():
    facts = mcp_server.list_facts()
    assert len(facts) == 4 and set(facts[0]) == {"id", "entity", "text", "status"}
    assert [f["id"] for f in mcp_server.list_facts("unconfirmed")] == ["UNC-JAVA"]

def test_run_evals_matches_current_numbers(monkeypatch):
    monkeypatch.setenv("RESUME_AGENT_PROFILE", "does-not-exist.yaml")  # evals ignore it
    s = mcp_server.run_evals()
    assert (s["caught"], s["bad_cases"]) == (15, 18)
    assert (s["false_positive_cases"], s["good_cases"]) == (0, 12)
    assert len(s["misses"]) == 3

def test_profile_path_falls_back_to_example(monkeypatch, tmp_path):
    monkeypatch.delenv("RESUME_AGENT_PROFILE")
    monkeypatch.setattr(mcp_server, "ROOT", tmp_path)
    (tmp_path / "profile").mkdir()
    assert mcp_server.profile_path() == tmp_path / "profile/facts.example.yaml"
    (tmp_path / "profile/facts.yaml").write_text("")
    assert mcp_server.profile_path() == tmp_path / "profile/facts.yaml"

def test_server_registers_three_tools():
    names = {t.name for t in asyncio.run(mcp_server.server.list_tools())}
    assert names == {"check_resume", "list_facts", "run_evals"}
