#!/usr/bin/env python3
"""Audit both documentation layers in one pass, one report.

Runs the memory-layer validator (`validate_context_map.py`) on each
`context-map-<slug>/` folder and the navigation-layer linter (`lint_docs.py`)
on `agent-docs/`, then prints a single report with a MEMORY section and a
NAVIGATION section. This is the orchestration behind the skill's `audit` mode.

Read-only. Exit codes:
  0 — both layers clean (no errors; warnings allowed)
  1 — at least one layer reported errors
  2 — nothing to audit (neither layer present)

Usage:
  python3 audit.py --project /path/to/project
  python3 audit.py --project /path --layer memory   # one layer only
  python3 audit.py --project /path --layer nav
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def _run(script: str, *args: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / script), *args],
        capture_output=True, text=True,
    )
    return proc.returncode, (proc.stdout + proc.stderr).rstrip()


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit memory + navigation doc layers.")
    ap.add_argument("--project", required=True, help="Project root")
    ap.add_argument("--layer", choices=["memory", "nav", "both"], default="both")
    args = ap.parse_args()

    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        print(f"error: {project} is not a directory", file=sys.stderr)
        return 2

    do_mem = args.layer in ("memory", "both")
    do_nav = args.layer in ("nav", "both")

    mem_folders = [
        p for p in sorted(project.glob("context-map-*"))
        if (p / "context-map.md").is_file()
    ]
    has_nav = (project / "agent-docs" / "MAP.md").exists()

    any_layer = (do_mem and mem_folders) or (do_nav and has_nav)
    if not any_layer:
        print(f"[audit] nothing to audit in {project} (no context-map-*/ or agent-docs/).")
        return 2

    errors = False
    print(f"[audit] {project}\n")

    if do_mem:
        print("=" * 60)
        print("MEMORY LAYER  (context-map-<slug>/)")
        print("=" * 60)
        if not mem_folders:
            print("  (no memory layer present)")
        for folder in mem_folders:
            rc, out = _run("validate_context_map.py", str(folder))
            print(out or f"  {folder.name}: (no output)")
            if rc != 0:
                errors = True
        print()

    if do_nav:
        print("=" * 60)
        print("NAVIGATION LAYER  (agent-docs/)")
        print("=" * 60)
        if not has_nav:
            print("  (no navigation layer present)")
        else:
            rc, out = _run("lint_docs.py", "--root", str(project))
            print(out or "  (no output)")
            if rc != 0:
                errors = True
        print()

    print("=" * 60)
    print(f"[audit] result: {'FAIL — errors found' if errors else 'OK — no errors'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
