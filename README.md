# context-map

> **Project memory for AI coding agents — survives context resets.**

A Claude Code skill that generates, updates, audits, and conflict-checks a `context-map-<slug>/` folder at the project root. The folder is a compact operational map split across domain files (known issues, decisions, tasks, gotchas) that helps future AI agents reorient instantly, find the right files, avoid repeating past mistakes, and respect prior project decisions.

A context map is **not** a README, PRD, or architecture document. It is navigational project memory that agents read first when they enter a project after a context reset.

**Status:** v0.1.0 · MIT license · part of [kyzdes/claude-skills](https://github.com/kyzdes/claude-skills) marketplace

---

## Install

### Via the kyzdes marketplace (recommended)

```
/plugin marketplace add kyzdes/claude-skills
/plugin install context-map@claude-skills
```

You'll auto-update on every Claude Code session start (4h debounced via shared stamp file).

### Standalone

```
/plugin marketplace add kyzdes/context-map-skill
/plugin install context-map@context-map-skill
```

---

## Triggers

The skill activates when you ask Claude Code for any of:

- "make a context map", "generate context-map.md"
- "audit project docs", "agent onboarding doc"
- "track project decisions", "log known issues for future agents"
- "what gotchas should the next agent know about?"

---

## What it produces

A `context-map-<project-slug>/` folder at the project root with:

- `context-map.md` — index + landmarks
- `known-issues.md` — recurring traps and their workarounds
- `decisions.md` — architectural / scope choices and rationale
- `tasks.md` — open work that survives between sessions

All files are generated in **English** regardless of session language. Existing non-English project terms are preserved when translation would lose precision.

The full schema (frontmatter, table columns, enums, required sections) lives in `skills/context-map/references/schema.md` — that file is authoritative.

---

## How it differs from CLAUDE.md / cursor rules

| | CLAUDE.md / cursor rules | context-map |
|---|---|---|
| Scope | Permanent rules for every session | Mutable state of one project |
| Owns | "How to behave" | "What is true right now" |
| Survives a context reset | Yes (auto-loaded) | Yes (agents are told to read it first) |
| Updates frequency | Rarely (curated) | Every meaningful change |

Both can coexist. The skill's docs explain when to put something in CLAUDE.md vs the context map.

---

## License

MIT — see [LICENSE](./LICENSE).

## Source

This plugin lives at [`kyzdes/context-map-skill`](https://github.com/kyzdes/context-map-skill) and is distributed via the [`kyzdes/claude-skills`](https://github.com/kyzdes/claude-skills) marketplace.
