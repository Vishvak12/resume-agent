"""Keyword layer: map terms to canonical skills with a type, and find skills in text."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Skill:
    canonical: str
    type: str
    case_sensitive: bool = False


@dataclass(frozen=True)
class Match:
    canonical: str
    type: str
    start: int
    end: int


@dataclass
class Taxonomy:
    _by_term: dict[str, Skill] = field(default_factory=dict)  # lowercase term -> skill (case-insensitive)
    _exact: dict[str, Skill] = field(default_factory=dict)    # exact term -> skill (case-sensitive)
    _pattern: re.Pattern | None = None

    def lookup(self, term: str) -> Skill | None:
        term = term.strip()
        return self._exact.get(term) or self._by_term.get(term.lower())

    def match(self, text: str) -> list[Match]:
        """Longest-first, non-overlapping matches on word boundaries."""
        out: list[Match] = []
        for m in self._pattern.finditer(text):
            skill = self.lookup(m.group(0))
            if skill:
                out.append(Match(skill.canonical, skill.type, m.start(), m.end()))
        return out


def load_taxonomy(path: str | Path) -> Taxonomy:
    tax = Taxonomy()
    terms: list[tuple[str, bool]] = []
    for e in yaml.safe_load(Path(path).read_text(encoding="utf-8")):
        skill = Skill(e["canonical"], e["type"], bool(e.get("case_sensitive")))
        for term in [e["canonical"], *(e.get("aliases") or [])]:
            if skill.case_sensitive:
                tax._exact[term] = skill
            else:
                tax._by_term[term.lower()] = skill
            terms.append((term, skill.case_sensitive))
    parts = []
    for term, cs in sorted(terms, key=lambda t: -len(t[0])):  # longest first
        esc = re.escape(term)
        parts.append(esc if cs else f"(?i:{esc})")
    tax._pattern = re.compile(r"(?<![\w.+/-])(?:" + "|".join(parts) + r")(?![\w+/&]|-\w)")
    return tax
