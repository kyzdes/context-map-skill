#!/usr/bin/env python3
"""Self-contained regression tests for the context-map skill scripts.

Zero-dependency (stdlib only, no pytest). Run:

    python3 skills/context-map/tests/test_skill.py

Exits non-zero if any test fails. Wired into CI (validate-plugin.yml).

Covers the behaviours that were verified ad-hoc during the v0.3 merge so they
don't silently regress: the freshness-gate segment match, reconcile's
zero-data-loss + idempotency, the legacy-stanza replacement, v2/v3 validation,
the lint nav-only false-positive fix, and the audit orchestrator.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"

_PASS = 0
_FAIL = 0


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check(label: str, cond: bool) -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


def run_script(name: str, *args: str) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(SCRIPTS / f"{name}.py"), *args],
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


# ---------- memory frontmatter helper ----------

def write_memory(folder: Path, version: int = 3, nav: bool = True, scale: str = "XS") -> None:
    folder.mkdir(parents=True, exist_ok=True)
    fm = ["---", f"context_map_version: {version}", "project_id: t", "project_slug: t",
          'name: "T"', "repo_path: /tmp/t", "repo_url: null", "visibility: private",
          "status: active", f"scale: {scale}", "primary_stack: [Python]"]
    if nav:
        fm.append("nav_layer: agent-docs")
    fm += ["last_updated: 2026-05-26", "last_verified_vs_code: 2026-05-26",
           "generator: context-map-skill/0.3", "---", "",
           "## Project Identity", "T.", "",
           "## Current Phase", "- Active focus: x", "",
           "## Tech Stack", "", "| Layer | Tech | Version | Notes |",
           "|-------|------|---------|-------|", "| lang | Python | - | - |", "",
           "## Directory Structure", "- x", "",
           "## Linked Files", "", "- `decisions.md` — decisions.", "",
           "## Confidence Notes", "", "| Claim | Source | Confidence | Evidence | Needs Human? |",
           "|-------|--------|------------|----------|--------------|",
           "| x | inferred | inferred | x | no |", "",
           "## Update Protocol", "- x", ""]
    (folder / "context-map.md").write_text("\n".join(fm))


def write_nav(project: Path, verified_line: str = "2026-05-10 @ abc") -> None:
    (project / "agent-docs" / "domains").mkdir(parents=True, exist_ok=True)
    (project / "agent-docs" / "_meta").mkdir(parents=True, exist_ok=True)
    (project / "agent-docs" / "MAP.md").write_text(
        f"# Project Map: T\n\n**Last verified**: {verified_line}\n\n"
        "## Domains\n| Domain | Root path | Responsibility | Deep doc |\n"
        "|--------|-----------|----------------|----------|\n"
        "| api | `app/` | x | [api.md](domains/api.md) |\n"
    )
    (project / "agent-docs" / "domains" / "api.md").write_text("# Domain: api\n\n**Last verified**: 2026-05-10 @ abc\n")
    (project / "agent-docs" / "_meta" / "domain-paths.json").write_text('{"api":["app/"]}\n')


# ---------- tests ----------

def test_gate_segment_match() -> None:
    print("test_gate_segment_match")
    g = load("check_agent_docs_freshness")
    m = {"api": ["backend/app"], "ai": ["backend/app/services/ai.py"]}
    check("dir root matches child", g.map_path_to_domain("backend/app/x.py", m) == "api")
    check("dir root does NOT match sibling", g.map_path_to_domain("backend/application/x.py", m) is None)
    check("exact file root matches", g.map_path_to_domain("backend/app/services/ai.py", m) in ("api", "ai"))
    check("unrelated path is None", g.map_path_to_domain("frontend/x.tsx", m) is None)


def test_validator_versions() -> None:
    print("test_validator_versions")
    tmp = Path(tempfile.mkdtemp())
    write_memory(tmp / "context-map-t", version=3)
    rc, _ = run_script("validate_context_map", str(tmp / "context-map-t"))
    check("v3 passes", rc == 0)

    tmp2 = Path(tempfile.mkdtemp())
    write_memory(tmp2 / "context-map-t", version=2, nav=False)
    rc2, _ = run_script("validate_context_map", str(tmp2 / "context-map-t"))
    check("v2 back-compat passes", rc2 == 0)

    tmp3 = Path(tempfile.mkdtemp())
    write_memory(tmp3 / "context-map-t", version=4)
    rc3, out3 = run_script("validate_context_map", str(tmp3 / "context-map-t"))
    check("v4 rejected", rc3 != 0 and "one of [2, 3]" in out3)


def test_legacy_stanza_replacement() -> None:
    print("test_legacy_stanza_replacement")
    ear = load("ensure_agent_rule")
    legacy = ("# P\n\nIntro.\n\n## Project Context Map\n\n"
              f"{ear.LEGACY_BEGIN}\n- read context-map-t/context-map.md\n{ear.LEGACY_END}\n\n"
              "## Workflow\nkeep me\n")
    p = Path(tempfile.mkdtemp()) / "CLAUDE.md"
    p.write_text(legacy)
    block = ear.build_project_block("t", "both")
    msg, changed = ear.install_or_update(p, block)
    out = p.read_text()
    check("changed", changed)
    check("legacy markers gone", ear.LEGACY_BEGIN not in out)
    check("new markers present", ear.MARKER_BEGIN in out and ear.MARKER_END in out)
    check("intro preserved", "Intro." in out)
    check("trailing section preserved", "keep me" in out)
    check("no duplicate heading", out.count("## Project Context Map") == 0)
    check("both layers mentioned", "agent-docs/MAP.md" in out and "context-map-t/" in out)
    _, changed2 = ear.install_or_update(p, block)
    check("idempotent second run", not changed2)


def test_gitignore_guard() -> None:
    print("test_gitignore_guard")
    eg = load("ensure_gitignore")
    check("nav layer flagged as ignored", eg.nav_layer_ignored("agent-docs/\n"))
    check("plain comment not flagged", not eg.nav_layer_ignored("# mentions agent-docs/ in a comment\ncontext-map-*/\n"))


def test_reconcile_zero_loss() -> None:
    print("test_reconcile_zero_loss")
    proj = Path(tempfile.mkdtemp()) / "proj"
    write_memory(proj / "context-map-t", version=2, nav=False)
    decisions = "## Decisions\n\n| ID | Date | Decision | Rationale | Consequence | Do Not Repeat |\n|----|------|----------|-----------|-------------|---------------|\n| D-001 | 2026-04-01 | x | y | z | w |\n"
    (proj / "context-map-t" / "decisions.md").write_text(decisions)
    write_nav(proj)
    (proj / "pyproject.toml").write_text('[project]\nname="t"\n')

    before = (proj / "context-map-t" / "decisions.md").read_bytes()
    rc, _ = run_script("reconcile", "--project", str(proj), "--apply")
    after = (proj / "context-map-t" / "decisions.md").read_bytes()
    main_txt = (proj / "context-map-t" / "context-map.md").read_text()

    check("reconcile exit 0", rc == 0)
    check("decisions.md byte-identical", before == after)
    check("links.json written", (proj / "agent-docs" / "_meta" / "links.json").is_file())
    check("MAP row added once", main_txt.count("agent-docs/MAP.md") == 1)
    check("nav_layer added", "nav_layer: agent-docs" in main_txt)
    check("version bumped to 3", "context_map_version: 3" in main_txt)

    # idempotency
    rc2, out2 = run_script("reconcile", "--project", str(proj), "--apply")
    main_txt2 = (proj / "context-map-t" / "context-map.md").read_text()
    check("reconcile idempotent: one MAP row", main_txt2.count("agent-docs/MAP.md") == 1)
    check("reconcile idempotent: one nav_layer", main_txt2.count("nav_layer:") == 1)


def test_lint_nav_only_no_false_positive() -> None:
    print("test_lint_nav_only_no_false_positive")
    proj = Path(tempfile.mkdtemp()) / "nav-only"
    write_nav(proj)  # navigation layer, NO context-map-*/ memory folder
    rc, out = run_script("lint_docs", "--root", str(proj))
    check("no spurious memory-link warning", "no cross-link to the memory" not in out and "memory layer present" not in out)


def test_audit_both_layers() -> None:
    print("test_audit_both_layers")
    proj = Path(tempfile.mkdtemp()) / "proj"
    write_memory(proj / "context-map-t", version=3)
    write_nav(proj)
    rc, out = run_script("audit", "--project", str(proj))
    check("audit prints MEMORY section", "MEMORY LAYER" in out)
    check("audit prints NAVIGATION section", "NAVIGATION LAYER" in out)


def test_tracked_memory_detection() -> None:
    print("test_tracked_memory_detection")
    eg = load("ensure_gitignore")
    proj = Path(tempfile.mkdtemp()) / "repo"
    proj.mkdir()
    git = lambda *a: subprocess.run(["git", "-C", str(proj), *a], capture_output=True, text=True)
    git("init", "-q")
    git("config", "user.email", "t@t.t"); git("config", "user.name", "t")
    write_memory(proj / "context-map-t", version=3)
    # -f: simulate "committed before the ignore rule existed" (and survive a
    # machine whose global git excludes already ignore context-map-*/).
    git("add", "-f", "context-map-t/context-map.md")
    git("commit", "-q", "-m", "add memory")
    tracked = eg.tracked_memory_folders(proj)
    check("detects committed memory folder", "context-map-t/" in tracked)
    # a fresh untracked folder must NOT be flagged
    write_memory(proj / "context-map-untracked", version=3)
    tracked2 = eg.tracked_memory_folders(proj)
    check("untracked folder not flagged", "context-map-untracked/" not in tracked2)


def test_inspect_domain_candidates() -> None:
    print("test_inspect_domain_candidates")
    import json
    # Exercise the CLI path (what the skill actually uses) against the repo root.
    repo = SCRIPTS.parents[2]
    rc, out = run_script("inspect_project", str(repo), "--format", "json")
    check("inspect exit 0", rc == 0)
    try:
        data = json.loads(out)
        ok_key = "domain_candidates" in data
    except (json.JSONDecodeError, ValueError):
        ok_key = False
    check("inspect json has domain_candidates key", ok_key)


def main() -> int:
    tests = [
        test_gate_segment_match,
        test_validator_versions,
        test_legacy_stanza_replacement,
        test_gitignore_guard,
        test_reconcile_zero_loss,
        test_lint_nav_only_no_false_positive,
        test_audit_both_layers,
        test_tracked_memory_detection,
        test_inspect_domain_candidates,
    ]
    for t in tests:
        try:
            t()
        except Exception as exc:  # noqa: BLE001
            global _FAIL
            _FAIL += 1
            print(f"  FAIL {t.__name__}: {type(exc).__name__}: {exc}")
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
