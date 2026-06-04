# Reference: the unified root `CLAUDE.md` stanza

The skill writes **one** managed stanza into the project's root `CLAUDE.md` (or
`AGENTS.md`) covering **both** doc layers — navigation and memory. It is written
by `scripts/ensure_agent_rule.py`, never hand-pasted, so it stays idempotent and
upgradable in place.

Do **not** maintain two separate stanzas. Older versions of this skill wrote a
memory-only "Project Context Map" block with a different marker syntax;
`ensure_agent_rule.py` detects that legacy block and **replaces** it with the
unified one (it does not duplicate).

## How to write it

```bash
# both layers (default) — auto-detects slug from the context-map-* folder
python3 scripts/ensure_agent_rule.py --scope project --project /path/to/project

# navigation only (no memory folder yet)
python3 scripts/ensure_agent_rule.py --scope project --project /path --layers nav

# memory only
python3 scripts/ensure_agent_rule.py --scope project --project /path --layers memory

# preview without writing
python3 scripts/ensure_agent_rule.py --scope project --project /path --dry-run
```

Always show the diff and get approval before writing. The script only touches
content between its managed markers
(`<!-- managed by context-map skill: BEGIN/END agent-rule -->`); everything else
in the file is preserved.

## What the unified stanza contains

- **Navigation (committed) — `agent-docs/`.** Read `MAP.md` first → the owning
  `domains/<name>.md` → then the code. After changing entry points, public API,
  architecture, or domain boundaries, update the matching domain doc in the same
  change (or `[skip-agent-docs]` for a trivial one).
- **Memory (gitignored) — `context-map-<slug>/`.** Read `context-map.md` and its
  split files before planning. Treat Known Issues / Decisions / Agent Conflict
  Protocol as project memory; flag conflicts before proceeding. Never commit the
  folder.

The `--layers` flag composes the stanza from only the layers that exist, so a
memory-only project is not told to read a navigation layer it lacks, and vice
versa.

## Placement guidance

- Place the stanza near the top of `CLAUDE.md`. Agents read top-down; "read the
  docs first" rules should precede project-specific workflow rules.
- If the file already has the managed block, the script updates it in place.

## What not to include

- Don't list domains in `CLAUDE.md`. `MAP.md` is the source of truth; mirroring
  it guarantees drift.
- Don't duplicate domain content or conventions. Those live in the domain docs
  and `agent-docs/_meta/conventions.md`.
