#!/usr/bin/env python3
"""Collect context-map folders into a dashboard-ready JSON index."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from discover_projects import (  # noqa: E402
    CONTEXT_MAP_FOLDER_PATTERN,
    LEGACY_CONTEXT_MAP_NAMES,
    discover_roots,
    expand,
    load_config,
)


HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
BULLET_RE = re.compile(r"^[-*]\s+(.+?):\s*(.*)$")


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"", "null", "None", "~"}:
        return ""
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [item.strip().strip("'\"") for item in inner.split(",")]
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    return value.strip("'\"")


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end].strip()
    body = text[end + 4 :].lstrip("\n")
    data: dict[str, Any] = {}
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = parse_scalar(value)
    return data, body


def section_text(body: str, heading: str) -> str:
    matches = list(HEADING_RE.finditer(body))
    for index, match in enumerate(matches):
        if match.group(1).strip().lower() == heading.lower():
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
            return body[start:end].strip()
    return ""


def split_table_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip().replace("\\|", "|") for cell in line.split("|")]


def parse_first_table(text: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index in range(len(lines) - 1):
        if not lines[index].startswith("|") or not lines[index + 1].startswith("|"):
            continue
        headers = split_table_row(lines[index])
        separator = split_table_row(lines[index + 1])
        if not all(set(cell.replace(" ", "")) <= {"-", ":"} and "-" in cell for cell in separator):
            continue
        rows: list[dict[str, str]] = []
        for line in lines[index + 2 :]:
            if not line.startswith("|"):
                break
            cells = split_table_row(line)
            row = {headers[i]: cells[i] if i < len(cells) else "" for i in range(len(headers))}
            rows.append(row)
        return rows
    return []


def parse_current_phase(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for line in text.splitlines():
        match = BULLET_RE.match(line.strip())
        if not match:
            continue
        key = match.group(1).strip().lower().replace(" ", "_")
        value = match.group(2).strip()
        if "," in value and key in {"recently_changed", "recently_changed_dirs", "unstable_areas"}:
            out[key] = [item.strip(" `") for item in value.split(",") if item.strip()]
        else:
            out[key] = value
    return out


def normalize_project_id(folder: Path, frontmatter: dict[str, Any]) -> str:
    raw = str(frontmatter.get("project_id") or frontmatter.get("project_slug") or folder.parent.name)
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", raw.strip().lower()).strip("-")
    return slug or "unknown-project"


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


_TABLE_HEADER_RE = re.compile(r"^\|(.+)\|\s*$")


def _has_table_header(section: str) -> bool:
    lines = [line.strip() for line in section.splitlines()]
    for index in range(len(lines) - 1):
        if not _TABLE_HEADER_RE.match(lines[index]) or not _TABLE_HEADER_RE.match(lines[index + 1]):
            continue
        separator_cells = [cell.strip() for cell in lines[index + 1].strip("|").split("|")]
        if all(set(cell.replace(" ", "")) <= {"-", ":"} and "-" in cell for cell in separator_cells):
            return True
    return False


def parse_split_file(folder: Path, filename: str, heading: str) -> tuple[list[dict[str, str]], str | None]:
    path = folder / filename
    if not path.exists() or not path.is_file():
        return [], None
    text = _safe_read(path)
    section = section_text(text, heading)
    if not section:
        return [], f"{filename}: missing '## {heading}' section"
    rows = parse_first_table(section)
    if not rows and not _has_table_header(section):
        return [], f"{filename}: no canonical table under '## {heading}'"
    return rows, None


def parse_context_map_folder(folder: Path, project_path: Path | None = None) -> dict[str, Any]:
    main_file = folder / "context-map.md"
    warnings: list[str] = []

    if not main_file.exists():
        return {
            "context_map_folder": str(folder),
            "context_map_main": "",
            "parse_status": "error",
            "parse_warnings": ["context-map.md missing in folder"],
            "known_issues": [],
            "decisions": [],
            "tasks": [],
            "gotchas": [],
            "confidence_notes": [],
            "current_phase": {},
        }

    text = _safe_read(main_file)
    frontmatter, body = parse_frontmatter(text)

    if int(frontmatter.get("context_map_version") or 0) != 2:
        warnings.append("context_map_version != 2")

    known_issues, ki_warn = parse_split_file(folder, "known-issues.md", "Known Issues")
    if ki_warn:
        warnings.append(ki_warn)
    decisions, dec_warn = parse_split_file(folder, "decisions.md", "Decisions")
    if dec_warn:
        warnings.append(dec_warn)
    tasks, task_warn = parse_split_file(folder, "tasks.md", "Tasks / Next Work")
    if task_warn:
        warnings.append(task_warn)
    gotchas, got_warn = parse_split_file(folder, "gotchas.md", "Gotchas")
    if got_warn:
        warnings.append(got_warn)

    confidence_notes = parse_first_table(section_text(body, "Confidence Notes"))
    current_phase = parse_current_phase(section_text(body, "Current Phase"))

    project_root = Path(str(frontmatter.get("repo_path") or project_path or folder.parent)).expanduser()
    stack = frontmatter.get("primary_stack", [])
    if isinstance(stack, str):
        stack = [stack] if stack else []

    if warnings:
        parse_status = "partial"
    else:
        parse_status = "ok"

    return {
        "project_id": normalize_project_id(folder, frontmatter),
        "project_slug": str(frontmatter.get("project_slug") or frontmatter.get("project_id") or folder.name.removeprefix("context-map-")),
        "name": frontmatter.get("name") or project_root.name,
        "path": str(project_root),
        "context_map_folder": str(folder),
        "context_map_main": str(main_file),
        "context_map_version": frontmatter.get("context_map_version") or None,
        "repo_url": frontmatter.get("repo_url", ""),
        "visibility": frontmatter.get("visibility", "unknown"),
        "status": frontmatter.get("status", "unknown"),
        "scale": frontmatter.get("scale", ""),
        "stack": stack,
        "last_updated": frontmatter.get("last_updated", ""),
        "last_verified_vs_code": frontmatter.get("last_verified_vs_code", ""),
        "generator": frontmatter.get("generator", ""),
        "parse_status": parse_status,
        "parse_warnings": warnings,
        "known_issues": known_issues,
        "decisions": decisions,
        "tasks": tasks,
        "gotchas": gotchas,
        "confidence_notes": confidence_notes,
        "current_phase": current_phase,
    }


def parse_legacy_single_file(path: Path, project_path: Path | None = None) -> dict[str, Any]:
    text = _safe_read(path)
    frontmatter, body = parse_frontmatter(text)
    project_root = Path(str(frontmatter.get("repo_path") or project_path or path.parent)).expanduser()
    stack = frontmatter.get("primary_stack", [])
    if isinstance(stack, str):
        stack = [stack] if stack else []
    return {
        "project_id": normalize_project_id(path, frontmatter),
        "project_slug": str(frontmatter.get("project_slug") or frontmatter.get("project_id") or project_root.name),
        "name": frontmatter.get("name") or project_root.name,
        "path": str(project_root),
        "context_map_folder": "",
        "context_map_main": str(path),
        "context_map_version": frontmatter.get("context_map_version") or 1,
        "repo_url": frontmatter.get("repo_url", ""),
        "visibility": frontmatter.get("visibility", "unknown"),
        "status": frontmatter.get("status", "unknown"),
        "scale": frontmatter.get("scale", ""),
        "stack": stack,
        "last_updated": frontmatter.get("last_updated", ""),
        "last_verified_vs_code": "",
        "generator": frontmatter.get("generator", ""),
        "parse_status": "legacy",
        "parse_warnings": ["single-file legacy map; run migrate-legacy"],
        "known_issues": parse_first_table(section_text(body, "Known Issues")),
        "decisions": parse_first_table(section_text(body, "Decisions")),
        "tasks": parse_first_table(section_text(body, "Tasks / Next Work")),
        "gotchas": parse_first_table(section_text(body, "Gotchas")),
        "confidence_notes": parse_first_table(section_text(body, "Confidence Notes")),
        "current_phase": parse_current_phase(section_text(body, "Current Phase")),
    }


def missing_row(project: dict[str, Any]) -> dict[str, Any]:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", project["name"].lower()).strip("-") or "unknown-project"
    return {
        "project_id": slug,
        "project_slug": slug,
        "name": project["name"],
        "path": project["path"],
        "context_map_folder": "",
        "context_map_main": "",
        "context_map_version": None,
        "repo_url": project.get("git", {}).get("remote", "") or "",
        "visibility": "unknown",
        "status": "unknown",
        "scale": project.get("scale", ""),
        "stack": project.get("stacks", []),
        "last_updated": "",
        "last_verified_vs_code": "",
        "generator": "",
        "parse_status": "missing",
        "parse_warnings": [],
        "known_issues": [],
        "decisions": [],
        "tasks": [],
        "gotchas": [],
        "confidence_notes": [],
        "current_phase": {},
    }


def collect(projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for project in projects:
        status = project.get("context_map_status")
        project_path = Path(project["path"])

        if status == "v2" and project.get("context_map_folder"):
            parsed = parse_context_map_folder(Path(project["context_map_folder"]), project_path)
        elif status == "invalid" and project.get("context_map_folder"):
            parsed = parse_context_map_folder(Path(project["context_map_folder"]), project_path)
            parsed["parse_status"] = "partial"
            parsed["parse_warnings"].insert(0, "discovery flagged folder as invalid")
        elif status == "legacy" and project.get("legacy_context_map"):
            parsed = parse_legacy_single_file(Path(project["legacy_context_map"]), project_path)
        else:
            parsed = missing_row(project)

        if not parsed.get("repo_url"):
            parsed["repo_url"] = project.get("git", {}).get("remote", "") or ""
        if not parsed.get("scale"):
            parsed["scale"] = project.get("scale", "")
        if not parsed.get("stack"):
            parsed["stack"] = project.get("stacks", [])

        rows.append(parsed)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect context maps into a dashboard-ready index.")
    parser.add_argument("roots", nargs="*", help="Project roots to discover")
    parser.add_argument("--config", help="Path to ~/.context-map/config.json")
    parser.add_argument("--output", help="Output index path; defaults to config dashboard_index_path or ~/.context-map/index.json")
    parser.add_argument("--format", choices=["json", "summary"], default="json")
    parser.add_argument("--max-depth", type=int, default=4)
    args = parser.parse_args()

    config = load_config(args.config)
    configured_roots = [expand(path) for path in config.get("project_roots", []) if isinstance(path, str)]
    cli_roots = [expand(path) for path in args.roots]
    roots = cli_roots or configured_roots or [Path.cwd().resolve()]

    folder_pattern = config.get("context_map_folder_pattern", CONTEXT_MAP_FOLDER_PATTERN)
    if not isinstance(folder_pattern, str) or not folder_pattern:
        folder_pattern = CONTEXT_MAP_FOLDER_PATTERN

    legacy_names = config.get("legacy_context_map_names") or config.get("context_map_names") or LEGACY_CONTEXT_MAP_NAMES
    if not isinstance(legacy_names, list):
        legacy_names = LEGACY_CONTEXT_MAP_NAMES

    discovered = discover_roots(roots, args.max_depth, legacy_names, folder_pattern)
    projects = collect(discovered)
    payload = {
        "version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "roots": [str(root) for root in roots],
        "projects": projects,
    }

    output = args.output or config.get("dashboard_index_path") or "~/.context-map/index.json"
    output_path = Path(str(output)).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.format == "summary":
        ok = sum(1 for project in projects if project["parse_status"] == "ok")
        partial = sum(1 for project in projects if project["parse_status"] == "partial")
        legacy = sum(1 for project in projects if project["parse_status"] == "legacy")
        missing = sum(1 for project in projects if project["parse_status"] == "missing")
        error = sum(1 for project in projects if project["parse_status"] == "error")
        print(f"Wrote {output_path}")
        print(f"Projects: {len(projects)}; ok={ok}; partial={partial}; legacy={legacy}; missing={missing}; error={error}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
