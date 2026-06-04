# Context Map

**Agent-facing project documentation in two linked layers** — so an AI coding agent never gets lost in a big codebase, and never forgets what was already decided.

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill / plugin that generates, decomposes, audits, reconciles, and conflict-checks the docs an AI agent actually needs. It is **not** a README, PRD, or architecture spec — it is navigation *and* memory built for LLM ingestion.

```
your-project/
├── agent-docs/              ← navigation  (COMMITTED)   "where do I go, what reads what"
│   ├── MAP.md               router
│   ├── domains/*.md         per-domain deep docs
│   └── _meta/*.json         machine-readable links + freshness
└── context-map-<slug>/      ← memory      (GITIGNORED)  "what was decided, what's broken, what not to repeat"
    ├── context-map.md       router + frontmatter
    ├── decisions.md         D-### locked decisions
    ├── known-issues.md      KI-### open issues + regression rules
    ├── gotchas.md           G-### traps
    └── tasks.md             T-### next work
```

---

## Why two layers

A single docs file fails an agent in two different ways, so the skill keeps two trees with opposite git policies:

| | **Navigation** — `agent-docs/` | **Memory** — `context-map-<slug>/` |
|---|---|---|
| Git | **committed** — shared, reviewable | **gitignored** — private, `.env`-like |
| Answers | "where do I go, what reads what" | "what was decided, what's broken, what must I not repeat" |
| A fact goes here if… | it's **code structure** — domains, entry points, file routing, neighbors | it's **project history / operational truth** — decisions, known issues, gotchas, tasks |
| Stays fresh via | a CI freshness gate (fails the build when code changes but its domain doc doesn't) | a SessionStart staleness notice + manual `update` |

The two trees are cross-linked: `MAP.md` points at the memory router, the memory router points back at `MAP.md`, and `_meta/links.json` records the machine-readable pairing. Domain docs **cite** memory IDs (`D-002`, `KI-001`) instead of restating them, so there is one source of truth.

> **Why gitignore the memory?** `decisions.md` / `known-issues.md` are operational notes that may name internal hosts, workarounds, and "do not ship this" caveats. They are treated like `.env` — useful to every future agent on your machine, never pushed to a public remote.

---

## Install

The skill ships through the [`kyzdes/claude-skills`](https://github.com/kyzdes/claude-skills) marketplace:

```
/plugin marketplace add kyzdes/claude-skills
/plugin install context-map@claude-skills
```

Then just describe what you want in plain language — the skill triggers on intent, not on a command:

> "Set up a context map for this repo so future sessions remember our decisions and stop re-litigating them."
>
> "This monorepo is too big — my agent keeps loading the wrong files. Split it into per-domain docs and add a check that keeps them fresh."

Works in **Claude Code**, and the generated docs are wired into `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, or `.cursor/rules/` so **Cursor** and **Gemini CLI** sessions read them first too.

---

## What it does

Generation scales to the project. The skill runs an inspector (`scripts/inspect_project.py`) to size the repo (XS → XL) from source count, churn, and structure, then:

- **XS–S** — a lightweight memory tree only.
- **M+** — the full memory tree **plus** the committed `agent-docs/` navigation layer (6–12 domains at M, 10–25 at L/XL). At ≥5 domains it dispatches one writer subagent per domain in parallel.
- **Cross-checks code against existing docs** to build a confidence ledger (`verified` / `inferred` / `stale` / `conflicting`), so it never silently launders a guess into a fact.
- **Verifies its own output** — picks two questions an agent would really ask ("how does auth work end to end?", "where do I add an API route?"), starts from `MAP.md`, and follows the trail. If it reads more than three files without an answer, that's a documented gap to fix before finishing.

### Modes

You rarely name a mode — the skill infers it — but they're explicit when you want them:

| Mode | What it does |
|---|---|
| `generate` (alias `init`) | Bootstrap both layers (memory always; navigation at M+ or on request). |
| `update [<domain>]` | Refresh in place; preserves hand-written notes. Both layers by default. |
| `audit` | Report-only health check of both layers (`scripts/audit.py`). |
| `conflict-check` | Compare a requested change against `known-issues.md` / `decisions.md` and **stop before editing code** if it violates project history. |
| `decompose` | Propose a domain list for the navigation layer — no writes. |
| `add-domain <name> <path>` | Insert one new domain and wire it into `MAP.md` + `_meta/`. |
| `sustain` | Wire maintenance (gitignore, agent rule, CI gate) without re-documenting. |
| `reconcile` | Link an existing split / legacy layout with **zero data loss** (additive only). |
| `migrate-legacy` | Convert an older single-file `context-map.md` into the folder layout. |
| `batch-*` / `dashboard-data` | Discover and update many local projects at once. |

---

## Staying fresh

The single biggest failure mode of agent docs is silent rot. The skill wires the layers so they can't drift quietly:

- **Navigation — CI gate (default).** Copies `check_agent_docs_freshness.py` into the target repo and generates a workflow + pre-commit hook that fails when a domain's code changes but its doc doesn't. A `[skip-agent-docs]` escape hatch is documented for intentional skips.
- **Memory — staleness notice.** A SessionStart hook surfaces a "this map is N days old" notice. It never auto-rewrites memory — humans and explicit `update` runs do that.
- **Safety rails.** `.gitignore`, `CLAUDE.md`, and `settings.json` are never modified silently — every change goes through a visible diff and explicit approval. The memory tree is never committed; the navigation tree is never gitignored. If memory was committed *before* the ignore rule, the skill detects it and prints the exact `git rm -r --cached` command rather than running it for you.

---

## Output language

All generated files are **English** regardless of session language, so the docs are portable across teams and tools. The conversation stays in whatever language you're speaking.

---

## Repository layout

```
skills/context-map/
├── SKILL.md            entry point — modes, required workflow, routing
├── references/         loaded on demand (schema is authoritative)
│   ├── schema.md       single source of truth for both layers
│   ├── templates.md    file templates per scale
│   ├── heuristics.md   scale sizing + domain decomposition
│   └── …               first-run, reconcile, ci-gate, hooks, subagent orchestration
├── scripts/            zero-dependency Python (stdlib only)
│   ├── inspect_project.py            size + domain-candidate seed
│   ├── validate_context_map.py       memory-layer validator
│   ├── lint_docs.py                  navigation-layer linter
│   ├── audit.py                      runs both, one report
│   ├── reconcile.py                  link existing split layouts
│   └── …
├── evals/              skill-creator test cases + trigger evals
└── tests/test_skill.py self-contained regression suite (no pytest)
```

### Development

```bash
python3 skills/context-map/tests/test_skill.py     # regression suite
python3 skills/context-map/scripts/audit.py --project /path/to/a/project
```

CI (`.github/workflows/validate-plugin.yml`) validates the plugin manifest, the `SKILL.md` frontmatter, and runs the test suite on every push. Scripts are stdlib-only and must run under a bare `python3`.

---

## Compatibility

- **Claude Code** — native skill / plugin.
- **Cursor** / **Gemini CLI** — generated docs are wired into the agent-config file each tool reads first (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.cursor/rules/`).

---

> Built as part of the [`kyzdes/claude-skills`](https://github.com/kyzdes/claude-skills) marketplace. `context-map` v0.3 folds in the former `agent-docs-architect` skill — one skill now owns both the navigation and memory layers.
