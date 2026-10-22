"""Claim checker: verify every resume claim against the profile. Code, not prompts."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .profile import Fact, Profile
from .skills import Taxonomy

NUMBER = re.compile(r"(?<![\w.\-/@])~?(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(\+|%|x)?(?![\w/]|[.,]\d)")
ESCALATION = {"production": "production", "led": "led", "owned": "owned", "daily": "daily",
              "state-of-the-art": "sota", "sota": "sota"}
STOPWORDS = {"on", "of", "in", "and", "across", "with", "to", "for", "by", "the", "a", "an", "over", "from", "at", "vs"}


@dataclass
class Issue:
    level: str   # "error" | "warning"
    code: str
    where: str
    message: str


@dataclass
class Report:
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "error"]

    def add(self, level: str, code: str, where: str, message: str) -> None:
        self.issues.append(Issue(level, code, where, message))


def _canon(tax: Taxonomy, name: str) -> str:
    s = tax.lookup(name)
    return s.canonical if s else name


FRACTION = re.compile(r"(?<![\w.\-/@])(\d+)/(\d+)(?![\w/]|[.,]\d)")


def _check_numbers(text: str, facts: list[Fact], where: str, r: Report, years: set[float] = frozenset()) -> None:
    metrics = [m for f in facts for m in f.metrics]
    values = {mt.value for mt in metrics}
    for fm in FRACTION.finditer(text):
        missing = [g for g in fm.groups() if float(g) not in values]
        if missing:
            r.add("error", "NUMBER_UNSUPPORTED", where, f"{fm.group(0)!r}: {missing} not in the cited facts")
    for m in NUMBER.finditer(text):
        value = float(m.group(1).replace(",", ""))
        if value in years and not m.group(2):
            continue
        hit = next((mt for mt in metrics if abs(mt.value - value) <= 1e-6 * max(1.0, abs(value))), None)
        if hit is None:
            r.add("error", "NUMBER_UNSUPPORTED", where, f"{m.group(0)!r} is not a metric of the cited facts")
            continue
        nxt = re.match(r"(?:\s+|-)([A-Za-z][\w-]*)", text[m.end():])
        if nxt:
            word = nxt.group(1).lower()
            what = {w.rstrip("s") for w in hit.what.lower().split()} | {hit.unit.lower()}
            if word not in STOPWORDS and word.rstrip("s") not in what:
                r.add("warning", "UNIT_MISMATCH", where, f"{m.group(0)} {word!r} — fact says {hit.value:g} {hit.what}")


def _check_bullet(b, where: str, profile: Profile, tax: Taxonomy, r: Report) -> None:
    if isinstance(b, str) or not b.get("facts"):
        r.add("error", "CITATION_MISSING", where, "bullet cites no fact IDs")
        return
    text, cited = b["text"], []
    for fid in b["facts"]:
        f = profile.facts.get(fid)
        if f is None:
            r.add("error", "FACT_UNKNOWN", where, f"unknown fact {fid}")
        elif f.status != "verified":
            r.add("error", "FACT_NOT_VERIFIED", where, f"{fid} is {f.status}")
        else:
            cited.append(f)
    if not cited:
        return
    _check_numbers(text, cited, where, r, profile.years())
    allowed = {_canon(tax, s) for f in cited for s in f.skills}
    mentioned = {m.canonical for m in tax.match(text) if m.type != "generic"}
    for s in sorted(mentioned - allowed):
        r.add("error", "SKILL_UNSUPPORTED", where, f"{s} is not in the cited facts")
    lower = text.lower()
    for f in cited:
        if f.scope and _canon(tax, f.scope.skill) in mentioned:
            bad = [w for w in f.scope.forbid if re.search(rf"\b{re.escape(w)}\b", lower)]
            if bad:
                r.add("error", "SCOPE_VIOLATION", where, f"{f.scope.skill} is scoped; found {bad}")
    for word, attr in ESCALATION.items():
        if re.search(rf"(?<![\w-]){re.escape(word)}(?![\w-])", lower) and not any(f.attributes.get(attr) for f in cited):
            r.add("warning", "ESCALATION_WORD", where, f"{word!r} needs a fact with attribute {attr}")


def _split_items(value: str) -> list[tuple[str, list[str]]]:
    items, depth, cur = [], 0, ""
    for ch in value + ",":
        if ch == "," and depth == 0:
            if cur.strip():
                head, _, inner = cur.strip().partition("(")
                items.append((head.strip(), [x.strip() for x in inner.rstrip(")").split(",") if x.strip()]))
            cur = ""
            continue
        depth += ch == "("
        depth -= ch == ")"
        cur += ch
    return items


def _check_skills(lines, profile: Profile, tax: Taxonomy, r: Report) -> None:
    verified = {_canon(tax, s) for s in profile.verified_skills()}
    for label, value in lines:
        is_lang = "language" in label.lower()
        for head, inner in _split_items(value):
            where = f"skills/{label}/{head}"
            for term, required in [(head, True)] + [(x, False) for x in inner]:
                s = tax.lookup(term)
                if s is None:
                    if required:
                        r.add("warning", "SKILLS_UNKNOWN", where, f"{term!r} not in the skill dictionary")
                    continue
                if s.type == "generic":
                    r.add("error", "SKILLS_GENERIC", where, f"{term!r} is a generic term, not a skill")
                    continue
                if is_lang and required and s.type != "language":
                    r.add("error", "SKILLS_WRONG_TYPE", where, f"{s.canonical} is a {s.type}, not a language")
                if not is_lang and required and s.type == "language":
                    r.add("warning", "SKILLS_MIXED_TYPES", where, f"{s.canonical} is a language; list it on the Languages line")
                if s.canonical not in verified:
                    r.add("error", "SKILLS_UNSUPPORTED", where, f"{s.canonical} is not backed by a verified fact")


def _check_fields(resume: dict, profile: Profile, r: Report) -> None:
    by_org = {p["org"]: p for p in profile.positions}
    for e in resume.get("experience", []):
        p = by_org.get(e.get("org"))
        if p is None:
            r.add("error", "FIELD_MISMATCH", f"experience/{e.get('org')}", "position not in profile")
            continue
        for k in ("role", "dates"):
            if e.get(k) and e[k] != p.get(k):
                r.add("error", "FIELD_MISMATCH", f"experience/{e['org']}/{k}", f"{e[k]!r} ≠ profile {p.get(k)!r}")
    by_school = {ed["school"]: ed for ed in profile.education}
    for e in resume.get("education", []):
        ed = by_school.get(e.get("school"))
        if ed is None:
            r.add("error", "FIELD_MISMATCH", f"education/{e.get('school')}", "school not in profile")
            continue
        if e.get("dates") and e["dates"] != ed.get("dates"):
            r.add("error", "FIELD_MISMATCH", f"education/{e['school']}/dates", f"{e['dates']!r} ≠ {ed.get('dates')!r}")
        gpa = re.search(r"GPA:\s*([\d.]+/\d+)", e.get("degree", ""))
        if gpa and ed.get("gpa") and gpa.group(1) != ed["gpa"]:
            r.add("error", "FIELD_MISMATCH", f"education/{e['school']}/gpa", f"{gpa.group(1)} ≠ {ed['gpa']}")


def check_resume(resume: dict, profile: Profile, taxonomy: Taxonomy) -> Report:
    r = Report()
    _check_fields(resume, profile, r)
    summary = resume.get("summary")
    if isinstance(summary, str) and summary.strip():
        r.add("error", "SUMMARY_UNCITED", "summary", "summary must be a list of {text, facts} sentences")
    elif isinstance(summary, list):
        for i, s in enumerate(summary):
            _check_bullet(s, f"summary/{i}", profile, taxonomy, r)
    for section in ("experience", "projects"):
        for entry in resume.get(section, []):
            name = entry.get("org") or entry.get("name")
            for i, b in enumerate(entry.get("bullets", [])):
                _check_bullet(b, f"{section}/{name}/{i}", profile, taxonomy, r)
    _check_skills(resume.get("skills", []), profile, taxonomy, r)
    return r
