#!/usr/bin/env python3
"""Migrate a legacy single-file context-map.md into the new context-map-<slug>/ folder layout.

Usage:
    python3 scripts/migrate_legacy.py /path/to/project
    python3 scripts/migrate_legacy.py /path/to/project --slug custom-slug --dry-run

The script reads an existing `context-map.md` or `docs/context-map.md`, extracts known
sections (Known Issues, Decisions, Tasks / Next Work, Gotchas, Confidence Notes,
Current Phase, Tech Stack, plus free-form body), and writes split files into the
target folder. It does not delete the legacy file; it renames it to `.bak`.

The output is intended as a starting point — run `validate_context_map.py` afterwards
and expect to fill in missing fields manually, especially new frontmatter fields like
`project_slug`, `last_verified_vs_code`, and `generator`.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from collect_context_maps import parse_first_table, parse_frontmatter, section_text  # noqa: E402
from discover_projects import LEGACY_CONTEXT_MAP_NAMES  # noqa: E402


TODAY = date.today().isoformat()


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    lowered = normalized.lower()
    replaced = re.sub(r"[^a-z0-9]+", "-", lowered)
    return replaced.strip("-") or "project"


def find_legacy(project: Path) -> Path | None:
    for name in LEGACY_CONTEXT_MAP_NAMES:
        candidate = project / name
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _render_table(columns: list[str], rows: list[dict[str, str]]) -> str:
    header = "| " + " | ".join(columns) + " |"
    separator = "|" + "|".join("------" for _ in columns) + "|"
    lines = [header, separator]
    for row in rows:
        cells = [row.get(col, "").replace("|", "\\|") for col in columns]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _empty_table(columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    separator = "|" + "|".join("------" for _ in columns) + "|"
    return header + "\n" + separator + "\n"


def _normalize_rows(rows: list[dict[str, str]], target_columns: list[str], aliases: dict[str, list[str]]) -> list[dict[str, str]]:
    """Reshape parsed rows into target columns, preserving values via aliases."""
    out: list[dict[str, str]] = []
    for row in rows:
        new_row: dict[str, str] = {}
        for column in target_columns:
            if column in row:
                new_row[column] = row[column]
                continue
            alias_hit = ""
            for alias in aliases.get(column, []):
                if alias in row and row[alias]:
                    alias_hit = row[alias]
                    break
            new_row[column] = alias_hit
        out.append(new_row)
    return out


def build_known_issues(rows: list[dict[str, str]]) -> str:
    target = ["ID", "Area", "Priority", "Symptom", "Cause", "Status", "Agent-Ready", "Rule"]
    aliases = {
        "Cause": ["Reason", "Root Cause"],
        "Rule": ["Workaround / Rule", "Workaround", "Fix"],
        "Agent-Ready": ["AgentReady"],
    }
    normalized = _normalize_rows(rows, target, aliases)
    body = "# Known Issues\n\n## Known Issues\n\n"
    if not normalized:
        body += _empty_table(target)
        return body
    body += _render_table(target, normalized) + "\n"
    return body


def build_decisions(rows: list[dict[str, str]]) -> str:
    target = ["ID", "Date", "Decision", "Rationale", "Consequence", "Do Not Repeat"]
    aliases = {
        "Date": ["Date / Session", "Session", "When"],
    }
    normalized = _normalize_rows(rows, target, aliases)
    body = "# Decisions\n\n## Decisions\n\n"
    if not normalized:
        body += _empty_table(target)
        return body
    body += _render_table(target, normalized) + "\n"
    return body


def build_tasks(rows: list[dict[str, str]]) -> str:
    target = ["ID", "Area", "Type", "Task", "Status", "Agent-Ready", "Validation"]
    aliases: dict[str, list[str]] = {}
    normalized = _normalize_rows(rows, target, aliases)
    body = "# Tasks / Next Work\n\n## Tasks / Next Work\n\n"
    if not normalized:
        body += _empty_table(target)
        return body
    body += _render_table(target, normalized) + "\n"
    return body


def build_gotchas(rows: list[dict[str, str]]) -> str:
    target = ["ID", "Category", "Description", "Trigger", "Guardrail"]
    aliases: dict[str, list[str]] = {
        "Description": ["Gotcha", "Note"],
    }
    normalized = _normalize_rows(rows, target, aliases)
    body = "# Gotchas\n\n## Gotchas\n\n"
    if not normalized:
        body += _empty_table(target)
        return body
    # If the legacy file had no IDs, auto-number.
    for idx, row in enumerate(normalized, start=1):
        if not re.match(r"^G-\d{3,}$", row.get("ID", "")):
            row["ID"] = f"G-{idx:03d}"
        if not row.get("Category"):
            row["Category"] = "other"
    body += _render_table(target, normalized) + "\n"
    return body


def build_main(
    legacy_frontmatter: dict[str, Any],
    legacy_body: str,
    project_path: Path,
    slug: str,
    project_name: str,
    scale: str,
) -> str:
    confidence_text = section_text(legacy_body, "Confidence Notes")
    current_phase_text = section_text(legacy_body, "Current Phase")
    tech_stack_text = section_text(legacy_body, "Tech Stack")
    project_identity_text = section_text(legacy_body, "Project Identity") or section_text(legacy_body, "What This Is")
    directory_structure_text = section_text(legacy_body, "Directory Structure") or section_text(legacy_body, "File Map")
    read_first_text = section_text(legacy_body, "Read First By Task Type") or section_text(legacy_body, "Read First")
    architecture_text = section_text(legacy_body, "Architecture Overview") or section_text(legacy_body, "Architecture")
    update_protocol_text = section_text(legacy_body, "Update Protocol") or section_text(legacy_body, "Keep This Updated")

    stack = legacy_frontmatter.get("primary_stack") or []
    if isinstance(stack, str):
        stack = [stack] if stack else []

    frontmatter_lines = [
        "---",
        "context_map_version: 3",
        f"project_id: {slug}",
        f"project_slug: {slug}",
        f'name: "{project_name}"',
        f"repo_path: {project_path}",
        f"repo_url: {legacy_frontmatter.get('repo_url') or 'null'}",
        f"visibility: {legacy_frontmatter.get('visibility') or 'unknown'}",
        f"status: {legacy_frontmatter.get('status') or 'active'}",
        f"scale: {scale}",
        f"primary_stack: [{', '.join(stack) if stack else ''}]",
        "nav_layer: null",
        f"last_updated: {TODAY}",
        f"last_verified_vs_code: {TODAY}",
        "generator: context-map-skill/0.3",
        "---",
    ]

    parts: list[str] = ["\n".join(frontmatter_lines), "", f"# Context Map: {project_name}", ""]

    parts.append("## Project Identity")
    parts.append("")
    parts.append(project_identity_text or "Migrated from legacy single-file context map. Fill in.")
    parts.append("")

    parts.append("## Current Phase")
    parts.append("")
    parts.append(current_phase_text or "- Active focus: migrated, needs review\n- Last verified vs code: " + TODAY)
    parts.append("")

    parts.append("## Tech Stack")
    parts.append("")
    tech_target = ["Layer", "Tech", "Version", "Notes"]
    tech_rows = parse_first_table(tech_stack_text) if tech_stack_text else []
    if tech_rows:
        tech_aliases = {"Layer": ["Area"], "Tech": ["Technology", "Stack"]}
        normalized_tech = _normalize_rows(tech_rows, tech_target, tech_aliases)
        parts.append(_render_table(tech_target, normalized_tech))
    else:
        parts.append(_empty_table(tech_target).rstrip())
    parts.append("")

    parts.append("## Directory Structure")
    parts.append("")
    parts.append(directory_structure_text or "```text\n(fill in)\n```")
    parts.append("")

    parts.append("## Read First By Task Type")
    parts.append("")
    rf_target = ["Task Type", "Start Here", "Then Check", "Validate With"]
    rf_rows = parse_first_table(read_first_text) if read_first_text else []
    if rf_rows:
        rf_aliases = {"Task Type": ["Task"], "Start Here": ["Start"], "Validate With": ["Validation"]}
        normalized_rf = _normalize_rows(rf_rows, rf_target, rf_aliases)
        parts.append(_render_table(rf_target, normalized_rf))
    else:
        parts.append(_empty_table(rf_target).rstrip())
    parts.append("")

    if scale in {"M", "L", "XL"}:
        parts.append("## Architecture Overview")
        parts.append("")
        parts.append(architecture_text or "See `architecture.md`.")
        parts.append("")

    parts.append("## Linked Files")
    parts.append("")
    parts.append(
        "- [`known-issues.md`](known-issues.md)\n"
        "- [`decisions.md`](decisions.md)\n"
        "- [`tasks.md`](tasks.md)\n"
        "- [`gotchas.md`](gotchas.md)"
        + ("\n- [`architecture.md`](architecture.md)" if scale in {"M", "L", "XL"} else "")
    )
    parts.append("")

    parts.append("## Agent Conflict Protocol")
    parts.append("")
    parts.append(
        "Before editing code, read `known-issues.md` and `decisions.md`. If the requested change "
        "conflicts with a recorded decision or known issue, explain the conflict and ask the user "
        "before proceeding."
    )
    parts.append("")

    if scale in {"M", "L", "XL"}:
        parts.append("## Validation Checklist")
        parts.append("")
        parts.append(_empty_table(["Change Type", "Required Check"]).rstrip())
        parts.append("")

    parts.append("## Confidence Notes")
    parts.append("")
    if confidence_text and parse_first_table(confidence_text):
        parts.append(confidence_text)
    else:
        body = _empty_table(["Claim", "Source", "Confidence", "Evidence", "Needs Human?"])
        body += (
            "| legacy migration | legacy context-map.md | inferred | "
            "automatic conversion, sections may be incomplete | yes |\n"
        )
        parts.append(body.rstrip())
    parts.append("")

    parts.append("## Update Protocol")
    parts.append("")
    parts.append(update_protocol_text or "Update this folder when entry points, architecture, decisions, or known issues change.")
    parts.append("")

    return "\n".join(parts)


def migrate(project_path: Path, slug: str | None, dry_run: bool) -> tuple[Path, list[str]]:
    legacy = find_legacy(project_path)
    if not legacy:
        raise SystemExit(f"No legacy context-map.md found in {project_path}")

    text = legacy.read_text(encoding="utf-8", errors="ignore")
    frontmatter, body = parse_frontmatter(text)

    project_name_raw = frontmatter.get("name") or project_path.name
    final_slug = slug or slugify(str(frontmatter.get("project_slug") or frontmatter.get("project_id") or project_path.name))
    folder_name = f"context-map-{final_slug}"
    target_folder = project_path / folder_name
    scale = frontmatter.get("scale") or "M"

    known_issues = parse_first_table(section_text(body, "Known Issues"))
    decisions = parse_first_table(section_text(body, "Decisions"))
    tasks = parse_first_table(section_text(body, "Tasks / Next Work"))
    gotchas_rows = parse_first_table(section_text(body, "Gotchas"))

    file_contents: dict[str, str] = {
        "context-map.md": build_main(frontmatter, body, project_path, final_slug, project_name_raw, scale),
        "known-issues.md": build_known_issues(known_issues),
        "decisions.md": build_decisions(decisions),
        "tasks.md": build_tasks(tasks),
        "gotchas.md": build_gotchas(gotchas_rows),
    }
    if scale in {"M", "L", "XL"}:
        architecture_text = section_text(body, "Architecture") or section_text(body, "Architecture Overview") or ""
        file_contents["architecture.md"] = "# Architecture\n\n" + (architecture_text or "Fill in flows, data model, API surface, deployment shape.") + "\n"

    actions: list[str] = []

    if dry_run:
        actions.append(f"[dry-run] would create folder {target_folder}")
        for name, content in file_contents.items():
            actions.append(f"[dry-run] would write {name} ({len(content)} chars)")
        actions.append(f"[dry-run] would rename legacy file to {legacy}.bak")
        return target_folder, actions

    if target_folder.exists():
        raise SystemExit(f"Target folder already exists: {target_folder}")
    target_folder.mkdir(parents=True, exist_ok=False)

    for name, content in file_contents.items():
        path = target_folder / name
        path.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")
        actions.append(f"wrote {path}")

    backup = legacy.with_suffix(legacy.suffix + ".bak")
    shutil.move(str(legacy), str(backup))
    actions.append(f"renamed legacy {legacy} -> {backup}")

    return target_folder, actions


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate a legacy context-map.md into the new folder layout.")
    parser.add_argument("project", help="Project root path")
    parser.add_argument("--slug", help="Override slug (default derived from project name)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would happen without writing")
    args = parser.parse_args()

    project_path = Path(args.project).expanduser().resolve()
    if not project_path.exists() or not project_path.is_dir():
        raise SystemExit(f"Project path is not a directory: {project_path}")

    target, actions = migrate(project_path, args.slug, args.dry_run)
    for action in actions:
        print(action)
    print(f"\nTarget folder: {target}")
    if not args.dry_run:
        print("Next step: run `python3 scripts/validate_context_map.py <target>`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
