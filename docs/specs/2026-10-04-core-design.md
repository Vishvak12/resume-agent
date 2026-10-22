# Resume Agent — Core Design (Part 1 of 3)

Status: draft for review · Owner: Vishvaksen Pendyala · 2026-10-04

## Goal

Tailor a resume to a job posting without ever stating something the candidate
can't back up, and measure how well that guarantee holds.

Parts: (1) **core** — this spec; (2) job tracker + fit ranker; (3) MCP server +
plugin distribution. Part 1 must work and be measured before 2 or 3 start.

## Principles

1. Every resume claim traces to a verified fact ID. No ID, no claim.
2. Enforcement is code; prompts only shape behavior.
3. Agents are separate model calls with scoped context. The reviewer never sees
   the tailor's reasoning.
4. Deterministic first, model last (and cached) — for keywords and for checks.
5. Every check exists because of an observed failure, and has an eval case.

## Section 1 — Profile

`profile/facts.yaml` is the source of truth; `facts.md` is generated for agents.

Fact fields: `id`, `entity`, `text`, `status` (verified | unconfirmed |
rejected), `metrics` [{value, unit, what}], `skills` [canonical names],
`scope` {skill, forbid: [words]}, `attributes` {production, led, ...: bool},
`alts` [approved phrasings], `source`.

Also in the profile: `positions` (org, role, location, dates), `education`
(school, degree, dates, gpa), `skills` (verified standalone skills).

Rejected facts stay in the file so re-uploads can't revive them.
Onboarding (later): extract facts from uploaded resumes as `unconfirmed`,
surface conflicts, user confirms.

## Section 2 — Keyword layer

Posting keywords → canonical skills with a type: language | framework | tool |
concept | generic. Resolution order: curated dictionary with aliases → embedding
nearest-neighbor (later) → LLM for the residue, cached into the dictionary →
human review queue. Ambiguous words (Go, R, Swift, Spring, Rust) match only on
exact case.

Placement rules: the Languages line accepts `language` only; `generic` terms
never enter skill lines; a keyword enters the resume only if a verified fact
backs it; use the posting's spelling when the skill is equivalent.
Output: matched (with backing fact) / missing-gap / missing-fixable.

## Section 3 — Claim checker

Input: resume JSON where every bullet is `{text, facts: [ids]}`.

Hard errors (block the build):
- `CITATION_MISSING`, `FACT_UNKNOWN`, `FACT_NOT_VERIFIED`
- `NUMBER_UNSUPPORTED` — every standalone number must match a metric of a cited fact
- `SKILL_UNSUPPORTED` — every skill mentioned must be in a cited fact's skills
- `SCOPE_VIOLATION` — a scoped skill appears with a forbidden widening word
- `SKILLS_GENERIC`, `SKILLS_WRONG_TYPE`, `SKILLS_UNSUPPORTED` — skills section
- `FIELD_MISMATCH` — org, role, dates, GPA differ from the profile

Warnings (to the reviewer):
- `UNIT_MISMATCH` — word after a number isn't in the metric's description
- `ESCALATION_WORD` — production / led / owned / daily / state-of-the-art etc.
  without a matching fact attribute
- `ENTAILMENT` — bullet says more than its facts (NLI model or LLM; not in v0)

Loop: errors return to the tailor with reasons; after 2 failed fixes the bullet
is dropped.

## Section 4 — Agents and evals (proposed; not yet reviewed)

Tailor: input = posting brief + facts.md + keyword report; output = resume JSON
with citations. Reviewer: input = posting brief + facts.md + built resume +
checker report — never tailor notes; output = verdict (Apply / Apply after
fixes / Long shot / Don't apply), fit score, blockers, requirement coverage
with fact IDs, gaps vs fixes.

Evals:
- **Checker evals** (v0): labeled bullets — known-bad from real sessions and
  known-good — scored for per-code recall and false-positive rate.
- **End-to-end evals** (v1): postings with expected eligibility verdicts and
  required keywords; headline metric = unsupported-claim rate before vs after
  the checker.

## Out of scope for Part 1

Job ingestion, ranking, multi-user accounts, MCP packaging, UI.
