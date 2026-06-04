---
name: context-map
description: >
  Build and maintain agent-facing project documentation in two linked layers: a
  COMMITTED `agent-docs/` navigation tree (a MAP router + per-domain deep docs +
  optional per-folder CLAUDE.md, so an agent reads only the slice it needs) and a
  GITIGNORED `context-map-<slug>/` memory tree (decisions, known issues, gotchas,
  tasks, Agent Conflict Protocol). Use when the user asks for a project context
  map, agent memory document, onboarding map, known-issues/decisions log; OR when
  a project is too big for an agent's context, agents get lost in the codebase,
  docs don't fit / waste tokens loading the wrong files, or the user wants to
  decompose / map / structure the project for AI, split docs by domain, set up
  per-area CLAUDE.md, or add a CI gate that keeps the docs fresh. Triggers in
  Russian too — "карта проекта", "память проекта для агента", "разложить проект",
  "агенты теряются в коде", "слишком большой проект", "документация для агентов",
  "decisions / known issues". Replaces the retired `agent-docs-architect` skill.
metadata:
  short-description: Two-layer agent docs — committed navigation + gitignored memory
  version: "0.3"
---

# Context Map

This skill owns a project's entire agent-facing documentation as **two cross-linked layers**:

- **Navigation layer — `agent-docs/` (committed).** A `MAP.md` router, per-domain deep docs, and `_meta/`. Answers *"where do I go, what reads what"*. Stable, shareable, and gated for freshness by CI.
- **Memory layer — `context-map-<slug>/` (gitignored).** Decisions, known issues, gotchas, tasks. Answers *"what was decided, what's broken, what must I not repeat"*. Private operational notes — treated like `.env`, never committed.

A context map is not a README, PRD, or full architecture spec. Together the two layers are project memory **and** navigation for future agents.

## Two Layers, One Skill

| | Navigation (`agent-docs/`) | Memory (`context-map-<slug>/`) |
|---|---|---|
| Git | **committed** | **gitignored** |
| A fact goes here if… | it's **code structure** — domains, entry points, file routing, neighbors, "read me when" | it's **project history / operational truth** — decisions (D-###), known issues (KI-###), gotchas (G-###), tasks (T-###), current phase |
| Freshness | CI gate (Policy C, ~99%) | SessionStart staleness notice + manual `update` |

**Gray-zone rule:** a *structural* gotcha ("router order matters in `main.py`") → the domain doc's `## Gotchas`. A *historical/operational* gotcha ("port 5000 fails on macOS AirPlay; KI-001") → memory `gotchas.md` / `known-issues.md`. When unsure: does the agent need it to **navigate** (nav) or to **avoid a known landmine / respect a decision** (memory)?

**Cross-link contract (bidirectional):**
- `agent-docs/MAP.md` `## Project memory` → `../context-map-<slug>/context-map.md`.
- memory `context-map.md` `## Linked Files` → `../agent-docs/MAP.md` (set `nav_layer: agent-docs` in frontmatter).
- `agent-docs/_meta/links.json` records the machine-readable pairing.
- Domain docs **cite** memory IDs (D/KI/G/T), never restate them.

The full schema for **both** layers (layout, frontmatter, tables, enums, required sections, canonical domain-doc headers, `_meta/*.json` shapes) lives in `references/schema.md`. It is authoritative; if any other file disagrees, follow `schema.md` and fix the other file.

## Output Language

All generated files (both layers) are in **English** regardless of session language. Conversation stays in the session language. Preserve established non-English project names or domain terms when translating would reduce precision; note the choice in `Confidence Notes`.

## Modes

`update` and `audit` act on **both layers by default**. A domain argument (`update auth`) or `--layer nav` scopes to navigation; `--layer memory` scopes to memory. Never silently do only one layer when the user said just `update`.

- **generate** (alias **init**): bootstrap. Creates the memory tree always; the navigation tree at scale M+ (or on request). `--layer nav|memory|both`.
- **update [<domain>]**: refresh. A domain arg ⇒ refresh that nav domain doc; `--layer memory` ⇒ refresh memory tables; bare ⇒ both. Preserves hand-written notes.
- **audit**: report-only, both layers via `scripts/audit.py` (one report, two sections) — memory schema/drift (`validate_context_map.py`) + navigation structure/staleness (`lint_docs.py`). `--layer` scopes it.
- **conflict-check**: compare a requested change against `known-issues.md` and `decisions.md`; stop before editing code and ask the user before violating project history.
- **decompose**: navigation-only Discover + Decompose. Propose the domain list, no writes.
- **add-domain `<name> <path>`**: insert one new nav domain; wire it into `MAP.md`, `_meta/`, and Neighbors.
- **sustain** (alias **sustain-only**): wire maintenance for both layers without re-documenting — memory `.gitignore` + agent rule + SessionStart notice; navigation CI gate (Policy C) + optional Stop hook (Policy B).
- **reconcile**: link an existing split/legacy layout (a project that already has `agent-docs/` and/or `context-map-<slug>/` and/or a legacy single-file map). Additive, zero data loss. See `references/reconcile.md`.
- **migrate-legacy**: convert an older single-file `context-map.md` / `docs/context-map.md` into the folder layout via `scripts/migrate_legacy.py`.
- **batch-discover / batch-plan / batch-generate / batch-index**: multi-project discovery and queued generation. `batch-generate` takes `--layer`.
- **dashboard-data**: prepare/refresh `~/.context-map/index.json` (spans both layers) for the local web UI.

Infer the mode. Default `generate` when nothing exists, `update` when a map exists, `reconcile` when both trees exist but are unlinked or use legacy markers, `migrate-legacy` when a legacy single-file map is detected (stop before touching code).

## First Run

If neither `context-map-*/` nor `agent-docs/` exists, treat this as a first run and read `references/first-run.md` before editing. On first run the skill:

1. Briefly explains, in the session language, that it will create agent-facing docs (which layers, and that memory is gitignored while navigation is committed).
2. Scans for existing agent-config files (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.cursor/rules/`, `.github/copilot-instructions.md`) and proposes a single unified "Project Docs" stanza in the most appropriate one, via `scripts/ensure_agent_rule.py` — always waiting for approval.
3. Optionally offers a global rule in `~/.claude/CLAUDE.md` (explicit approval only).
4. Offers `.gitignore` updates so the memory tree is ignored and the navigation tree stays committed.

Never modify `CLAUDE.md`, `AGENTS.md`, `.gitignore`, `settings.json`, or `~/.claude/CLAUDE.md` silently. Everything goes through a visible diff and explicit approval.

## Scale ↔ Domains

Project scale (XS–XL) gates the memory files (see `references/schema.md` → `File Presence By Scale`) **and** whether/how big the navigation layer is. The full scale↔domain-count table and the "what is a domain / good-vs-bad signs" rules live in `references/heuristics.md` → `Domain Decomposition`. In short: navigation layer is opt-in below M, default at M+; expect 6–12 domains at M, 10–25 at L/XL; dispatch parallel writer subagents at ≥5 domains.

## Required Workflow

The navigation layer adds a Discover→Decompose→Document→Sustain→Verify arc on top of the memory workflow. Combined:

1. **Find the project root.** Prefer cwd unless the user names a path.
2. **Discover.** Read existing agent/project guidance (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.cursor/rules/`, README, architecture docs, PRD, `decisions.md`, `known-issues.md`, ADRs). Run the inspector:

   ```bash
   python3 scripts/inspect_project.py /path/to/project --format json
   ```

   Output includes scale, git churn, doc-drift candidates, and a `domain_candidates` seed for the navigation layer. If first run, follow `references/first-run.md`.
3. **Determine scale** using `references/heuristics.md`.
4. **Cross-check code against docs** to build a confidence ledger (`references/first-run.md` → `Context Collection Flow`): `verified` / `inferred` / `stale` / `conflicting` / `duplicate`.
5. **Decompose** (navigation, scale M+ or on request). From the inspector's `domain_candidates` + directory signals, propose a domain list (`name — root(s) — one-line responsibility`) and the cross-cutting concerns. Present it and accept the user's edits literally before writing.
6. **Document.**
   - *Memory:* load `references/templates.md` + `references/schema.md`; populate the split files per scale. Always include `Known Issues`, `Decisions`, `Tasks / Next Work`, `Gotchas`, `Agent Conflict Protocol`, and `Confidence Notes` unless the user asks for a minimal XS note.
   - *Navigation:* the lead writes `_meta/domain-paths.json` + `_meta/conventions.md` first, then for ≥5 domains dispatches one writer subagent per domain (`references/subagent-orchestration.md` — read it before dispatching), then runs `scripts/lint_docs.py` and resolves flags, then writes `MAP.md`, `cross-cutting.md`, `_meta/last-verified.json`, and `_meta/links.json`. For <5 domains, write inline. Templates: `references/{map-template,domain-doc-template,cross-cutting-template,distributed-claude-md-template}.md`.
7. **Cross-link** the two layers per the contract above (`links.json`, the MAP `## Project memory` section, the memory `## Linked Files` row, `nav_layer: agent-docs`).
8. **Validate.** Run both via `python3 scripts/audit.py --project /path/to/project` (or each directly: `validate_context_map.py /path/.../context-map-<slug>` for memory, `lint_docs.py --root /path/to/project` for navigation). Fix output before reporting success — never claim completion with either failing.
9. **Sustain.** Gitignore + agent rule + (M+) CI gate. See the Sustain section.
10. **Verify.** Pick two questions an agent would realistically ask ("how does auth work end-to-end?", "where do I add an API route?"), start from `MAP.md`, follow the doc trail. If you read >3 files and still can't answer, the docs have a gap — fix it before finishing.
11. **Conflict protocol.** If requested work conflicts with a known issue or decision, stop before editing code and ask the user (`references/decision-format.md` → `Agent Conflict Protocol`).

## Sustain (maintenance discipline)

The single biggest failure mode of agent docs is silent rot. Wire the layers so they don't drift:

- **Memory:** `scripts/ensure_gitignore.py --scope project` (ignore `context-map-*/`, never `agent-docs/`) and `scripts/ensure_agent_rule.py` (unified two-layer stanza). The SessionStart hook surfaces a memory-staleness notice (it never auto-rewrites memory).
- **Navigation — Policy C (default, ~99%):** copy `scripts/check_agent_docs_freshness.py` into the target's `scripts/`, generate the CI workflow and a pre-commit hook (`references/ci-gate-setup.md`), and document the `[skip-agent-docs]` escape hatch in root `CLAUDE.md`. Tell the user to add the CI job to required status checks.
- **Navigation — Policy A (always):** the navigation half of the unified stanza ("update the domain doc in the same change").
- **Navigation — Policy B (optional):** a Stop-hook reminder via `/update-config` (`references/hooks-setup.md`); always show the `settings.json` diff, never write it directly.

Mechanics for `update` / `audit` / `add-domain` and the `_meta/` schemas live in `references/maintenance-rules.md`.

## Reconcile

For a project that already has both trees (or a legacy layout), `reconcile` detects, links, and unifies with **zero data loss** — it only adds files, adds lines via shown diffs, replaces content between managed markers (including the legacy memory-only stanza), and edits `.gitignore` additively. It never regenerates `decisions.md` / domain docs, never deletes, never reorders. Full step-by-step in `references/reconcile.md`.

## Batch And Dashboard

For `batch-*` and `dashboard-data`, read `references/batch-workflow.md` and `references/dashboard-data.md`. Config: `~/.context-map/config.json`. Dashboard index: `~/.context-map/index.json`. Show discovered candidates and let the user choose before writing. Process selected projects as a queue; write durable progress after each.

## Where To Write

- Existing `context-map-<slug>/` and/or `agent-docs/`: update in place (or `reconcile` if unlinked).
- Nothing yet: create the memory tree at the root (split files per scale) and, at M+ or on request, the navigation tree.
- Legacy single-file map detected: run `migrate-legacy` (do not silently overwrite).

Do not include secrets, tokens, passwords, or live credentials in either layer. Reference secret-holding file paths only if useful and safe.

## Update Rules

- Preserve accurate manual notes. Skill-managed tables/stanzas are idempotent; hand-written commentary (memory prose between sections; the navigation `## Notes` section) must survive.
- Remove or mark stale claims when code/docs contradict them; add a `Confidence Notes` row for each contradiction.
- Prefer adding a new decision over silently rewriting project history. Keep a fixed known issue if future agents might repeat it (status `fixed` + regression rule).
- Keep `context-map.md` and `MAP.md` concise routers. Deep memory detail → `architecture.md`; deep navigation detail → the domain doc.
- Bump `last_updated` and `last_verified_vs_code` (memory) and `_meta/last-verified.json` (navigation) on every run.

## Reference Files

Memory layer: `schema.md` (authoritative, both layers), `templates.md`, `heuristics.md` (scale + domain decomposition), `first-run.md`, `decision-format.md`, `quality-check.md`, `batch-workflow.md`, `dashboard-data.md`.

Navigation layer: `map-template.md`, `domain-doc-template.md`, `cross-cutting-template.md`, `distributed-claude-md-template.md`, `root-claude-md-stanza.md`, `subagent-orchestration.md` (read before dispatching writers), `maintenance-rules.md`, `ci-gate-setup.md`, `hooks-setup.md`.

Reconcile: `reconcile.md`.

Scripts: `inspect_project.py`, `validate_context_map.py` (memory), `lint_docs.py` (navigation), `audit.py` (runs both, one report), `check_agent_docs_freshness.py` (CI gate template), `ensure_gitignore.py`, `ensure_agent_rule.py`, `reconcile.py`, `discover_projects.py`, `collect_context_maps.py`, `migrate_legacy.py`.
