#!/usr/bin/env python3
"""Ensure context-map folders are gitignored at the project and/or global level.

Context-map folders are project memory for AI agents, not source code. They can
contain decisions, gotchas, and private operational notes that should never be
pushed to public hosting. This script adds an idempotent ignore rule.

Usage:
    # Per-project: write into <project>/.gitignore
    python3 ensure_gitignore.py --scope project --project /path/to/project

    # Global: write into the user's global git excludes file
    python3 ensure_gitignore.py --scope global

    # Check status without writing
    python3 ensure_gitignore.py --scope global --check
    python3 ensure_gitignore.py --scope project --project /path/to/project --check

    # Show what would be written
    python3 ensure_gitignore.py --scope global --dry-run

Exit codes:
    0  rule installed (or already present in --check mode)
    1  rule missing in --check mode (with --check) OR write failed
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


MARKER_BEGIN = "# managed by context-map skill — do not edit between markers"
MARKER_END = "# end context-map skill section"

BLOCK = f"""{MARKER_BEGIN}
# context-map-<slug>/ folders are the MEMORY layer: project memory for AI coding
# agents. They are not source code and may contain private operational notes,
# decisions, and known issues that must not be pushed to public hosting.
# NOTE: the NAVIGATION layer (agent-docs/) is the opposite — it MUST stay
# committed so the freshness gate can run on it. Do not add agent-docs/ here.
context-map-*/
{MARKER_END}
"""

# Patterns that would (wrongly) ignore the committed navigation layer.
NAV_IGNORE_TOKENS = {"agent-docs", "agent-docs/", "/agent-docs", "/agent-docs/", "agent-docs/**"}


def resolve_global_excludes_path() -> Path:
    """Return the path of the user's global git excludes file.

    Resolution order, matching git's own logic:
    1. `git config --global --get core.excludesfile`
    2. $XDG_CONFIG_HOME/git/ignore
    3. ~/.config/git/ignore
    """
    if shutil.which("git"):
        try:
            result = subprocess.run(
                ["git", "config", "--global", "--get", "core.excludesfile"],
                capture_output=True, text=True, timeout=5, check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return Path(os.path.expanduser(result.stdout.strip()))
        except (OSError, subprocess.SubprocessError):
            pass

    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg).expanduser() / "git" / "ignore"
    return Path.home() / ".config" / "git" / "ignore"


def project_excludes_path(project: Path) -> Path:
    return project / ".gitignore"


def has_managed_block(text: str) -> bool:
    return MARKER_BEGIN in text and MARKER_END in text


def has_rule(text: str) -> bool:
    """Loose check: any active line that matches our pattern."""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line in {"context-map-*/", "context-map-*", "context-map-*/**"}:
            return True
    return False


def nav_layer_ignored(text: str) -> bool:
    """True if a rule would ignore the committed navigation layer (agent-docs/).

    The navigation layer MUST stay committed for the CI freshness gate to work,
    so an existing rule that ignores it is a misconfiguration worth surfacing.
    """
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line in NAV_IGNORE_TOKENS:
            return True
    return False


def install(path: Path) -> tuple[bool, str]:
    """Append the managed block. Idempotent. Returns (changed, message)."""
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if has_managed_block(existing):
        return False, f"already managed: {path}"
    if has_rule(existing):
        return False, f"rule already present (unmanaged) in {path}; not modifying"
    path.parent.mkdir(parents=True, exist_ok=True)
    if existing and not existing.endswith("\n"):
        existing += "\n"
    new_content = existing + ("\n" if existing else "") + BLOCK
    path.write_text(new_content, encoding="utf-8")
    return True, f"installed managed block in {path}"


def tracked_memory_folders(project: Path) -> list[str]:
    """Return distinct already-tracked context-map-*/ folders in the project.

    A `.gitignore` rule does NOT untrack files already committed. If the memory
    layer was committed before the rule existed (common when reconciling old
    projects), private notes are still in the repo and the user must run
    `git rm -r --cached` to stop tracking them (files stay on disk).
    """
    if shutil.which("git") is None or not (project / ".git").exists():
        return []
    folders = set()
    # git ls-files does not glob `context-map-*/` in a pathspec (the `*` is
    # literal), so glob the dirs ourselves and ask git about each literal path.
    for d in sorted(project.glob("context-map-*")):
        if not d.is_dir():
            continue
        try:
            out = subprocess.run(
                ["git", "-C", str(project), "ls-files", "--", d.name],
                capture_output=True, text=True, timeout=10, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if out.returncode == 0 and out.stdout.strip():
            folders.add(d.name + "/")
    return sorted(folders)


def configure_git_excludesfile(target: Path) -> bool:
    """Ensure git's core.excludesfile points to `target` (only if currently unset)."""
    if shutil.which("git") is None:
        return False
    try:
        check = subprocess.run(
            ["git", "config", "--global", "--get", "core.excludesfile"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    if check.returncode == 0 and check.stdout.strip():
        # already set, leave it alone (we wrote into the resolved path)
        return False
    try:
        subprocess.run(
            ["git", "config", "--global", "core.excludesfile", str(target)],
            capture_output=True, text=True, timeout=5, check=True,
        )
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scope", choices=["global", "project"], required=True)
    parser.add_argument("--project", help="Project root (required when --scope project)")
    parser.add_argument("--check", action="store_true", help="Report status, do not write")
    parser.add_argument("--dry-run", action="store_true", help="Show planned action without writing")
    args = parser.parse_args()

    project_root: Path | None = None
    if args.scope == "project":
        if not args.project:
            print("error: --project is required when --scope project", file=sys.stderr)
            return 2
        project_root = Path(args.project).expanduser().resolve()
        path = project_excludes_path(project_root)
    else:
        path = resolve_global_excludes_path()

    text = path.read_text(encoding="utf-8") if path.exists() else ""

    # Guard: the navigation layer (agent-docs/) must stay committed. Warn loudly
    # if the target gitignore would exclude it — this silently breaks the gate.
    if nav_layer_ignored(text):
        print(
            f"[context-map] WARN: {path} appears to ignore `agent-docs/` — the "
            "navigation layer must stay committed for the freshness gate. "
            "Remove that rule.",
            file=sys.stderr,
        )

    if args.check:
        installed = has_managed_block(text) or has_rule(text)
        print(f"{path}: {'installed' if installed else 'missing'}")
        return 0 if installed else 1

    if args.dry_run:
        if has_managed_block(text):
            print(f"[dry-run] {path}: already managed; no change")
        elif has_rule(text):
            print(f"[dry-run] {path}: rule already present (unmanaged); no change")
        else:
            print(f"[dry-run] would append managed block to {path}")
            print("--- block ---")
            print(BLOCK)
        return 0

    changed, message = install(path)
    print(message)

    if args.scope == "global" and changed:
        if configure_git_excludesfile(path):
            print(f"set git config --global core.excludesfile = {path}")

    # A gitignore rule does not untrack already-committed memory. Surface it.
    if project_root is not None:
        tracked = tracked_memory_folders(project_root)
        if tracked:
            joined = " ".join(tracked)
            print(
                f"[context-map] WARN: memory folder(s) already tracked in git: {joined}\n"
                f"  .gitignore does NOT untrack committed files — private memory is still in the repo.\n"
                f"  Stop tracking (files stay on disk), then commit:\n"
                f"    git -C {project_root} rm -r --cached {joined}",
                file=sys.stderr,
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
