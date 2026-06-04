# Reconcile mode

`reconcile` links an existing split or legacy documentation layout into the
two-layer model with **zero data loss**. Use it when a project already has some
combination of `agent-docs/`, `context-map-<slug>/`, or a legacy single-file map
— typically built by an older skill or by hand, and only half-linked.

It is driven by `scripts/reconcile.py`, which is **read-only by default** (it
reports the detected state and the planned changes) and performs edits only with
`--apply`.

## Zero-data-loss invariants

Reconcile only ever:
1. **adds** files (`agent-docs/_meta/links.json`);
2. **adds** lines inside existing files via shown diffs (the `../agent-docs/MAP.md`
   row in the memory `## Linked Files`; `nav_layer: agent-docs` in frontmatter);
3. **replaces** content strictly between managed markers (the unified CLAUDE.md
   stanza — including a legacy memory-only stanza in the old marker syntax);
4. **edits `.gitignore` additively** (adds `context-map-*/`, never `agent-docs/`).

It NEVER regenerates `decisions.md` / `known-issues.md` / `gotchas.md` / domain
docs, never deletes, never reorders. Any regeneration is an explicit, separate
`update`.

## Detection (read-only)

`reconcile.py` classifies the project:

| State | Meaning | Action |
|-------|---------|--------|
| `both` | `agent-docs/` **and** `context-map-<slug>/` present | the main reconcile path (link them) |
| `memory-only` | memory tree, no navigation | suggest `decompose` → `generate --layer nav`, then reconcile |
| `nav-only` | navigation tree, no memory | suggest `generate --layer memory`, then reconcile |
| `legacy-single-file` | a `context-map.md` / `docs/context-map.md` not in a folder | run `migrate-legacy` first, then reconcile |
| `none` | nothing | run `generate` |

If more than one `context-map-*/` folder is found, it stops and asks you to
resolve the ambiguity (it will not guess the pairing).

## Steps (state = `both`)

1. **Inventory, never overwrite.** Read `agent-docs/_meta/*`, the memory
   `context-map.md` frontmatter version, and grep both trees for existing
   cross-links and managed stanzas (including the legacy marker syntax).
2. **Link (additive).**
   - Write `agent-docs/_meta/links.json` (pairing; shape in `references/schema.md` → Navigation Layer).
   - Add the `../agent-docs/MAP.md` row to the memory `context-map.md`
     `## Linked Files` (idempotent — skipped if already present).
   - If `agent-docs/MAP.md` lacks a `## Project memory` link to the memory
     folder, reconcile **warns** (it does not fabricate the section — populate it
     from `references/map-template.md`).
3. **Frontmatter migration (additive).** Add `nav_layer: agent-docs` and bump
   `context_map_version` 2 → 3. Existing fields and all table content are left
   byte-for-byte unchanged.
4. **Unify the stanza.** `ensure_agent_rule.py` replaces any legacy
   `## Project Context Map` block (old marker syntax) with the single unified
   two-layer block, in place, preserving everything outside the markers.
5. **Fix protection asymmetry (the data-safety step).** Run
   `ensure_gitignore.py --scope project` so the memory tree is ignored by the
   project's **own** `.gitignore` — not only by global excludes. Without this, a
   clone on a machine lacking the global rule would commit private memory. The
   navigation layer stays committed.

   **Already-tracked memory.** A `.gitignore` rule does **not** untrack files
   already committed. If the memory folder was committed before the rule existed
   (common in old projects — e.g. manaurum had all 6 memory files tracked),
   `ensure_gitignore.py` and `reconcile` both **warn** and print the fix — they
   do not run it (it mutates the git index):

   ```bash
   git -C <project> rm -r --cached context-map-<slug>/   # files stay on disk
   git -C <project> commit -m "stop tracking context-map memory"
   ```
6. **Validate + report.** Run `validate_context_map.py` (memory) and
   `lint_docs.py` (navigation); report what was linked, the stanza change, the
   gitignore change, and any lint warnings (e.g. slashless `domain-paths.json`).

## Commands

```bash
# 1. Report what reconcile would do (safe, read-only)
python3 scripts/reconcile.py --project /path/to/project

# 2. Show the user the report, get approval, then apply the additive edits
python3 scripts/reconcile.py --project /path/to/project --apply

# 3. Also run the gitignore + unified-stanza hooks in the same pass
python3 scripts/reconcile.py --project /path/to/project --apply --run-hooks
```

Always show the report/diffs and get approval before `--apply`. The protection
hooks (`ensure_gitignore.py`, `ensure_agent_rule.py`) are themselves idempotent
and have their own `--dry-run` / `--check`.
