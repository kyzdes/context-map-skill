# Decisions, Known Issues, Gotchas, Tasks — Format Rules

`references/schema.md` defines the canonical columns, enums, and ID formats. This file explains how to author each row so it stays useful for a future agent who has no chat history.

## Known Issues (`known-issues.md`)

Table columns are fixed: `ID | Area | Priority | Symptom | Cause | Status | Agent-Ready | Rule`.

- `ID`: `KI-###`. Never reuse an ID after a row is deleted.
- `Priority`: `critical` | `high` | `medium` | `low`.
- `Status`: `open` | `partial` | `fixed` | `wontfix` | `watch`.
  - `fixed` rows stay if an agent could re-introduce the bug. Phrase the rule as "do not regress X".
  - `watch` is for fragile or suspected areas that are not broken yet.
- `Agent-Ready`: `yes` | `no` | `needs-human`.
- `Symptom` + `Cause` must be understandable without reading old conversations.
- `Rule` is the actionable takeaway: what future agents must do or avoid.

XS projects may inline this section inside `context-map.md` as concise bullets:

```md
## Known Issues

- **KI-001: Port 5000 fails on macOS.**
  Symptom: server exits with EADDRINUSE.
  Cause: AirPlay Receiver uses port 5000.
  Status: fixed.
  Rule: use port 5050 or any unused port above 5000.
```

## Decisions (`decisions.md`)

Table columns: `ID | Date | Decision | Rationale | Consequence | Do Not Repeat`.

- `ID`: `D-###`.
- `Date`: ISO `YYYY-MM-DD`. Use the decision date, not the file-write date.
- Every decision must explain **why**, otherwise a future agent cannot tell when it is safe to revisit.
- `Consequence`: the tradeoff already accepted.
- `Do Not Repeat`: concrete action or pattern the agent must avoid.

If a long-form `decisions.md` / ADR directory already exists elsewhere in the repo, keep the split file focused on decisions that affect day-to-day agent work and link to the full log from `architecture.md` or `context-map.md`.

## Tasks / Next Work (`tasks.md`)

Table columns: `ID | Area | Type | Task | Status | Agent-Ready | Validation`.

- `ID`: `T-###`.
- `Type`: `feature` | `fix` | `refactor` | `docs` | `ops` | `research`.
- `Status`: `planned` | `ready` | `blocked` | `in_progress` | `done` | `wontfix`.
- `Agent-Ready`: `yes` | `no` | `needs-human`.
- `Validation`: the command or check that proves the task is done (e.g. `pytest tests/foo`, `npm run build`, curl health).

`ready` + `Agent-Ready: yes` is the dashboard's signal that an agent can pick up the task without human setup.

## Gotchas (`gotchas.md`)

Table columns: `ID | Category | Description | Trigger | Guardrail`.

- `ID`: `G-###`.
- `Category`: `runtime` | `api` | `deploy` | `ui` | `data` | `agent` | `other`.
- `Trigger`: the situation that causes the gotcha.
- `Guardrail`: the check, command, or habit that prevents it.

Gotchas differ from `Known Issues` in that there is no specific bug yet; they are traps or surprising configurations.

## Agent Conflict Protocol

Every `context-map.md` for projects above XS embeds this protocol verbatim. It is the safety guard against agents silently reversing decisions:

```md
## Agent Conflict Protocol

Before editing code, read `known-issues.md` and `decisions.md`.

If the requested change conflicts with a recorded decision or known issue:
1. Do not silently override it.
2. Explain the conflict in one short paragraph.
3. Ask the user whether to intentionally change course.
4. If confirmed, update `decisions.md` (and `known-issues.md` if relevant) with the new entry and rationale.
```

Example agent response when a conflict is detected:

```text
The requested dark-mode toggle conflicts with D-003, which made public pages light-only to reduce QA surface. Do you want to reverse that decision for this feature?
```

## Conflict Check Mode

When the skill runs in `conflict-check` mode:

1. Read `known-issues.md`, `decisions.md`, and `context-map.md` → `Agent Conflict Protocol`.
2. Identify direct conflicts and plausible conflicts with the requested change.
3. If no conflict, proceed.
4. If a conflict exists, stop before editing code and ask the user.
5. After implementation, update project memory: add a new row or change statuses, never silently rewrite past rows.
