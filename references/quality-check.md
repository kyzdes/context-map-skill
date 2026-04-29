# Context Map Quality Check

Run this checklist before reporting completion. Most of it is enforced mechanically by `scripts/validate_context_map.py`; the rest is human judgement the skill must apply.

## Mechanical Checks (must pass)

Run:

```bash
python3 scripts/validate_context_map.py /path/to/project/context-map-<slug>
```

The validator checks:

- Frontmatter is present, parseable YAML, and matches every field and enum in `references/schema.md`.
- `project_slug` matches the folder suffix.
- Required split files exist for the declared `scale` (see `references/schema.md` → `File Presence By Scale`).
- Each split file has exactly one canonical section header and table of the expected shape.
- All `ID` values in each file are unique and match the required format.
- Enum columns (`Priority`, `Status`, `Type`, `Confidence`, `Agent-Ready`, etc.) contain only allowed values.
- Dates are ISO `YYYY-MM-DD`.
- `last_updated` and `last_verified_vs_code` are not in the future.

Do not claim completion until the validator exits 0.

## Content Checks (skill applies judgement)

Must be true before reporting success:

- Every file is written in English; non-English terms only appear for proper nouns, justified in `Confidence Notes`.
- `Project Identity` describes the project in engineering terms (stack, entry points, main surfaces), not marketing copy.
- `Current Phase` reflects real git signals, not vague placeholders like "active development".
- `Read First By Task Type` covers the most common change types the project actually sees.
- `Confidence Notes` has at least one row for any non-trivial project, documenting stale/duplicate/conflicting docs or inferred claims.
- `Known Issues`, `Decisions`, and `Tasks / Next Work` are populated when evidence exists; if empty, prefer one row explaining why rather than an empty table.
- Commands in `Run / Test`, `Local Development`, `Deployment` are copy-pasteable and match the repo.
- No secrets, live tokens, passwords, or private keys appear anywhere.
- Root `context-map.md` remains concise. For L/XL projects, deep detail lives in `architecture.md` or `domains/*.md`.

## Good Traits

- Concrete paths and commands, not vague descriptions.
- Tables for routing, API surfaces, settings, and validation.
- Short architecture diagrams when they accelerate understanding.
- Active project memory: known issues, decisions, current phase reflect recent work.
- Tasks have IDs, status, agent-readiness, and validation notes.
- Clear distinction between `verified` and `inferred` claims, flagged in `Confidence Notes`.
- Root map points to deep docs instead of duplicating them.

## Anti-Patterns

- Marketing copy instead of engineering orientation.
- Copying README wholesale.
- Full source-code snippets when a file path is enough.
- Huge lists of every component with no routing guidance.
- Using stale git history as the main status signal; the `Current Phase` block is agg signals, not a commit log.
- Secret values, live tokens, passwords, private keys.
- Oversized map for an XS/S project.
- One root file over 600 lines for an L/XL project — split into `architecture.md` or `domains/*.md`.
- Duplicating schema definitions locally instead of referencing `references/schema.md`.

## Final Audit Questions

- Could a fresh AI agent start a backend / UI / deploy task from these files?
- Would the agent know what not to repeat?
- Would it stop and ask before contradicting project history?
- Are run / test / deploy commands specific enough to execute?
- Is the map appropriately sized for the project?
- Does `Confidence Notes` honestly record uncertainty?
