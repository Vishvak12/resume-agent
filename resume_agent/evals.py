"""Checker evals: run labeled cases through the checker and score them."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from .checker import check_resume
from .profile import Profile
from .skills import Taxonomy


def case_to_resume(case: dict) -> dict:
    if "skills" in case:
        return {"skills": case["skills"]}
    if "experience" in case or "education" in case:
        return {k: case[k] for k in ("experience", "education") if k in case}
    bullet = {"text": case["text"], "facts": case["facts"]} if case.get("facts") else case["text"]
    return {"projects": [{"name": case["id"], "bullets": [bullet]}]}


def run_cases(cases: list[dict], profile: Profile, taxonomy: Taxonomy) -> list[dict]:
    out = []
    for c in cases:
        report = check_resume(case_to_resume(c), profile, taxonomy)
        out.append({"id": c["id"], "origin": c.get("origin", ""), "expect": c.get("expect", []),
                    "got": sorted({i.code for i in report.issues}),
                    "messages": [f"{i.code}: {i.message}" for i in report.issues]})
    return out


def score(results: list[dict]) -> dict:
    bad = [r for r in results if r["expect"]]
    good = [r for r in results if not r["expect"]]
    caught = [r for r in bad if set(r["expect"]) & set(r["got"])]
    by_code: dict[str, dict] = {}
    for r in bad:
        for code in r["expect"]:
            d = by_code.setdefault(code, {"expected": 0, "caught": 0})
            d["expected"] += 1
            d["caught"] += code in r["got"]
    return {
        "bad_cases": len(bad), "caught": len(caught),
        "recall": round(len(caught) / len(bad), 3) if bad else None,
        "good_cases": len(good), "false_positive_cases": sum(bool(r["got"]) for r in good),
        "by_code": by_code,
    }


def misses(results: list[dict]) -> list[dict]:
    """Bad cases the checker missed (MISSED) and good cases it flagged (FALSE+)."""
    out = []
    for r in results:
        missed = r["expect"] and not set(r["expect"]) & set(r["got"])
        if missed or (not r["expect"] and r["got"]):
            out.append({"kind": "MISSED" if missed else "FALSE+", "id": r["id"],
                        "expect": r["expect"], "got": r["got"]})
    return out


def load_cases(path: str | Path) -> list[dict]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def write_results(results: list[dict], summary: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps({"summary": summary, "results": results}, indent=2), encoding="utf-8")
