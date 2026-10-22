"""CLI: `python -m resume_agent check resume.json` and `python -m resume_agent evals`."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .checker import check_resume
from .evals import load_cases, misses, run_cases, score, write_results
from .profile import load_profile
from .skills import load_taxonomy

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="resume_agent")
    ap.add_argument("--profile", default=str(ROOT / "profile/facts.yaml"))
    ap.add_argument("--skills", default=str(ROOT / "data/skills.yaml"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="check a resume JSON against the profile")
    c.add_argument("resume")
    c.add_argument("--profile", dest="profile_sub")
    e = sub.add_parser("evals", help="run checker evals")
    e.add_argument("--cases", default=str(ROOT / "evals/cases.yaml"))
    e.add_argument("--out", default=str(ROOT / "evals/results.json"))
    e.add_argument("--eval-profile", default=str(ROOT / "evals/profile.yaml"))
    a = ap.parse_args(argv)

    if a.cmd == "evals":
        a.profile = a.eval_profile
    profile = load_profile(getattr(a, "profile_sub", None) or a.profile)
    taxonomy = load_taxonomy(a.skills)

    if a.cmd == "check":
        report = check_resume(json.loads(Path(a.resume).read_text(encoding="utf-8")), profile, taxonomy)
        for i in report.issues:
            print(f"{i.level.upper():7} {i.code:20} {i.where}: {i.message}")
        print(f"\n{len(report.errors)} error(s), {len(report.issues) - len(report.errors)} warning(s)")
        return 1 if report.errors else 0

    results = run_cases(load_cases(a.cases), profile, taxonomy)
    s = score(results)
    write_results(results, s, a.out)
    print(f"Bad cases caught: {s['caught']}/{s['bad_cases']} (recall {s['recall']})")
    print(f"Good cases with false positives: {s['false_positive_cases']}/{s['good_cases']}")
    for code, d in sorted(s["by_code"].items()):
        print(f"  {code:20} {d['caught']}/{d['expected']}")
    for m in misses(results):
        print(f"  {m['kind']} {m['id']}: expected {m['expect']} got {m['got']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
