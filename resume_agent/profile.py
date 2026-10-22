"""Profile: the candidate's verified facts, the single source of truth for resume claims."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

STATUSES = {"verified", "unconfirmed", "rejected"}


class ProfileError(ValueError):
    pass


@dataclass
class Metric:
    value: float
    unit: str = ""
    what: str = ""


@dataclass
class Scope:
    skill: str
    forbid: list[str] = field(default_factory=list)


@dataclass
class Fact:
    id: str
    entity: str
    text: str
    status: str
    metrics: list[Metric] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    scope: Scope | None = None
    attributes: dict[str, bool] = field(default_factory=dict)
    alts: list[str] = field(default_factory=list)
    source: str = ""


@dataclass
class Profile:
    facts: dict[str, Fact]
    positions: list[dict]
    education: list[dict]
    skills: list[str]

    def years(self) -> set[float]:
        """Years that appear in position or education dates (e.g. 'May 2027')."""
        import re
        text = " ".join(str(x.get("dates", "")) for x in self.positions + self.education)
        return {float(y) for y in re.findall(r"\b(?:19|20)\d{2}\b", text)}

    def verified_skills(self) -> set[str]:
        out = set(self.skills)
        for f in self.facts.values():
            if f.status == "verified":
                out.update(f.skills)
        return out


def _fact(raw: dict) -> Fact:
    if raw.get("status") not in STATUSES:
        raise ProfileError(f"fact {raw.get('id')!r}: invalid status {raw.get('status')!r}")
    scope = raw.get("scope")
    return Fact(
        id=raw["id"],
        entity=raw["entity"],
        text=raw["text"],
        status=raw["status"],
        metrics=[Metric(float(m["value"]), m.get("unit", ""), m.get("what", "")) for m in raw.get("metrics") or []],
        skills=list(raw.get("skills") or []),
        scope=Scope(scope["skill"], list(scope.get("forbid") or [])) if scope else None,
        attributes=dict(raw.get("attributes") or {}),
        alts=list(raw.get("alts") or []),
        source=raw.get("source", ""),
    )


def load_profile(path: str | Path) -> Profile:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    facts: dict[str, Fact] = {}
    for raw in data.get("facts") or []:
        fact = _fact(raw)
        if fact.id in facts:
            raise ProfileError(f"duplicate fact id {fact.id!r}")
        facts[fact.id] = fact
    return Profile(facts, data.get("positions") or [], data.get("education") or [], list(data.get("skills") or []))


def render_facts_md(profile: Profile) -> str:
    """Agent-readable view. Rejected facts are omitted so they can't leak back in."""
    lines = ["# Verified facts (cite these IDs)", ""]
    for f in profile.facts.values():
        if f.status == "verified":
            metrics = "; ".join(f"{m.value:g}{m.unit} {m.what}".strip() for m in f.metrics)
            extra = f" — metrics: {metrics}" if metrics else ""
            scope = f" — scope: {f.scope.skill} only as stated; never {', '.join(f.scope.forbid)}" if f.scope else ""
            lines.append(f"- [{f.id}] ({f.entity}) {f.text}{extra}{scope}")
    unconfirmed = [f for f in profile.facts.values() if f.status == "unconfirmed"]
    if unconfirmed:
        lines += ["", "# Unconfirmed — do not use; ask the user if a posting needs one", ""]
        lines += [f"- [{f.id}] {f.text}" for f in unconfirmed]
    return "\n".join(lines) + "\n"
