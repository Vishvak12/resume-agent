# resume-agent

Tailors a resume to a job posting **without stating anything the candidate can't back up** —
and measures how well that guarantee holds.

Most AI resume tools rewrite toward the job description and leave fact-checking to you.
Here every bullet must cite verified fact IDs, and a deterministic checker blocks any claim
that isn't supported before a reviewer agent ever sees the resume.

## How it works

```
profile/facts.yaml ──► facts.md ──► Tailor agent ──► resume.json (bullets cite fact IDs)
                                                        │
data/skills.yaml ──► keyword layer                      ▼
                                                 Claim checker (code) ──errors──► back to tailor
                                                        │ warnings
                                                        ▼
                                                 Reviewer agent ──► verdict + gaps
```

- **Profile** — each fact has an ID, a status (verified / unconfirmed / rejected), metrics,
  skills, optional scope limits (e.g. *Azure: dev testing only*) and attributes
  (e.g. `production: true`). Rejected facts stay recorded so they can't creep back in.
- **Keyword layer** — a curated dictionary maps terms to canonical skills with a type
  (language / framework / tool / concept / generic). "Programming" is generic, so it can
  never land in a Languages line. Ambiguous words (Go, R, Swift, Rust) match only on exact case.
- **Claim checker** — pure Python. The summary is a list of cited sentences and is checked like bullets. Hard errors: missing citations, unverified facts, numbers
  not in the cited facts, technologies not in the cited facts, scope violations, generic or
  mistyped skills, wrong dates/titles/GPA. Warnings: unit mismatches ("812 carriers" vs
  "812 invoices") and escalation words ("production", "daily", "state-of-the-art") without a
  supporting attribute.
- **Agents** — `agents/tailor/AGENT.md` and `agents/reviewer/AGENT.md` define each agent's
  inputs and outputs. The reviewer never sees the tailor's reasoning.

## Results (deterministic checker only)

Eval set: 18 failure cases from real tailoring sessions, rewritten onto a fictional candidate
so no real resume is in the repo, plus 12 known-good bullets for the same candidate
(`evals/cases.yaml`, run against `evals/profile.yaml`).

| | Result |
|---|---|
| Known-bad bullets caught | **15 of 18 (83%)** |
| Known-good bullets wrongly flagged | 0 of 12 (small set, so not a false-positive rate) |
| Missed | all 3 `ENTAILMENT` cases: claims that say more than the fact without a wrong number or tool |

Run on a real tailored resume, the checker found one skill ("API design") that no verified
fact supported: an overclaim that had survived a manual review pass.

Building the evals also caught two checker bugs: hyphenated counts ("812-carrier",
"8-invoice") were invisible, and "12,416-feature" was misread as "12". Both now have tests.

## Usage

```bash
pip install -r requirements.txt
cp profile/facts.example.yaml profile/facts.yaml     # then replace with your own facts (git-ignored)
python -m resume_agent check examples/example_resume.json --profile profile/facts.example.yaml
python -m resume_agent evals                         # writes evals/results.json
pytest                                               # 52 tests
```

The example resume is meant to fail: it deploys a dev-testing-only Azure fact to production
and cites an unconfirmed Java fact, and the checker blocks both.

## Use as an MCP server

`python -m resume_agent.mcp_server` runs the checker as an MCP server over stdio, built on
the [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) (`mcp` 2.3.0, MIT).
It exposes three tools, each a wrapper over the functions above:

| Tool | Returns |
|---|---|
| `check_resume(resume_json)` | issues (`level`, `code`, `where`, `message`) plus error and warning counts |
| `list_facts(status=None)` | `id`, `entity`, `text`, `status` for each fact, optionally filtered by status |
| `run_evals()` | the CLI's eval summary (caught/bad, false positives/good, by code, misses); does not write `evals/results.json` |

The profile is `$RESUME_AGENT_PROFILE` if set, else `profile/facts.yaml`, else
`profile/facts.example.yaml`. `run_evals` always uses `evals/profile.yaml`.

VS Code (`.vscode/mcp.json`, included in this repo):

```json
{"servers": {"resume-agent": {"type": "stdio", "command": "python",
  "args": ["-m", "resume_agent.mcp_server"]}}}
```

`command` must be a Python that has `requirements.txt` installed.

## Roadmap

1. **Entailment check:** catch claims that go beyond their facts. Compare a Hugging Face
   NLI model against an LLM judge on accuracy and cost (target: the 3 current misses).
2. **Tailor + reviewer as separate API calls**, wired to the checker loop, with end-to-end
   evals on real postings (eligibility verdicts, unsupported-claim rate before vs after the checker).
3. **Onboarding:** extract facts from uploaded resumes as unconfirmed and surface conflicts.
4. **Job tracker and fit ranker**, then an MCP server and plugin.

Design: `docs/specs/2026-10-04-core-design.md`.
