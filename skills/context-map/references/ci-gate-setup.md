# Policy C: CI-enforced maintenance (default)

This is the only policy that makes "обновлять беспрекословно" actually true. It blocks merge/commit if the code in a domain changed without the corresponding `agent-docs/domains/<name>.md` being updated in the same change set.

Without this layer, instructions and Stop-hook reminders catch maybe 70–90% of misses. Policy C catches ≥99% — and the remaining ≤1% is users explicitly skipping via a documented escape hatch.

## What gets installed

1. **`scripts/check_agent_docs_freshness.py`** — the gate script. Zero deps, just stdlib + git. Lives in the project's `scripts/` folder.
2. **Local pre-commit hook** — runs the script before each commit. The user picks one of three integration styles (see below).
3. **GitHub Action workflow** — runs the script on every PR. Hard gate before merge.
4. **Escape hatch documented in root `CLAUDE.md`** — so the agent knows the correct way to skip.

## The gate script

Path in the project after install: `scripts/check_agent_docs_freshness.py`. Source-of-truth template lives in this skill at `scripts/check_agent_docs_freshness.py`.

Behavior:
- Compute the set of files changed since `--base` (defaults to `HEAD~1` locally, `origin/<base_ref>` in CI).
- Map each changed file to a domain via `agent-docs/_meta/domain-paths.json`.
- Filter out **ignored** patterns (Markdown, tests, fixtures, lockfiles, snapshots) — these don't trigger the gate.
- If any code-domain X was touched and `agent-docs/domains/X.md` was **not** touched in the same change set → **fail** with the exact command to fix.
- Parse commit messages for `[skip-agent-docs]` or `[skip-agent-docs: dom1, dom2]` escape hatch.

Exit codes: `0` = pass, `1` = stale docs, `2` = misconfigured (missing `domain-paths.json`).

## Pre-commit integration (pick one)

The local hook is best-effort — the source of truth is the GitHub Action. The local hook just gives the user/agent feedback before pushing.

### Option A — pre-commit framework (most projects)

If `.pre-commit-config.yaml` exists, append:
```yaml
- repo: local
  hooks:
    - id: agent-docs-freshness
      name: agent-docs freshness
      entry: python scripts/check_agent_docs_freshness.py --base HEAD~1
      language: system
      pass_filenames: false
      stages: [commit]
```

### Option B — husky (Node-heavy projects)

In `.husky/pre-commit`, append:
```sh
python scripts/check_agent_docs_freshness.py --base HEAD~1 || exit 1
```

### Option C — raw `.git/hooks/pre-commit` (no framework)

This is per-clone, not tracked. Install via a setup script (`scripts/install-hooks.sh`) so each clone runs it once:
```sh
cat > .git/hooks/pre-commit <<'EOF'
#!/usr/bin/env bash
python scripts/check_agent_docs_freshness.py --base HEAD~1
EOF
chmod +x .git/hooks/pre-commit
```

Pick the option that matches the project. For ManAurum: husky+node sit alongside Python — Option B feels native if husky is installed; otherwise Option C with a tracked install script.

## GitHub Action

Create `.github/workflows/agent-docs-gate.yml`:

```yaml
name: agent-docs gate

on:
  pull_request:
    paths:
      # Trigger on any code change. Add/remove paths to match your domain roots.
      - "backend/**"
      - "frontend/**"
      - "apps/**"
      - "addon/**"
      - "library/**"
      - "manaurum-cli-py/**"
      - "agent-docs/**"
      - "scripts/check_agent_docs_freshness.py"

jobs:
  freshness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # full history so origin/<base> is reachable

      - name: Check agent-docs freshness
        run: |
          python scripts/check_agent_docs_freshness.py \
            --base "origin/${{ github.base_ref }}"
```

Place it alongside existing CI workflows (e.g., next to `ci-frontend.yml` / `ci-backend.yml`).

Add the job to **required status checks** in the repo settings (Settings → Branches → branch protection rules → "Require status checks to pass"). Without this step the workflow runs but doesn't block merge — easy to miss.

## Escape hatch (documented in root `CLAUDE.md`)

Append to the navigation stanza (already added in Phase 3):

```markdown
### Skipping the agent-docs gate

For trivial changes that don't affect the structure described in the domain doc (typos, comments, formatting, test-only changes, lockfile bumps, generated files) — skip the gate by adding to ANY commit message in the change set:

`[skip-agent-docs]` — skip all touched domains
`[skip-agent-docs: domain1, domain2]` — skip only listed domains

When to use it:
- Typo / comment / docstring fix in code: OK to skip.
- Pure test-only changes that don't reflect a behavior change: OK.
- Refactor that preserves entry points and architecture: OK if you can defend "the domain doc would not change".

When NOT to use it (will create silent rot):
- Any new public function/handler/route.
- Renaming / moving / deleting files listed in the domain doc.
- Architecture changes (new dispatch layer, new entry point, new neighbor).
- New gotcha-worthy behavior.

If unsure: run `context-map skill: update <domain>` instead. Two minutes now beats a stale doc later.
```

## What the script doesn't catch (and what does)

- **Quality of the update** — the script only checks that the doc file was modified, not that the modification was meaningful. A one-character whitespace change passes. → Mitigation: `audit` mode periodically + tech-lead review on PRs.
- **Doc drift across domains** — if A is updated but B (a neighbor whose code didn't change but whose section about A is now wrong) is not. → Mitigation: `audit` flags via the bidirectional-Neighbors check; tech-lead review during multi-domain refactors.
- **Generated docs / vendored code** — anything in `node_modules/`, `.next/`, `dist/`, `build/`. → Already filtered by the ignore patterns in the script.

The realistic coverage with all four layers active:
- L1 instructions: catches ~50–70%.
- L1 + L2 stop-hook: ~85–90%.
- L1 + L2 + L3 CI gate: ~99%.
- L1 + L2 + L3 + L4 periodic audit: catches the remaining drift over time.

## Installation flow during Phase 4

When the skill installs Policy C:
1. Copy `scripts/check_agent_docs_freshness.py` from the skill's `scripts/` into the project's `scripts/`.
2. Detect which pre-commit style the project uses (`.pre-commit-config.yaml`, `.husky/`, neither) → propose the matching option.
3. Generate the GitHub Action workflow → show diff → wait for approval.
4. Append the escape-hatch section to root `CLAUDE.md` → show diff → wait for approval.
5. Tell the user: "Now go to Settings → Branches → required checks and add `agent-docs gate / freshness`."
6. Verify by running the script locally with `--base HEAD~5` (or similar) on the existing history and reporting how many domains would fail had the gate existed.

If the project does not use GitHub Actions, fall back to whatever CI it has (GitLab CI, CircleCI, Buildkite). The script itself is CI-agnostic — only the workflow file changes. Note this in the install summary.

## Removing the gate

If the user wants to remove Policy C later:
1. Delete `.github/workflows/agent-docs-gate.yml`.
2. Remove the pre-commit entry (Option A/B/C as installed).
3. Optionally delete `scripts/check_agent_docs_freshness.py`.
4. The required status check setting in repo settings must be removed manually.

Keep the `agent-docs/` folder either way — the docs still help even without the gate, just at lower coverage.
