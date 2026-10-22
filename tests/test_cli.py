import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def run_cli(tmp_path, resume):
    f = tmp_path / "resume.json"; f.write_text(json.dumps(resume))
    return subprocess.run([sys.executable, "-m", "resume_agent", "check", str(f),
                           "--profile", str(ROOT / "tests/fixtures/profile/facts.yaml")],
                          cwd=ROOT, capture_output=True, text=True)

def test_cli_exits_1_and_reports_errors(tmp_path):
    p = run_cli(tmp_path, {"projects": [{"name": "x", "bullets": ["Built a thing."]}]})
    assert p.returncode == 1 and "CITATION_MISSING" in p.stdout

def test_cli_exits_0_on_clean_resume(tmp_path):
    p = run_cli(tmp_path, {"projects": [{"name": "x", "bullets": [{"text": "Used Azure for testing.", "facts": ["NOVA-AZURE"]}]}]})
    assert p.returncode == 0
