# Subagent orchestration

Phase 3 (document generation) is the most parallelizable part of this skill. On a project with 18 domains, writing each doc in serial from one Claude context wastes time and burns context for no reason — each domain doc is independent of the others, and each subagent can deep-read its own 5–15 files without polluting the lead Claude's view.

The pattern is **two-stage**:

1. **Per-domain writer subagents (parallel)** — one Agent call per domain, all dispatched in the same turn. Each subagent reads code, writes one domain doc, returns a report.
2. **Tech-lead review pass (lead Claude, serial)** — read all outputs, run consistency checks, fix what's auto-fixable, surface judgment calls to the user.

This pattern also applies (in lighter form) to `update <domain>` when the user asks for several domains at once, and to `audit` when checking staleness across many domains.

## When to dispatch subagents

| Phase / mode | Dispatch subagents? | Why |
|--------------|---------------------|-----|
| Phase 1 Discover | No | Needs holistic view of the whole repo; subagents would re-do each other's work. |
| Phase 2 Decompose | No | Single-shot judgment call; needs full discovery in one context. |
| Phase 3 Document — domains | **Yes**, one per domain in parallel | Independent units, well-suited. |
| Phase 3 Document — MAP.md / cross-cutting.md / _meta files | No (lead writes after subagents finish) | Needs all domain outputs as input. |
| Phase 4 Sustain | No | Mostly settings/CLAUDE.md patches the user must approve. |
| Phase 5 Verify | Optional | Can dispatch 2 subagents to trace 2 questions through the docs; lead aggregates. |
| `update <a> <b> <c>` | Yes if ≥ 2 domains | Same parallel logic. |
| `update <a>` (single domain) | No | One Agent call is just overhead. Lead does it. |
| `audit` | No (script-driven) | Mostly mechanical: git log + last-verified.json comparison. |
| `add-domain` | No | Single-shot. |

The rule of thumb: dispatch subagents only when you have **≥ 2 truly independent** work items. Single units, holistic surveys, and things that need full discovery context — do them in the lead.

## Master prompt: domain-writer subagent

Use this prompt verbatim (with placeholders filled) when dispatching each domain-writer. The prompt is self-contained because the subagent has no memory of the conversation.

```
You are writing one specific agent-docs domain doc for a software project. The lead Claude has already done discovery and decomposition; your job is to write the doc for ONE domain by reading the actual code.

CONTEXT FROM THE LEAD (filled in by the lead):
- Project root (absolute path): {ABS_PATH}
- Domain name: {DOMAIN_NAME}
- Domain root path(s), repo-relative: {ROOTS}
- One-line responsibility (from Phase 2 decomposition): {RESPONSIBILITY}
- Neighbors (depends on): {NEIGHBORS_IN}
- Neighbors (depended on by): {NEIGHBORS_OUT}
- Project conventions reference (read it): {CONVENTIONS_PATH}
- Existing context-map (optional, read if present): {CONTEXT_MAP_PATH_OR_NONE}
- Doc template you MUST follow (read it FIRST): {SKILL_DIR}/references/domain-doc-template.md
- Output path (write here, do not write elsewhere): agent-docs/domains/{DOMAIN_NAME}.md

WHAT TO DO, IN ORDER:

1. Read the template fully. Required sections are fixed; their order matters; tables are required (not prose). The template explains why each rule exists — internalize the why, don't just pattern-match.

2. Read the project conventions (one short file). Project-wide rules go in _meta/conventions.md, NOT in your domain doc. If you find yourself writing a rule that applies project-wide, stop — it doesn't belong here.

3. Map the domain's code:
   - Use Glob to enumerate files in {ROOTS}.
   - Identify entry points: main.py / index.ts / router / handler factories — files with public surface other code reaches into.
   - Identify the 5–15 most important files. Skip generated files, vendored code, fixtures.
   - For each, Read the top 25–50 lines (docstring + imports + first class/function) to confirm what it does. Don't deep-read.
   - For complex domains, Grep for `^class `, `^def `, `^async def `, `^export `, `^function ` in the root to get a symbol inventory.

4. Cross-reference the existing context-map if it exists. Look for:
   - Decisions (D-xxx) that affect this domain → cite them in Gotchas or Notes (don't restate).
   - Known issues (KI-xxx) tied to this code → cite in Gotchas.
   - Architecture notes that say where this domain fits in the bigger picture.

5. Fill EVERY section of the template, in order. Use the column headers from the template literally (the tech-lead linter checks them):

   - **Last verified**: today's date + current git HEAD short SHA (run `git rev-parse --short HEAD`).
   - **Root**: from inputs, exactly as given.
   - **When to read me**: one paragraph leading with the root path. Say what it covers AND what it explicitly doesn't (point to neighbor domains).
   - **Responsibility**: 2–4 sentences. State the boundary — what this domain does NOT own. Boundary > inclusion.
   - **Entry points**: table, 3–10 rows, columns `File | Symbol | What it does`. Real paths, real symbols. No invented names.
   - **Architecture**: 3–7 bullets, no prose paragraphs.
   - **Files of interest**: table, 5–20 rows, columns `Path | What it does`. Include line counts for files >100 lines in the description.
   - **Conventions**: 3–8 bullets — local to this domain only. If you can't think of any, write 1–2 and say so. Don't pad.
   - **Gotchas**: MANDATORY even if short. Non-obvious things, past bugs (cite IDs from the context map if known), counter-intuitive behavior. If you found nothing surprising — write 1–2 entries about "common false assumptions about this domain" and flag in your report that you didn't find documented gotchas.
   - **How to extend**: 3–6 common change types and where to make them.
   - **Neighbors**: use the IN/OUT lists provided in inputs. Don't invent neighbors. If you discover a real dependency that wasn't in the inputs — flag it in your report (do NOT silently add it; the lead checks bidirectionality across all docs).
   - **External integrations**: only if real. Skip the section if there are none.
   - **Tests**: location + run command + special fixtures. Look in `tests/`, `__tests__/`, or alongside source.
   - **Notes**: leave a single line `*(hand-written — preserved by update mode)*` and stop. User fills this.

6. Write the file at the output path. DO NOT touch any other file. DO NOT modify code.

7. Return a brief structured report (under 250 words):

CONSTRAINTS:
- Read-only on everything except your one output file.
- No marketing language: "robust", "elegant", "beautifully", "scalable", "production-grade", "seamlessly", "powerful", "comprehensive". Delete on sight.
- Tables MUST use the exact column headers from the template.
- DO NOT exceed 200 lines in the doc. If you would, write 180 lines and flag in your report that the domain may need splitting.
- DO NOT invent file paths or symbols. If unsure something exists, leave it out and flag the gap in the report.
- If the codebase contradicts an input from the lead (e.g., the responsibility doesn't fit what you found): write the best doc you can AND flag the contradiction prominently in your report. Don't try to "fix" the inputs.

REPORT FORMAT (return this in your final message):

```
DOMAIN: <name>
OUTPUT: agent-docs/domains/<name>.md (<line count> lines)
FILES READ: <count>
CONFIDENCE: high | medium | low

GAPS LEFT (things you couldn't verify):
- ...

FLAGS FOR TECH-LEAD REVIEW:
- ...  (e.g., "Discovered a dependency on `foo` not in inputs", "Doc hit 195 lines, may need split", "Could not find tests for this domain")

SUGGESTED FOLLOW-UPS:
- ...  (e.g., "Convention X looks project-wide, consider promoting to _meta/conventions.md")
```
```

## Master prompt: update-mode subagent

For `update <domain>` invoked on multiple domains in parallel. Slightly different from the writer because it must preserve handwritten content.

```
You are refreshing one existing agent-docs domain doc. The doc exists; your job is to compare it against current code and produce an updated version, preserving handwritten content.

CONTEXT:
- Domain name: {DOMAIN_NAME}
- Domain root path(s): {ROOTS}
- Existing doc path: agent-docs/domains/{DOMAIN_NAME}.md
- Last verified SHA (from doc frontmatter, or from _meta/last-verified.json): {LAST_SHA}
- Doc template: {SKILL_DIR}/references/domain-doc-template.md
- Update rules: {SKILL_DIR}/references/maintenance-rules.md

STEPS:

1. Read the existing doc fully. Note any handwritten content: `## Notes`, anything under `## Gotchas` that looks user-written (specific incident references, dated entries, first-person voice), conventions the user added.

2. Read the update rules. The key invariants:
   - Never silently delete a Gotcha. If a gotcha looks resolved, FLAG it; don't drop it.
   - Never reorder sections.
   - Preserve everything in `## Notes` verbatim.
   - Refresh: Last verified, Root, Entry points, Files of interest, Architecture bullets, Neighbors (with caution — see below).

3. Diff against current code:
   - `git log {LAST_SHA}..HEAD -- {ROOTS}` to see what changed.
   - Glob the root to see current file set.
   - For each file in the doc's Entry points / Files of interest tables — does it still exist? Has the symbol changed? Has it grown / shrunk significantly?

4. Re-derive each refreshable section. Keep diffs minimal: if a section is still accurate, leave it alone.

5. Update Last verified to today + current short SHA. Update _meta/last-verified.json entry for this domain.

6. Write the updated doc. DO NOT modify code.

7. Report what changed:

```
DOMAIN: <name>
COMMITS REVIEWED: <count> since <last sha>
SECTIONS UPDATED: <list, e.g., "Entry points (2 added, 1 removed), Files of interest (3 changed), Architecture (1 bullet revised)">
HANDWRITTEN PRESERVED: <list, e.g., "Notes section (12 lines), 2 user-added gotchas">
FLAGS:
- ...  (e.g., "Removed file `foo.py` from Files of interest — confirm not just moved", "Gotcha #3 about X may now be resolved; left intact, please verify")
```
```

## Tech-lead review pass (lead Claude, after subagents return)

After all writer/update subagents finish, the lead reads each report (NOT each full doc) and runs a consistency pass. The lead can defer the heavy doc-reading to a script.

### Step 1: Run the deterministic linter (script)

The skill ships `scripts/lint_docs.py` (described below). It checks:

- Every doc has the required headers, in order.
- Every doc has a `Last verified` line.
- No doc exceeds 200 lines.
- No banned phrases ("robust", "elegant", "beautifully", "scalable", "production-grade", "seamlessly", "powerful", "comprehensive").
- Tables use canonical column headers (`File | Symbol | What it does`, `Path | What it does`).
- No file paths in tables that don't actually exist on disk.
- Neighbors form a valid graph (no references to non-existent domain names).
- Bidirectional Neighbors: if A says "Depends on B", does B say "Depended on by A"? Flag asymmetries.

### Step 2: Read each subagent's report (NOT the full doc unless flagged)

Aggregate:
- Confidence distribution (how many high / medium / low).
- All FLAGS across reports — these need lead judgment.
- Domains flagged as possibly needing a split.
- Gaps left for human review.

### Step 3: Fix what's auto-fixable

- Bidirectional Neighbors asymmetries: pick one direction (whichever the subagent claimed more confidently) and apply to both sides.
- Banned phrases: delete and rewrite the sentence.
- Path overlap (two domains claim the same file): consult the decomposition; one of them is wrong. If unclear → surface to user.

### Step 4: Write MAP.md, cross-cutting.md, _meta files

These need all domain outputs to be in. Lead writes them after subagents finish:
- `MAP.md` from `references/map-template.md` + the actual domains in `domains/`.
- `cross-cutting.md` from `references/cross-cutting-template.md` + the cross-cutting concerns from Phase 2.
- `_meta/last-verified.json` from each subagent's "Last verified" line.
- `_meta/domain-paths.json` from the Phase 2 decomposition (directory roots SHOULD end with `/`).
- `_meta/conventions.md` lifted from root CLAUDE.md (manually, the lead does this once).
- `_meta/links.json` if a memory layer (`context-map-<slug>/`) exists — the cross-link pairing (shape in `references/schema.md` → Navigation Layer). Also populate the MAP.md `## Project memory` section and add the `../agent-docs/MAP.md` row to the memory `context-map.md` `## Linked Files`.

### Step 5: Surface to user

Final report to user:
- N domain docs written / updated.
- M flags requiring human review (with paths).
- Linter output: clean or list of issues.
- Diffs proposed for root CLAUDE.md and distributed CLAUDE.md files.
- Wait for user approval before applying file writes to anything outside `agent-docs/`.

## `scripts/lint_docs.py` (in this skill)

The lead invokes this after subagents finish. Read-only check, no writes.

It's deterministic and fast. Don't try to use Claude judgment for what a regex can decide.

```python
# Pseudocode for the lint script:
# - Walk agent-docs/domains/*.md
# - For each: check headers, table columns, length, banned phrases, last-verified line.
# - Build the depends-on graph; verify bidirectional consistency.
# - Verify _meta/domain-paths.json maps every domain to existing directories.
# - Verify MAP.md domain table matches files in domains/.
# - Output: tabular report of issues. Exit 1 if any issues.
```

(See the actual implementation in `scripts/lint_docs.py`.)

## Dispatch example (Phase 3 of init)

When the lead reaches Phase 3 with 18 domains in the decomposition:

1. Lead writes `_meta/domain-paths.json` and `_meta/conventions.md` first (these are inputs the subagents need).
2. Lead dispatches **18 Agent calls in a single turn** (all in one message with parallel `Agent` tool_use blocks), each with the writer master prompt filled in for that domain.
3. As each subagent returns, lead captures its report.
4. Once all 18 are back, lead runs `scripts/lint_docs.py`.
5. Lead reads the lint output + the 18 reports.
6. Lead does Step 3 (auto-fixes) — small inline edits, no new dispatches.
7. Lead writes MAP.md, cross-cutting.md, last-verified.json.
8. Lead writes distributed CLAUDE.md files (one quick subagent per domain, optional — these are tiny, can also be inline).
9. Lead proposes the root CLAUDE.md stanza diff.
10. Lead surfaces the final summary to the user.

For a typical complex project this is ~one main turn + 18 parallel subagent turns + cleanup. Wall-clock: 5–15 minutes depending on domain sizes. Single-Claude serial would be 60–120 minutes.

## When NOT to use subagents (anti-patterns)

- **For Phase 1/2**: subagents lose the holistic view. The lead needs to see the whole tree to identify boundaries; partitioning before you have boundaries makes no sense.
- **For "small" projects (≤5 domains)**: dispatch overhead exceeds gain.
- **For `update <single-domain>`**: one Agent call is just bureaucracy. Lead does it.
- **For `audit`**: it's a script-driven check, not a research task.
- **For cross-cutting.md / MAP.md**: these depend on ALL domain outputs. No way to parallelize the integration step itself.

## Cost note

Each subagent has its own context, its own tool calls, its own model invocation. Parallel dispatch trades **wall-clock time for total tokens**. For a 18-domain project this is unambiguously the right tradeoff (5–15 min × 1 = much better than 60–120 min × 1). For a 3-domain project the math flips — inline is fine.
