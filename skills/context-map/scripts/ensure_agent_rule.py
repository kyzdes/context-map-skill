#!/usr/bin/env python3
"""Ensure agents read this project's docs first — both layers.

Writes ONE unified managed stanza into agent-config files telling any agent
opening the project (or any project, for global scope) to:
1. read `agent-docs/MAP.md` first (navigation, committed) → the owning domain doc;
2. read `context-map-<slug>/context-map.md` (memory, gitignored) before planning;
3. treat known-issues / decisions as project memory and flag conflicts;
4. never commit `context-map-*/`; keep `agent-docs/` committed.

The stanza is composed from the layers that exist (`--layers nav|memory|both`),
so a memory-only project is not told to read a navigation layer it lacks.

Usage:
    # Global rule for every project on this machine (~/.claude/CLAUDE.md)
    python3 ensure_agent_rule.py --scope global

    # Per-project rule (auto-detects slug from the context-map-* folder)
    python3 ensure_agent_rule.py --scope project --project /path/to/project

    # Only reference the navigation layer (no memory folder yet)
    python3 ensure_agent_rule.py --scope project --project /path --layers nav

    # Per-project, choose target file explicitly
    python3 ensure_agent_rule.py --scope project --project /path --file AGENTS.md

    # Dry-run / check
    python3 ensure_agent_rule.py --scope global --dry-run
    python3 ensure_agent_rule.py --scope global --check

Idempotent: managed markers `<!-- managed by context-map skill: BEGIN/END agent-rule -->`
delimit the block. Re-running with the same content is a no-op; if the block
content changed, the script replaces it in place. A LEGACY memory-only stanza
(older marker syntax) is detected and replaced rather than duplicated. Content
outside the markers is left alone.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


MARKER_BEGIN = "<!-- managed by context-map skill: BEGIN agent-rule -->"
MARKER_END = "<!-- managed by context-map skill: END agent-rule -->"

# Legacy markers written by older versions of this skill (memory-only stanza).
# `reconcile` must recognize these so it REPLACES the old block in place rather
# than appending a second, duplicate stanza. The legacy block was preceded by a
# `## Project Context Map` heading; we strip that too.
LEGACY_BEGIN = "<!-- managed by context-map skill; edit above/below this section freely -->"
LEGACY_END = "<!-- end context-map skill section -->"
LEGACY_HEADING = "## Project Context Map"


GLOBAL_BLOCK = f"""{MARKER_BEGIN}
## Project Docs (global rule)

- When opening any project, check its root for `agent-docs/MAP.md` (navigation, committed) and a folder matching `context-map-*/` (memory, gitignored).
- If `agent-docs/MAP.md` exists, read it FIRST to find which domain owns the code you'll touch, then read that `agent-docs/domains/<name>.md` before editing.
- If `context-map-*/` exists, read `context-map.md` inside it before planning, then the split files it links to (`known-issues.md`, `decisions.md`, `tasks.md`, `gotchas.md`). Flag conflicts before implementing changes that contradict them.
- Never commit `context-map-*/` content. It is project memory and may contain private operational notes; treat it like `.env`. The navigation layer (`agent-docs/`) is the opposite — it stays committed.
{MARKER_END}
"""


# Per-layer fragments. The project block is composed from the layers that
# actually exist (or are intended) for the project, so a memory-only project
# does not get told to read a navigation layer that isn't there.
NAV_FRAGMENT = """**Navigation (committed) — `agent-docs/`.** Read `agent-docs/MAP.md` FIRST to find which domain owns the code you're about to touch, then read that `agent-docs/domains/<name>.md` before editing. After you change entry points, public API, architecture, or domain boundaries, update the matching domain doc in the same change (or add `[skip-agent-docs]` to a commit message for a genuinely trivial change)."""

MEMORY_FRAGMENT = """**Memory (gitignored) — `context-map-{slug}/`.** Before planning or editing, read `context-map-{slug}/context-map.md` and the split files it links to (`known-issues.md`, `decisions.md`, `tasks.md`, `gotchas.md`; `architecture.md` if present). Treat `Known Issues`, `Decisions`, and the `Agent Conflict Protocol` as project memory. If a requested change conflicts with a Known Issue or Decision, explain the conflict and ask before proceeding. Update it when a significant decision is made or reversed, a known issue is discovered/fixed/accepted, or a fix prevents a future regression. Never commit `context-map-{slug}/` — the skill keeps it in `.gitignore`; if you find it staged, unstage it and verify the rule."""


def build_project_block(slug: str, layers: str) -> str:
    """Compose the managed project stanza for the requested layer(s).

    `layers` is one of `nav`, `memory`, `both`.
    """
    parts: list[str] = []
    if layers in ("both", "nav"):
        parts.append(NAV_FRAGMENT)
    if layers in ("both", "memory"):
        parts.append(MEMORY_FRAGMENT.format(slug=slug))
    body = "\n\n".join(parts)
    return (
        f"{MARKER_BEGIN}\n"
        "## Project Docs (navigation + memory)\n\n"
        "This repo's agent-facing docs live in two layers, maintained by the "
        "context-map skill. Do not put secrets, tokens, or credentials in either.\n\n"
        f"{body}\n"
        f"{MARKER_END}\n"
    )


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


def strip_legacy_block(text: str) -> tuple[str, bool]:
    """Remove a legacy memory-only stanza (old marker syntax) if present.

    Returns (cleaned_text, removed). Also drops a `## Project Context Map`
    heading immediately preceding the legacy markers, so reconcile can drop in
    the new unified block cleanly instead of leaving an orphan heading.
    """
    if LEGACY_BEGIN not in text or LEGACY_END not in text:
        return text, False
    begin = text.index(LEGACY_BEGIN)
    end = text.index(LEGACY_END, begin) + len(LEGACY_END)
    # extend end to swallow the trailing newline
    line_end = text.find("\n", end)
    end = len(text) if line_end < 0 else line_end + 1
    # extend begin backward over the legacy heading + blank lines, if adjacent
    head = text.rfind(LEGACY_HEADING, 0, begin)
    start = begin
    if head != -1 and text[head + len(LEGACY_HEADING):begin].strip() == "":
        start = text.rfind("\n", 0, head) + 1
    cleaned = text[:start] + text[end:]
    return cleaned, True


def install_or_update(path: Path, block: str) -> tuple[str, bool]:
    """Append or replace the managed block at `path`. Returns (message, changed)."""
    existing = path.read_text(encoding="utf-8") if path.exists() else ""

    # Reconcile path: collapse any legacy stanza before installing the new one.
    existing, legacy_removed = strip_legacy_block(existing)

    suffix = " (replaced legacy block)" if legacy_removed else ""

    if MARKER_BEGIN in existing:
        if MARKER_END not in existing:
            return f"begin marker found but no end marker in {path}; refusing to write", False
        begin_idx = existing.index(MARKER_BEGIN)
        end_idx = existing.index(MARKER_END, begin_idx) + len(MARKER_END)
        line_end = existing.find("\n", end_idx)
        line_end = len(existing) if line_end < 0 else line_end + 1
        line_start = existing.rfind("\n", 0, begin_idx) + 1  # 0 if not found
        old_block = existing[line_start:line_end]
        if old_block.strip() == block.strip() and not legacy_removed:
            return f"already up to date: {path}", False
        new_text = existing[:line_start] + block + existing[line_end:]
        path.write_text(new_text, encoding="utf-8")
        return f"updated managed block in {path}{suffix}", True

    path.parent.mkdir(parents=True, exist_ok=True)
    if existing and not existing.endswith("\n"):
        existing += "\n"
    sep = "\n" if existing else ""
    new_text = existing + sep + block
    path.write_text(new_text, encoding="utf-8")
    verb = "replaced legacy block with managed block" if legacy_removed else "installed managed block"
    return f"{verb} in {path}", True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scope", choices=["global", "project"], required=True)
    parser.add_argument("--project", help="Project root (required for --scope project)")
    parser.add_argument("--slug", help="Override auto-detected slug")
    parser.add_argument(
        "--layers",
        choices=["nav", "memory", "both"],
        default="both",
        help="Which doc layers the project stanza should reference (default: both)",
    )
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
        # The memory fragment needs a slug; the nav fragment does not.
        if not slug and args.layers != "nav":
            print(
                "error: --slug not given and could not auto-detect a single context-map-* folder",
                file=sys.stderr,
            )
            return 2
        path = pick_project_target(project, args.file)
        block = build_project_block(slug or "", args.layers)

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
