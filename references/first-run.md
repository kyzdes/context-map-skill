# First Run User Journey

Use this when a project has no `context-map-<slug>/` folder yet (or only a legacy single-file `context-map.md` / `docs/context-map.md`, in which case run `migrate-legacy` first).

## Conversation Language

The user-facing conversation uses the current session language. The generated files are always English — that split is intentional and does not change based on how the user writes.

## Goal

The first interaction should make the skill understandable without overwhelming the user:

- explain that a context map is project memory for AI agents;
- state the folder that will be created (`context-map-<slug>/`);
- offer `.gitignore` changes for public / unclear repos;
- offer agent-file integration so future agents automatically read the folder;
- avoid blocking on choices unless they change what files are created or touched.

## First Response Pattern

Before scanning or editing, send a short note. This is a conversation example written in Russian to illustrate the shape; adapt to the actual session language, and do not put this text into the generated files:

```text
Я создам папку `context-map-<slug>/` в корне проекта с набором файлов: `context-map.md` (главный), `known-issues.md`, `decisions.md`, `tasks.md`, `gotchas.md` (и `architecture.md` для средних+ проектов). Это оперативная память проекта для будущих AI-агентов на английском языке.

Дополнительно могу:
- добавить правило в `CLAUDE.md` / `AGENTS.md`, чтобы агенты всегда читали эту папку перед работой;
- добавить универсальное правило в `~/.claude/CLAUDE.md` для всех твоих проектов (опционально);
- добавить `context-map-*/` в `.gitignore`, если репозиторий публичный.

Ничего из этого не сделаю без подтверждения. Сейчас просканирую проект.
```

Then proceed to inspection. Do not wait for setup answers unless the user asked to decide them first.

## Context Collection Flow

Generation has five phases. Phases 1–2 are read-only.

### Phase 1 — Scan

1. Run `python3 scripts/inspect_project.py <path> --format json` to collect files, stacks, entry points, package scripts, env examples, docs, git signals, and doc-drift candidates.
2. Read existing agent-config files and project docs listed in `references/heuristics.md` → `Read Priority`.
3. If an existing `context-map-<slug>/` exists, read every file in it.

### Phase 2 — Cross-Check (Confidence Ledger)

For each candidate claim that might enter the map (endpoint, file path, command, feature name, key decision, invariant):

- is it present in code? (ripgrep, AST-light, or manifest search);
- is it mentioned in docs, and in how many sources;
- when was the claim last touched (git log of the referencing file).

Classify each claim:

| Confidence | Meaning |
|------------|---------|
| `verified` | present in code, matches docs |
| `inferred` | present in code, not documented |
| `stale` | mentioned in docs, absent or changed in code |
| `conflicting` | docs disagree with each other |
| `duplicate` | same topic repeated in multiple docs with different detail |

Every `stale`, `conflicting`, and `duplicate` claim must land in `Confidence Notes`. `inferred` claims go into the relevant section with an `(inferred)` tag and a `Confidence Notes` row referencing the source.

The skill does not automatically modify README or docs. It only flags them.

### Phase 3 — Generate

Create or update files inside `context-map-<slug>/`. Use the templates in `references/templates.md` and the schema in `references/schema.md`. Populate:

- `Current Phase` from git signals (`extract_git_signals` output).
- `Confidence Notes` from the ledger above.
- `Tech Stack`, `Directory Structure`, `Read First By Task Type`, `Architecture Overview` from the inspection output.
- Split files (`known-issues.md`, `decisions.md`, `tasks.md`, `gotchas.md`, `architecture.md`) from project docs + confidence ledger + git history.

Do not invent rows. If there is no evidence for a known issue or decision, leave the table empty with a short note explaining why.

### Phase 4 — Validate

Run `python3 scripts/validate_context_map.py <project>/context-map-<slug>`. If validation fails, fix the output before reporting success.

### Phase 5 — Agent Integration (see below)

## Agent File Integration

On first run, after the folder is written, propose writing a "Project Context Map" stanza into existing agent config files.

### Detect

Look for each of these at the project root (or where applicable):

| File | Notes |
|------|-------|
| `CLAUDE.md` | primary target; most common in 2026 |
| `AGENTS.md` | secondary; check before defaulting to `CLAUDE.md` |
| `.claude.local.md` | personal / gitignored rules |
| `GEMINI.md` | uncommon; only if present |
| `.cursor/rules/` | Cursor convention; do not create, only add rules if folder exists |
| `.github/copilot-instructions.md` | GitHub Copilot; do not create, only add rules if file exists |

Also consider the global file `~/.claude/CLAUDE.md` for the optional generic stanza.

### Per-Project Stanza

Write (or refresh) this stanza into the selected project agent file, between marker comments so future runs update only this region. Substitute `<slug>` with the folder slug.

```markdown
## Project Context Map

<!-- managed by context-map skill; edit above/below this section freely -->

- Before planning or editing, read `context-map-<slug>/context-map.md` and the split files it links to (`known-issues.md`, `decisions.md`, `tasks.md`, `gotchas.md`; `architecture.md` if present).
- Treat `Known Issues`, `Decisions`, and the `Agent Conflict Protocol` section as project memory.
- If a requested change conflicts with a Known Issue or Decision, explain the conflict and ask the user before proceeding.
- Update the context map when entry points, architecture, deploy flow, run/test commands, DB schema, auth, payments, or external integrations change; when a significant decision is made or reversed; when a known issue is discovered, fixed, or accepted; when a fix prevents a future regression.
- Do not put secrets, tokens, passwords, or private credentials in the context map.

<!-- end context-map skill section -->
```

### Idempotency

- Search for the exact marker `<!-- managed by context-map skill` in the target file. If present, replace everything between it and `<!-- end context-map skill section -->` with the refreshed stanza; leave content outside the markers untouched.
- If no marker exists but a `## Project Context Map` heading is already present (hand-written), show it as a diff against the proposed stanza and ask the user whether to replace, merge, or skip.
- If no heading is present, append the stanza to the end of the file.
- If no agent file exists at all, offer to create `CLAUDE.md` with just this stanza.

Always show the diff and wait for approval before writing. Never write silently. Use the `Edit` tool for changes.

### Optional: Global Stanza in `~/.claude/CLAUDE.md`

After the per-project stanza is applied, ask separately:

```text
Добавить универсальное правило в `~/.claude/CLAUDE.md`, чтобы любой твой проект с папкой `context-map-*/` автоматически подхватывался агентом?
```

Only on explicit approval, write this stanza (same marker discipline):

```markdown
## Project Context Maps (global rule)

<!-- managed by context-map skill -->

- When opening any project, check its root for a folder matching `context-map-*/`. If present, read `context-map.md` inside it before planning or editing.
- Treat `known-issues.md`, `decisions.md`, and `tasks.md` inside that folder as project memory. Flag conflicts before implementing changes that contradict them.

<!-- end context-map skill section -->
```

This is a one-time, idempotent addition. Subsequent runs against the same global file detect the marker and skip unless the stanza content itself changed.

## Repository Visibility Guidance

Default recommendation:

- **Private / internal repo**: commit `context-map-<slug>/`. It is shared project memory.
- **Public / open-source repo**: ask whether to keep the folder private. If yes, add `context-map-*/` to `.gitignore`.
- **Unknown visibility**: ask before adding `.gitignore` changes.

Do not assume visibility from a remote URL alone.

### .gitignore Snippet

Use only with user approval:

```gitignore
# AI agent local project memory
context-map-*/
```

If the user wants to keep a committed shared folder while still having personal local overrides, a `*.local.md` convention inside the folder is available:

```gitignore
context-map-*/**/*.local.md
```

## First-Run Completion Message

After the folder is written, agent stanza is proposed (and optionally applied), end with:

- path of the created folder;
- list of files created;
- status of the agent-file integration (applied / declined / pending);
- status of the optional global stanza;
- status of `.gitignore` suggestion;
- one concrete next step (e.g. "open `context-map.md` to review the Confidence Notes").

Example (session-language conversation, adapt wording):

```text
Создал `context-map-myproj/` (5 файлов). Предложил добавить правило в `CLAUDE.md` — ждёт твоего подтверждения. `~/.claude/CLAUDE.md` и `.gitignore` не трогал. Рекомендую открыть `context-map-myproj/context-map.md` → раздел Confidence Notes (три расхождения между README и кодом).
```
