# Maintenance modes: `update`, `audit`, `add-domain`

The skill stays useful only if the user (or another agent) can refresh docs cheaply. This file documents the three maintenance modes.

## `update <domain>` — refresh one domain doc

When invoked: `context-map skill: update <domain>` or `update <domain1> <domain2>`.

Steps:
1. **Read the current doc**: `agent-docs/domains/<domain>.md`. Note the `Last verified` SHA.
2. **Diff the domain** since that SHA: `git log --since-commit=<sha> -- <domain root>` to find what changed. Also list current files (`Glob` in the domain root) to compare against the doc's "Files of interest" table.
3. **Re-derive each section** from current code:
   - Entry points: did any new public functions/handlers/routes appear or disappear?
   - Files of interest: any new important files? Any deleted? Any that no longer match their listed description?
   - Architecture bullets: still accurate? Is there a new component?
   - Neighbors: any new cross-domain imports?
4. **Preserve hand-written content**:
   - Everything under `## Notes`.
   - Anything under `## Gotchas` unless the gotcha is clearly resolved (e.g., the code it warned about is gone).
   - User-added bullets in `## Conventions` that don't contradict current code.
5. **Update `Last verified`** to today's date and current commit SHA.
6. **Show the diff** to the user. Apply on approval.

### Update rules

- **Never silently delete a Gotcha.** Even if it looks stale, ask. Gotchas often encode hard-won knowledge.
- **Never reorder existing sections.** Predictability beats prettiness for agent-friendly docs.
- **If the doc grew past 200 lines after update** — flag the domain for splitting.

## `audit` — staleness report (no writes)

When invoked: `context-map skill: audit`.

Steps:
1. Read `agent-docs/_meta/last-verified.json`. Example shape:
   ```json
   {
     "auth": { "date": "2026-03-01", "sha": "abc123" },
     "apps": { "date": "2026-04-15", "sha": "def456" }
   }
   ```
2. For each domain:
   - Run `git log --since=<date> -- <domain root>` (or `git log <sha>..HEAD -- <domain root>`).
   - Count commits and changed files.
   - Read the domain doc's "Entry points" table. If any listed entry point was modified — flag as **likely stale**.
   - If ≥ 5 files changed and ≥ 1 entry point modified — flag as **definitely stale**.
   - If fewer than 5 files changed and no entry points modified — flag as **probably fresh**.
3. Output a report:
   ```
   Audit results:
     ✗ auth        — definitely stale (12 commits, 3 entry points modified since 2026-03-01)
     ⚠ apps        — likely stale (8 commits, 1 entry point modified)
     ✓ wizard      — fresh (no changes since last verify)
   
   Recommended: context-map skill: update auth apps
   ```
4. **Do not auto-fix.** This mode is informational.

## `add-domain <name> <path>` — register a new area

When invoked: `context-map skill: add-domain <name> <path>` (or with multiple paths).

Steps:
1. **Sanity check**: ensure `<path>` is not already inside an existing domain's root. If it is — ask whether to split or merge instead.
2. **Generate the doc** at `agent-docs/domains/<name>.md` using `domain-doc-template.md`. Fill what you can infer; mark gaps for the user.
3. **Append a row** to the domains table in `agent-docs/MAP.md`.
4. **Update `_meta/domain-paths.json`** to include the new domain's root(s).
5. **Update `_meta/last-verified.json`** with today's entry.
6. **If distributed CLAUDE.md is enabled**: generate the local `<path>/CLAUDE.md` using `distributed-claude-md-template.md`.
7. Show all diffs and apply on approval.

## `_meta/last-verified.json` schema

```json
{
  "<domain-name>": {
    "date": "YYYY-MM-DD",
    "sha": "<commit SHA at time of verification>"
  }
}
```

One entry per domain. The `update` mode writes here. The `audit` mode reads here. Keep this file simple — it's an index, not a log.

## `_meta/domain-paths.json` schema

```json
{
  "<domain-name>": ["<path/to/root/>", "<optional-other-root/>"]
}
```

Paths are relative to project root and end with `/`. Used by the audit logic and (if enabled) by the Stop hook.
