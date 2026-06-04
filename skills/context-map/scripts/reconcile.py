#!/usr/bin/env python3
"""Reconcile an existing split/legacy doc layout into the linked two-layer model.

Many projects already have a committed `agent-docs/` (navigation) and/or a
gitignored `context-map-<slug>/` (memory), built by older skills or by hand and
only half-linked. This script detects that state and links the two layers with
ZERO data loss.

Read-only by default — it reports the detected state and the planned changes.
With `--apply` it performs ONLY safe, additive operations:
  1. write `agent-docs/_meta/links.json` (machine-readable pairing)
  2. add a `../agent-docs/MAP.md` row to the memory `context-map.md`
     `## Linked Files` section (idempotent)
  3. add `nav_layer: agent-docs` to the memory frontmatter if absent, and bump
     `context_map_version` 2 → 3 (additive; the validator accepts both)

It NEVER regenerates `decisions.md` / `known-issues.md` / domain docs, never
deletes, never reorders. The gitignore rule and the unified CLAUDE.md stanza are
owned by `ensure_gitignore.py` / `ensure_agent_rule.py`; this script prints the
exact commands and, with `--run-hooks`, runs them.

Usage:
  python3 reconcile.py --project /path/to/project            # report only
  python3 reconcile.py --project /path/to/project --apply     # additive edits
  python3 reconcile.py --project /path --apply --run-hooks     # + gitignore & stanza

Exit codes:
  0 — reconciled (or already linked), or report produced
  1 — nothing to reconcile (no docs found) / ambiguous (multiple memory folders)
"""

from __future__ import annotations

import argparse
import datetime as _dt
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
NAV_LINK_ROW = (
    "- `../agent-docs/MAP.md` — navigation index; read first to find which "
    "domain owns the code."
)


# ---------- detection ----------

def find_memory_folders(project: Path) -> list[Path]:
    out = []
    for p in sorted(project.iterdir()):
        if p.is_dir() and p.name.startswith("context-map-"):
            main = p / "context-map.md"
            if main.exists() and "context_map_version" in main.read_text(encoding="utf-8", errors="ignore"):
                out.append(p)
    return out


def find_legacy_single_file(project: Path) -> Path | None:
    for cand in (project / "context-map.md", project / "docs" / "context-map.md"):
        if cand.exists():
            txt = cand.read_text(encoding="utf-8", errors="ignore")
            # legacy = single file NOT inside a context-map-<slug>/ folder
            if "context_map_version" not in txt or "context_map_version: 1" in txt:
                return cand
    return None


def has_nav(project: Path) -> bool:
    return (project / "agent-docs" / "MAP.md").exists()


def classify(project: Path) -> tuple[str, dict]:
    mem = find_memory_folders(project)
    nav = has_nav(project)
    legacy = find_legacy_single_file(project)
    info = {"memory_folders": mem, "nav": nav, "legacy": legacy}
    if legacy and not mem:
        return "legacy-single-file", info
    if mem and nav:
        return "both", info
    if mem and not nav:
        return "memory-only", info
    if nav and not mem:
        return "nav-only", info
    return "none", info


# ---------- frontmatter (line-based, no deps) ----------

def split_frontmatter(text: str) -> tuple[list[str], int, int] | None:
    """Return (frontmatter_lines, start_line_idx, end_line_idx) for the first
    `---`-delimited block, or None if absent."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], 0, i
    return None


def fm_get(fm_lines: list[str], key: str) -> str | None:
    for ln in fm_lines:
        if ln.strip().startswith(f"{key}:"):
            return ln.split(":", 1)[1].strip()
    return None


# ---------- linked-files section ----------

def linked_files_has_nav(text: str) -> bool:
    return "agent-docs/MAP.md" in text


def insert_nav_link_row(text: str) -> tuple[str, bool]:
    """Add the MAP.md row to the `## Linked Files` section. Idempotent.
    Returns (new_text, changed)."""
    if linked_files_has_nav(text):
        return text, False
    lines = text.splitlines()
    # find the section header
    start = None
    for i, ln in enumerate(lines):
        if ln.strip() == "## Linked Files":
            start = i
            break
    if start is None:
        return text, False  # no section to extend; caller reports this
    # find end of section (next "## " or EOF) and the last bullet within it
    end = len(lines)
    last_bullet = start
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
        if lines[j].lstrip().startswith("- "):
            last_bullet = j
    insert_at = last_bullet + 1
    lines.insert(insert_at, NAV_LINK_ROW)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), True


def add_nav_layer_frontmatter(text: str) -> tuple[str, bool, list[str]]:
    """Add `nav_layer: agent-docs` if absent and bump version 2->3.
    Returns (new_text, changed, notes)."""
    fm = split_frontmatter(text)
    if fm is None:
        return text, False, ["no frontmatter found — skipped"]
    fm_lines, _start, end_idx = fm
    lines = text.splitlines()
    notes: list[str] = []
    changed = False

    # bump version 2 -> 3
    for i in range(1, end_idx):
        if lines[i].strip().startswith("context_map_version:"):
            cur = lines[i].split(":", 1)[1].strip()
            if cur == "2":
                lines[i] = "context_map_version: 3"
                notes.append("context_map_version: 2 -> 3")
                changed = True
            break

    # add nav_layer if absent
    if fm_get(fm_lines, "nav_layer") is None:
        # insert before last_updated if present, else just before closing ---
        insert_idx = end_idx
        for i in range(1, end_idx):
            if lines[i].strip().startswith("last_updated:"):
                insert_idx = i
                break
        lines.insert(insert_idx, "nav_layer: agent-docs")
        notes.append("added nav_layer: agent-docs")
        changed = True

    if not changed:
        return text, False, ["frontmatter already has nav_layer (no change)"]
    return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), True, notes


# ---------- links.json ----------

def write_links_json(project: Path, slug: str, apply: bool) -> tuple[str, bool]:
    meta = project / "agent-docs" / "_meta"
    target = meta / "links.json"
    today = _dt.date.today().isoformat()
    content = (
        "{\n"
        '  "links_version": 1,\n'
        f'  "memory_folder": "context-map-{slug}",\n'
        f'  "memory_main": "../context-map-{slug}/context-map.md",\n'
        f'  "verified": "{today}"\n'
        "}\n"
    )
    if target.exists() and target.read_text(encoding="utf-8").strip() == content.strip():
        return f"links.json already current: {target}", False
    if apply:
        meta.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"wrote {target}", True
    return f"would write {target}", True


# ---------- main ----------

def run(cmd: list[str]) -> None:
    print(f"  $ {' '.join(cmd)}")
    subprocess.run(cmd, check=False)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True, help="Project root")
    ap.add_argument("--apply", action="store_true", help="Perform additive edits (default: report only)")
    ap.add_argument("--run-hooks", action="store_true", help="Also run ensure_gitignore.py / ensure_agent_rule.py")
    args = ap.parse_args()

    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        print(f"error: {project} is not a directory", file=sys.stderr)
        return 1

    state, info = classify(project)
    print(f"[reconcile] project: {project}")
    print(f"[reconcile] state:   {state}")

    if state == "none":
        print("  Nothing to reconcile — no agent-docs/ or context-map-*/ found.")
        print("  Run the context-map skill `generate` to create the layers.")
        return 1

    if state == "legacy-single-file":
        print(f"  Legacy single-file map at: {info['legacy']}")
        print("  Run `migrate-legacy` (scripts/migrate_legacy.py) first, then reconcile.")
        return 0

    mem_folders: list[Path] = info["memory_folders"]
    if len(mem_folders) > 1:
        print(f"  Ambiguous: {len(mem_folders)} memory folders found: "
              f"{[p.name for p in mem_folders]}. Resolve before reconciling.", file=sys.stderr)
        return 1

    verb = "APPLY" if args.apply else "REPORT"
    print(f"[reconcile] mode:    {verb}")
    print()

    # nav-only: no memory layer to link; report and suggest generate --layer memory
    if state == "nav-only":
        print("  Navigation layer present, memory layer missing.")
        print("  Suggested: context-map `generate --layer memory`, then reconcile.")
        return 0

    mem = mem_folders[0]
    slug = mem.name.removeprefix("context-map-")
    print(f"  memory folder: {mem.name}  (slug: {slug})")
    print(f"  navigation:    {'present' if info['nav'] else 'MISSING'}")
    print()

    # memory-only: nothing to cross-link to yet
    if state == "memory-only":
        print("  Memory layer present, navigation layer missing.")
        print("  Suggested: context-map `decompose` then `generate --layer nav`, then reconcile.")
        print("  Protection check below still applies.")
        if args.run_hooks:
            _run_protection(project, slug, args.apply)
        return 0

    # state == "both": the main reconcile path
    changes: list[str] = []

    # 1. links.json
    msg, _ = write_links_json(project, slug, args.apply)
    changes.append(msg)

    # 2. linked-files row in memory context-map.md
    main_md = mem / "context-map.md"
    text = main_md.read_text(encoding="utf-8")
    if linked_files_has_nav(text):
        changes.append(f"linked-files row already present in {main_md.name}")
    else:
        new_text, changed = insert_nav_link_row(text)
        if not changed:
            changes.append(f"WARN: no `## Linked Files` section in {main_md.name} — "
                           "add one or run `update --layer memory`")
        elif args.apply:
            main_md.write_text(new_text, encoding="utf-8")
            text = new_text
            changes.append(f"added MAP.md row to {main_md.name} ## Linked Files")
        else:
            changes.append(f"would add MAP.md row to {main_md.name} ## Linked Files")

    # 3. nav_layer frontmatter (+ version bump)
    new_text, changed, notes = add_nav_layer_frontmatter(text)
    if changed and args.apply:
        main_md.write_text(new_text, encoding="utf-8")
        changes.append(f"frontmatter: {', '.join(notes)}")
    elif changed:
        changes.append(f"would update frontmatter: {', '.join(notes)}")
    else:
        changes.append(f"frontmatter: {notes[0]}")

    # 4. MAP.md back-link (report; the skill populates it via templates)
    map_md = project / "agent-docs" / "MAP.md"
    if map_md.exists() and "context-map-" not in map_md.read_text(encoding="utf-8"):
        changes.append("WARN: agent-docs/MAP.md has no `## Project memory` link to "
                       f"../{mem.name}/ — add it (see references/map-template.md)")

    print("  Planned changes:" if not args.apply else "  Applied changes:")
    for c in changes:
        print(f"    - {c}")
    print()

    _run_protection(project, slug, args.apply, run_now=args.run_hooks)

    if not args.apply:
        print("\n  Re-run with --apply to perform the additive edits.")
    return 0


def _tracked_memory(project: Path) -> list[str]:
    """Already-tracked context-map-*/ folders — a .gitignore rule won't untrack them."""
    if not (project / ".git").exists():
        return []
    folders = set()
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


def _run_protection(project: Path, slug: str, apply: bool, run_now: bool = False) -> None:
    """Print (and optionally run) the gitignore + unified-stanza commands."""
    gi = SCRIPT_DIR / "ensure_gitignore.py"
    ar = SCRIPT_DIR / "ensure_agent_rule.py"
    tracked = _tracked_memory(project)
    if tracked:
        joined = " ".join(tracked)
        print(f"  ⚠ memory already tracked in git: {joined}")
        print("    A .gitignore rule will NOT untrack it. Stop tracking (files stay on disk):")
        print(f"      git -C {project} rm -r --cached {joined}  &&  git commit -m 'stop tracking context-map memory'")
    print("  Protection (memory gitignored, navigation committed) + unified stanza:")
    cmds = [
        [sys.executable, str(gi), "--scope", "project", "--project", str(project)],
        [sys.executable, str(ar), "--scope", "project", "--project", str(project),
         "--slug", slug, "--layers", "both"],
    ]
    if run_now and apply:
        for c in cmds:
            run(c)
    else:
        for c in cmds:
            print(f"    $ {' '.join(c)}")
        if run_now and not apply:
            print("    (skipped — pass --apply with --run-hooks to run)")


if __name__ == "__main__":
    sys.exit(main())
