#!/usr/bin/env python3
"""Ensure agents always read context-map content first when working on a project.

Writes a "Project Context Map" stanza into agent-config files so any agent
opening the project (or any project, for global scope) is told to:
1. read `context-map-<slug>/context-map.md` first;
2. treat known-issues / decisions as project memory;
3. never commit context-map content.

Usage:
    # Global rule for every project on this machine (~/.claude/CLAUDE.md)
    python3 ensure_agent_rule.py --scope global

    # Per-project rule (auto-detects slug from the context-map-* folder)
    python3 ensure_agent_rule.py --scope project --project /path/to/project

    # Per-project, choose target file explicitly
    python3 ensure_agent_rule.py --scope project --project /path --file AGENTS.md

    # Dry-run / check
    python3 ensure_agent_rule.py --scope global --dry-run
    python3 ensure_agent_rule.py --scope global --check

Idempotent: managed markers `<!-- managed by context-map skill: BEGIN/END agent-rule -->`
delimit the block. Re-running with the same content is a no-op; if the block
content changed, the script replaces it in place. Content outside the markers
is left alone.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


MARKER_BEGIN = "<!-- managed by context-map skill: BEGIN agent-rule -->"
MARKER_END = "<!-- managed by context-map skill: END agent-rule -->"


GLOBAL_BLOCK = f"""{MARKER_BEGIN}
## Project Context Maps (global rule)

- When opening any project, check its root for a folder matching `context-map-*/`. If present, read `context-map.md` inside it before planning or editing, then read the split files it links to.
- Treat `known-issues.md`, `decisions.md`, and `tasks.md` inside that folder as project memory. Flag conflicts before implementing changes that contradict them.
- Never commit `context-map-*/` content. It is project memory and may contain private operational notes; treat it like `.env`. If a `git add` would include it, stop and add the path to `.gitignore` instead.
{MARKER_END}
"""


PROJECT_BLOCK_TEMPLATE = f"""{MARKER_BEGIN}
## Project Context Map

- Before planning or editing, read `context-map-{{slug}}/context-map.md` and the split files it links to (`known-issues.md`, `decisions.md`, `tasks.md`, `gotchas.md`; `architecture.md` if present).
- Treat `Known Issues`, `Decisions`, and the `Agent Conflict Protocol` section as project memory.
- If a requested change conflicts with a Known Issue or Decision, explain the conflict and ask the user before proceeding.
- Update the context map when entry points, architecture, deploy flow, run/test commands, DB schema, auth, payments, or external integrations change; when a significant decision is made or reversed; when a known issue is discovered, fixed, or accepted; when a fix prevents a future regression.
- Do not put secrets, tokens, passwords, or private credentials in the context map.
- Never commit `context-map-{{slug}}/` content. The skill ensures `.gitignore` excludes it; if you find this folder being staged, remove it from the index and verify the project's `.gitignore` carries the rule.
{MARKER_END}
"""


def global_target() -> Path:
    home = os.environ.get("CLAUDE_HOME")
    if home:
        return Path(home).expanduser() / "CLAUDE.md"
    return Path.home() / ".claude" / "CLAUDE.md"


def find_unique_slug(project: Path) -> str | None:
    if not project.is_dir():
        return None
    folders = [p for p in project.iterdir() if p.is_dir() and p.name.startswith("context-map-")]
    if len(folders) != 1:
        return None
    return folders[0].name.removeprefix("context-map-")


def pick_project_target(project: Path, file_choice: str | None) -> Path:
    if file_choice:
        return project / file_choice
    for candidate in ("CLAUDE.md", "AGENTS.md"):
        if (project / candidate).exists():
            return project / candidate
    return project / "CLAUDE.md"


def install_or_update(path: Path, block: str) -> tuple[str, bool]:
    """Append or replace the managed block at `path`. Returns (message, changed)."""
    existing = path.read_text(encoding="utf-8") if path.exists() else ""

    if MARKER_BEGIN in existing:
        if MARKER_END not in existing:
            return f"begin marker found but no end marker in {path}; refusing to write", False
        begin_idx = existing.index(MARKER_BEGIN)
        end_idx = existing.index(MARKER_END, begin_idx) + len(MARKER_END)
        line_end = existing.find("\n", end_idx)
        line_end = len(existing) if line_end < 0 else line_end + 1
        line_start = existing.rfind("\n", 0, begin_idx) + 1  # 0 if not found
        old_block = existing[line_start:line_end]
        if old_block.strip() == block.strip():
            return f"already up to date: {path}", False
        new_text = existing[:line_start] + block + existing[line_end:]
        path.write_text(new_text, encoding="utf-8")
        return f"updated managed block in {path}", True

    path.parent.mkdir(parents=True, exist_ok=True)
    if existing and not existing.endswith("\n"):
        existing += "\n"
    sep = "\n" if existing else ""
    new_text = existing + sep + block
    path.write_text(new_text, encoding="utf-8")
    return f"installed managed block in {path}", True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scope", choices=["global", "project"], required=True)
    parser.add_argument("--project", help="Project root (required for --scope project)")
    parser.add_argument("--slug", help="Override auto-detected slug")
    parser.add_argument("--file", choices=["CLAUDE.md", "AGENTS.md"], help="Force target filename for project scope")
    parser.add_argument("--check", action="store_true", help="Report status, do not write")
    parser.add_argument("--dry-run", action="store_true", help="Show planned action without writing")
    args = parser.parse_args()

    if args.scope == "global":
        path = global_target()
        block = GLOBAL_BLOCK
    else:
        if not args.project:
            print("error: --project is required when --scope project", file=sys.stderr)
            return 2
        project = Path(args.project).expanduser().resolve()
        slug = args.slug or find_unique_slug(project)
        if not slug:
            print(
                "error: --slug not given and could not auto-detect a single context-map-* folder",
                file=sys.stderr,
            )
            return 2
        path = pick_project_target(project, args.file)
        block = PROJECT_BLOCK_TEMPLATE.format(slug=slug)

    text = path.read_text(encoding="utf-8") if path.exists() else ""

    if args.check:
        installed = MARKER_BEGIN in text and MARKER_END in text
        print(f"{path}: {'installed' if installed else 'missing'}")
        return 0 if installed else 1

    if args.dry_run:
        if MARKER_BEGIN in text and MARKER_END in text:
            begin = text.index(MARKER_BEGIN)
            end = text.index(MARKER_END, begin) + len(MARKER_END)
            old = text[text.rfind("\n", 0, begin) + 1:text.find("\n", end) + 1 if text.find("\n", end) >= 0 else len(text)]
            if old.strip() == block.strip():
                print(f"[dry-run] {path}: already up to date; no change")
            else:
                print(f"[dry-run] {path}: would replace existing managed block")
                print("--- new block ---")
                print(block)
        else:
            print(f"[dry-run] {path}: would append managed block:")
            print("--- block ---")
            print(block)
        return 0

    message, _changed = install_or_update(path, block)
    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
