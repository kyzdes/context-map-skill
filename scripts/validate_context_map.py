#!/usr/bin/env python3
"""Validate a context-map-<slug>/ folder against references/schema.md.

Exit codes:
    0 — all required checks pass
    1 — errors found
    2 — warnings only (only with --warnings-as-errors disabled; still exits 0)
    3 — usage error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from collect_context_maps import (  # noqa: E402
    parse_first_table,
    parse_frontmatter,
    section_text,
)


# ---- Schema ---------------------------------------------------------------

REQUIRED_FRONTMATTER: dict[str, dict[str, Any]] = {
    "context_map_version": {"type": "int", "equals": 2},
    "project_id": {"type": "slug"},
    "project_slug": {"type": "slug"},
    "name": {"type": "str"},
    "repo_path": {"type": "str"},
    "repo_url": {"type": "maybe_str"},
    "visibility": {"type": "enum", "enum": ["private", "public", "unknown"]},
    "status": {"type": "enum", "enum": ["active", "paused", "archived", "unknown"]},
    "scale": {"type": "enum", "enum": ["XS", "S", "M", "L", "XL"]},
    "primary_stack": {"type": "list"},
    "last_updated": {"type": "date"},
    "last_verified_vs_code": {"type": "date"},
    "generator": {"type": "str"},
}

REQUIRED_SECTIONS_BY_SCALE: dict[str, list[str]] = {
    "XS": [
        "Project Identity",
        "Current Phase",
        "Tech Stack",
        "Directory Structure",
        "Confidence Notes",
        "Update Protocol",
    ],
    "S": [
        "Project Identity",
        "Current Phase",
        "Tech Stack",
        "Directory Structure",
        "Read First By Task Type",
        "Linked Files",
        "Confidence Notes",
        "Agent Conflict Protocol",
        "Update Protocol",
    ],
    "M": [
        "Project Identity",
        "Current Phase",
        "Tech Stack",
        "Directory Structure",
        "Read First By Task Type",
        "Architecture Overview",
        "Linked Files",
        "Confidence Notes",
        "Agent Conflict Protocol",
        "Validation Checklist",
        "Update Protocol",
    ],
}
REQUIRED_SECTIONS_BY_SCALE["L"] = REQUIRED_SECTIONS_BY_SCALE["M"]
REQUIRED_SECTIONS_BY_SCALE["XL"] = REQUIRED_SECTIONS_BY_SCALE["M"]


SPLIT_FILES_BY_SCALE: dict[str, list[str]] = {
    "XS": [],
    "S": ["known-issues.md", "decisions.md", "tasks.md", "gotchas.md"],
    "M": ["known-issues.md", "decisions.md", "tasks.md", "gotchas.md", "architecture.md"],
    "L": ["known-issues.md", "decisions.md", "tasks.md", "gotchas.md", "architecture.md"],
    "XL": ["known-issues.md", "decisions.md", "tasks.md", "gotchas.md", "architecture.md"],
}


SPLIT_SPEC: dict[str, dict[str, Any]] = {
    "known-issues.md": {
        "heading": "Known Issues",
        "columns": ["ID", "Area", "Priority", "Symptom", "Cause", "Status", "Agent-Ready", "Rule"],
        "id_prefix": "KI",
        "enums": {
            "Priority": ["critical", "high", "medium", "low"],
            "Status": ["open", "partial", "fixed", "wontfix", "watch"],
            "Agent-Ready": ["yes", "no", "needs-human"],
        },
    },
    "decisions.md": {
        "heading": "Decisions",
        "columns": ["ID", "Date", "Decision", "Rationale", "Consequence", "Do Not Repeat"],
        "id_prefix": "D",
        "enums": {},
        "date_columns": ["Date"],
    },
    "tasks.md": {
        "heading": "Tasks / Next Work",
        "columns": ["ID", "Area", "Type", "Task", "Status", "Agent-Ready", "Validation"],
        "id_prefix": "T",
        "enums": {
            "Type": ["feature", "fix", "refactor", "docs", "ops", "research"],
            "Status": ["planned", "ready", "blocked", "in_progress", "done", "wontfix"],
            "Agent-Ready": ["yes", "no", "needs-human"],
        },
    },
    "gotchas.md": {
        "heading": "Gotchas",
        "columns": ["ID", "Category", "Description", "Trigger", "Guardrail"],
        "id_prefix": "G",
        "enums": {
            "Category": ["runtime", "api", "deploy", "ui", "data", "agent", "other"],
        },
    },
}


TECH_STACK_COLUMNS = ["Layer", "Tech", "Version", "Notes"]
READ_FIRST_COLUMNS = ["Task Type", "Start Here", "Then Check", "Validate With"]
CONFIDENCE_COLUMNS = ["Claim", "Source", "Confidence", "Evidence", "Needs Human?"]
CONFIDENCE_ENUM = ["verified", "inferred", "stale", "conflicting", "duplicate"]
NEEDS_HUMAN_ENUM = ["yes", "no"]


SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ID_RE_TEMPLATE = r"^{prefix}-\d{{3,}}$"
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_table_header(text: str) -> list[str] | None:
    """Return the column list from the first markdown table header, or None."""
    lines = [line.strip() for line in text.splitlines()]
    for index in range(len(lines) - 1):
        if not lines[index].startswith("|") or not lines[index + 1].startswith("|"):
            continue
        header = [cell.strip() for cell in lines[index].strip("|").split("|")]
        separator_cells = [cell.strip() for cell in lines[index + 1].strip("|").split("|")]
        if not all(set(cell.replace(" ", "")) <= {"-", ":"} and "-" in cell for cell in separator_cells):
            continue
        return header
    return None


# ---- Result containers ----------------------------------------------------


class Report:
    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "folder": str(self.folder),
            "errors": self.errors,
            "warnings": self.warnings,
            "status": "ok" if self.ok() else "fail",
        }


# ---- Helpers --------------------------------------------------------------


def _parse_iso_date(value: str) -> date | None:
    if not isinstance(value, str) or not ISO_DATE_RE.match(value):
        return None
    try:
        y, m, d = value.split("-")
        return date(int(y), int(m), int(d))
    except ValueError:
        return None


def _validate_frontmatter(folder: Path, frontmatter: dict[str, Any], report: Report) -> str | None:
    """Return declared scale if parseable, else None."""
    for field, spec in REQUIRED_FRONTMATTER.items():
        if field not in frontmatter:
            report.err(f"frontmatter: missing required field '{field}'")
            continue
        value = frontmatter[field]
        kind = spec["type"]

        if kind == "int":
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                report.err(f"frontmatter: '{field}' must be int, got {value!r}")
                continue
            if "equals" in spec and parsed != spec["equals"]:
                report.err(f"frontmatter: '{field}' must equal {spec['equals']}, got {parsed}")

        elif kind == "slug":
            if not isinstance(value, str) or not SLUG_RE.match(value):
                report.err(f"frontmatter: '{field}' must be kebab-case slug, got {value!r}")

        elif kind == "str":
            if not isinstance(value, str) or not value.strip():
                report.err(f"frontmatter: '{field}' must be non-empty string, got {value!r}")

        elif kind == "maybe_str":
            if value not in (None, "") and not isinstance(value, str):
                report.err(f"frontmatter: '{field}' must be string or null, got {value!r}")

        elif kind == "enum":
            if value not in spec["enum"]:
                report.err(f"frontmatter: '{field}' must be one of {spec['enum']}, got {value!r}")

        elif kind == "list":
            if not isinstance(value, list) or not value:
                report.err(f"frontmatter: '{field}' must be a non-empty list, got {value!r}")

        elif kind == "date":
            parsed_date = _parse_iso_date(str(value))
            if not parsed_date:
                report.err(f"frontmatter: '{field}' must be YYYY-MM-DD, got {value!r}")
            elif parsed_date > date.today():
                report.warn(f"frontmatter: '{field}' is in the future ({value})")

    expected_slug_from_folder = folder.name.removeprefix("context-map-")
    if frontmatter.get("project_slug") and frontmatter["project_slug"] != expected_slug_from_folder:
        report.err(
            f"frontmatter: 'project_slug' ({frontmatter['project_slug']!r}) "
            f"does not match folder suffix ({expected_slug_from_folder!r})"
        )

    if frontmatter.get("project_id") and frontmatter.get("project_slug"):
        if frontmatter["project_id"] != frontmatter["project_slug"]:
            report.err(
                f"frontmatter: 'project_id' must equal 'project_slug' "
                f"({frontmatter['project_id']!r} vs {frontmatter['project_slug']!r})"
            )

    scale = frontmatter.get("scale")
    return scale if scale in REQUIRED_SECTIONS_BY_SCALE else None


def _validate_required_sections(body: str, scale: str, report: Report) -> None:
    required = REQUIRED_SECTIONS_BY_SCALE.get(scale, [])
    headings = {match.strip() for match in re.findall(r"^##\s+(.+?)\s*$", body, re.MULTILINE)}
    for heading in required:
        if heading not in headings:
            report.err(f"context-map.md: missing required section '## {heading}' for scale {scale}")


def _validate_generic_table(
    body: str,
    heading: str,
    expected_columns: list[str],
    report: Report,
    required: bool,
) -> list[dict[str, str]]:
    text = section_text(body, heading)
    if not text:
        if required:
            report.err(f"context-map.md: '## {heading}' section is missing")
        return []
    header = _parse_table_header(text)
    if header is None:
        if required:
            report.err(f"context-map.md: '## {heading}' has no canonical table")
        return []
    if header != expected_columns:
        report.err(
            f"context-map.md: '## {heading}' columns {header} do not match schema {expected_columns}"
        )
    return parse_first_table(text)


def _validate_confidence_notes(rows: list[dict[str, str]], report: Report) -> None:
    for idx, row in enumerate(rows, start=1):
        confidence = row.get("Confidence", "").strip().lower()
        if confidence and confidence not in CONFIDENCE_ENUM:
            report.err(
                f"context-map.md: Confidence Notes row {idx} has invalid Confidence "
                f"{confidence!r}; expected one of {CONFIDENCE_ENUM}"
            )
        needs_human = row.get("Needs Human?", "").strip().lower()
        if needs_human and needs_human not in NEEDS_HUMAN_ENUM:
            report.err(
                f"context-map.md: Confidence Notes row {idx} has invalid 'Needs Human?' "
                f"{needs_human!r}; expected {NEEDS_HUMAN_ENUM}"
            )


def _validate_split_file(folder: Path, filename: str, report: Report) -> None:
    path = folder / filename
    if not path.exists():
        report.err(f"{filename}: required split file is missing")
        return
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        report.err(f"{filename}: cannot read ({exc})")
        return

    spec = SPLIT_SPEC[filename]
    heading = spec["heading"]
    section = section_text(text, heading)
    if not section:
        report.err(f"{filename}: missing '## {heading}' heading")
        return

    header = _parse_table_header(section)
    if header is None:
        report.err(f"{filename}: no canonical table under '## {heading}'")
        return
    if header != spec["columns"]:
        report.err(
            f"{filename}: columns {header} do not match schema {spec['columns']}"
        )
        return

    rows = parse_first_table(section)
    if not rows:
        return  # empty table with correct header is allowed

    id_re = re.compile(ID_RE_TEMPLATE.format(prefix=spec["id_prefix"]))
    seen_ids: set[str] = set()
    for idx, row in enumerate(rows, start=1):
        row_id = row.get("ID", "").strip()
        if not id_re.match(row_id):
            report.err(f"{filename} row {idx}: ID {row_id!r} does not match {spec['id_prefix']}-###")
        elif row_id in seen_ids:
            report.err(f"{filename} row {idx}: duplicate ID {row_id!r}")
        else:
            seen_ids.add(row_id)

        for column, allowed in spec.get("enums", {}).items():
            value = row.get(column, "").strip().lower()
            if value and value not in [a.lower() for a in allowed]:
                report.err(
                    f"{filename} row {idx}: column '{column}' has invalid value "
                    f"{value!r}; expected one of {allowed}"
                )

        for column in spec.get("date_columns", []):
            value = row.get(column, "").strip()
            if value and not _parse_iso_date(value):
                report.err(
                    f"{filename} row {idx}: column '{column}' must be YYYY-MM-DD, got {value!r}"
                )


# ---- Public API -----------------------------------------------------------


def validate_folder(folder: Path) -> Report:
    report = Report(folder)
    if not folder.exists() or not folder.is_dir():
        report.err(f"folder does not exist: {folder}")
        return report
    if not folder.name.startswith("context-map-"):
        report.err(f"folder name must start with 'context-map-': {folder.name}")

    main = folder / "context-map.md"
    if not main.exists():
        report.err("context-map.md is missing in folder")
        return report

    try:
        text = main.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        report.err(f"cannot read context-map.md ({exc})")
        return report

    frontmatter, body = parse_frontmatter(text)
    if not frontmatter:
        report.err("context-map.md: missing or malformed YAML frontmatter")
        return report

    scale = _validate_frontmatter(folder, frontmatter, report)

    if scale:
        _validate_required_sections(body, scale, report)

    _validate_generic_table(body, "Tech Stack", TECH_STACK_COLUMNS, report, required=bool(scale))
    confidence_rows = _validate_generic_table(
        body, "Confidence Notes", CONFIDENCE_COLUMNS, report, required=bool(scale)
    )
    _validate_confidence_notes(confidence_rows, report)

    if scale and scale != "XS":
        _validate_generic_table(body, "Read First By Task Type", READ_FIRST_COLUMNS, report, required=True)

    if scale:
        for filename in SPLIT_FILES_BY_SCALE.get(scale, []):
            if filename == "architecture.md":
                # architecture.md is free-form; only presence required.
                if not (folder / filename).exists():
                    report.err(f"{filename}: required file is missing for scale {scale}")
                continue
            _validate_split_file(folder, filename, report)

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a context-map-<slug>/ folder against schema.")
    parser.add_argument("folder", help="Path to the context-map-<slug> folder")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    folder = Path(args.folder).expanduser().resolve()
    report = validate_folder(folder)

    if args.format == "json":
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        if report.errors:
            print(f"FAIL {folder}")
            for err in report.errors:
                print(f"  ERROR: {err}")
        else:
            print(f"OK   {folder}")
        for warn in report.warnings:
            print(f"  WARN:  {warn}")

    return 0 if report.ok() else 1


if __name__ == "__main__":
    raise SystemExit(main())
