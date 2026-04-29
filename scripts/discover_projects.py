#!/usr/bin/env python3
"""Discover project candidates across one or more roots for batch context maps."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from inspect_project import EXCLUDED_DIRS, detect_stacks, classify_scale, iter_files  # noqa: E402


PROJECT_MARKERS = {
    ".git",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "Dockerfile",
    "docker-compose.yml",
    "compose.yml",
    "go.mod",
    "Cargo.toml",
    "project.yml",
    "Package.swift",
    "SKILL.md",
    "wrangler.toml",
    "wrangler.jsonc",
}

CONTEXT_MAP_FOLDER_PATTERN = "context-map-*"

LEGACY_CONTEXT_MAP_NAMES = [
    "context-map.md",
    "docs/context-map.md",
    "CONTEXT-MAP.md",
    "docs/CONTEXT-MAP.md",
]


def expand(path: str) -> Path:
    return Path(path).expanduser().resolve()


def load_config(path: str | None) -> dict[str, Any]:
    if not path:
        default = Path("~/.context-map/config.json").expanduser()
        path_obj = default
    else:
        path_obj = Path(path).expanduser()
    if not path_obj.exists():
        return {}
    try:
        return json.loads(path_obj.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Failed to read config {path_obj}: {exc}") from exc


def candidate_marker_names(path: Path) -> list[str]:
    markers = []
    try:
        names = {child.name for child in path.iterdir()}
    except OSError:
        return []
    for marker in sorted(PROJECT_MARKERS):
        if marker in names:
            markers.append(marker)
    if any(child.suffix in {".xcodeproj", ".xcworkspace"} for child in path.iterdir() if child.exists()):
        markers.append("xcodeproj")
    return markers


def is_project_candidate(path: Path) -> bool:
    if path.suffix in {".xcodeproj", ".xcworkspace"}:
        return False
    return bool(candidate_marker_names(path))


def has_git(path: Path) -> bool:
    return (path / ".git").exists()


def within_depth(root: Path, path: Path, max_depth: int) -> bool:
    try:
        depth = len(path.relative_to(root).parts)
    except ValueError:
        return False
    return depth <= max_depth


def _parse_frontmatter_version(main_file: Path) -> int | None:
    """Return context_map_version from the YAML frontmatter, or None on failure."""
    try:
        with main_file.open("r", encoding="utf-8", errors="ignore") as handle:
            first = handle.readline()
            if first.strip() != "---":
                return None
            for _ in range(40):
                line = handle.readline()
                if not line:
                    return None
                line = line.rstrip("\n")
                if line.strip() == "---":
                    return None
                if ":" in line:
                    key, _, value = line.partition(":")
                    if key.strip() == "context_map_version":
                        try:
                            return int(value.strip())
                        except ValueError:
                            return None
    except OSError:
        return None
    return None


def find_context_map_folder(path: Path, pattern: str = CONTEXT_MAP_FOLDER_PATTERN) -> dict[str, Any] | None:
    """Return info about a v2 context-map folder, or None if absent."""
    for child in sorted(path.glob(pattern)):
        if not child.is_dir():
            continue
        main_file = child / "context-map.md"
        if not main_file.exists() or not main_file.is_file():
            continue
        version = _parse_frontmatter_version(main_file)
        last_updated = _parse_frontmatter_field(main_file, "last_updated")
        last_verified = _parse_frontmatter_field(main_file, "last_verified_vs_code")
        status = "v2" if version == 2 else "invalid"
        return {
            "folder": str(child),
            "main": str(main_file),
            "context_map_version": version,
            "last_updated": last_updated,
            "last_verified_vs_code": last_verified,
            "status": status,
        }
    return None


def _parse_frontmatter_field(main_file: Path, key: str) -> str | None:
    try:
        with main_file.open("r", encoding="utf-8", errors="ignore") as handle:
            first = handle.readline()
            if first.strip() != "---":
                return None
            for _ in range(40):
                line = handle.readline()
                if not line:
                    return None
                if line.strip() == "---":
                    return None
                if ":" in line:
                    k, _, v = line.partition(":")
                    if k.strip() == key:
                        return v.strip().strip('"').strip("'") or None
    except OSError:
        return None
    return None


def find_legacy_context_map(path: Path, names: list[str]) -> str | None:
    for name in names:
        candidate = path / name
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    return None


def git_info(path: Path) -> dict[str, Any]:
    if not has_git(path):
        return {"is_repo": False}
    info: dict[str, Any] = {"is_repo": True}
    try:
        branch = subprocess.run(
            ["git", "-C", str(path), "branch", "--show-current"],
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
        info["branch"] = branch.stdout.strip() or "detached"
        status = subprocess.run(
            ["git", "-C", str(path), "status", "--short"],
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
        info["dirty"] = bool(status.stdout.strip())
        remote = subprocess.run(
            ["git", "-C", str(path), "remote", "get-url", "origin"],
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
        info["remote"] = remote.stdout.strip() if remote.returncode == 0 else ""
    except Exception as exc:
        info["error"] = str(exc)
    return info


def source_count(files: list[Path]) -> int:
    source_exts = {
        ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".py", ".swift", ".kt", ".java",
        ".go", ".rs", ".rb", ".php", ".cs", ".cpp", ".c", ".h", ".hpp", ".css", ".scss",
        ".html", ".vue", ".svelte", ".sql",
    }
    return sum(1 for path in files if path.suffix.lower() in source_exts)


def discover_roots(
    roots: list[Path],
    max_depth: int,
    legacy_names: list[str],
    folder_pattern: str = CONTEXT_MAP_FOLDER_PATTERN,
) -> list[dict[str, Any]]:
    candidates: dict[str, Path] = {}
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue
        for dirpath, dirnames, _filenames in os.walk(root):
            current = Path(dirpath)
            dirnames[:] = [
                d
                for d in dirnames
                if d not in EXCLUDED_DIRS and Path(d).suffix not in {".xcodeproj", ".xcworkspace"}
            ]
            if not within_depth(root, current, max_depth):
                dirnames[:] = []
                continue
            if is_project_candidate(current):
                candidates[str(current.resolve())] = current.resolve()
                if has_git(current):
                    dirnames[:] = [d for d in dirnames if d == ".git"]

    rows = []
    for path in sorted(candidates.values(), key=lambda p: str(p).lower()):
        files = iter_files(path)
        stacks = detect_stacks(path, files)
        scale = classify_scale(source_count(files), stacks, files, path)
        markers = candidate_marker_names(path)
        v2 = find_context_map_folder(path, folder_pattern)
        legacy = find_legacy_context_map(path, legacy_names)

        if v2:
            status = v2["status"]
            context_map_folder = v2["folder"]
            context_map_main = v2["main"]
            last_updated = v2.get("last_updated")
            last_verified = v2.get("last_verified_vs_code")
            context_map_version = v2.get("context_map_version")
        else:
            status = "legacy" if legacy else "none"
            context_map_folder = None
            context_map_main = None
            last_updated = None
            last_verified = None
            context_map_version = None

        rows.append(
            {
                "name": path.name,
                "path": str(path),
                "scale": scale,
                "stacks": stacks,
                "markers": markers,
                "context_map_status": status,
                "context_map_folder": context_map_folder,
                "context_map_main": context_map_main,
                "context_map_version": context_map_version,
                "last_updated": last_updated,
                "last_verified_vs_code": last_verified,
                "legacy_context_map": legacy,
                "git": git_info(path),
            }
        )
    return rows


def markdown(rows: list[dict[str, Any]], roots: list[Path]) -> str:
    lines = [
        "# Context Map Project Discovery",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Roots: {', '.join(f'`{root}`' for root in roots)}",
        f"- Candidates: {len(rows)}",
        "",
    ]
    if not rows:
        lines.append("No project candidates found.")
        return "\n".join(lines)

    for index, row in enumerate(rows, start=1):
        git = row["git"]
        git_text = "no git"
        if git.get("is_repo"):
            git_text = f"branch={git.get('branch', 'unknown')}, dirty={git.get('dirty', 'unknown')}"
        stacks = ", ".join(row["stacks"]) or "none detected"
        markers = ", ".join(row["markers"])

        status = row["context_map_status"]
        if status == "v2":
            extras = []
            if row.get("last_verified_vs_code"):
                extras.append(f"last_verified {row['last_verified_vs_code']}")
            folder = row.get("context_map_folder") or ""
            suffix = f" — `{folder}`" + (" (" + ", ".join(extras) + ")" if extras else "")
        elif status == "legacy":
            suffix = f" (`{row.get('legacy_context_map')}`, migrate recommended)"
        elif status == "invalid":
            suffix = f" — `{row.get('context_map_folder')}` (schema violation, audit)"
        else:
            suffix = ""
        context_map_line = f"- Context map: {status}{suffix}"

        lines.extend(
            [
                f"## [{index}] {row['name']}",
                "",
                f"- Path: `{row['path']}`",
                f"- Scale: `{row['scale']}`",
                f"- Stack: {stacks}",
                f"- Markers: {markers}",
                context_map_line,
                f"- Git: {git_text}",
                "",
            ]
        )
    lines.extend(
        [
            "## Selection Syntax",
            "",
            "- `1,3,5-8`",
            "- `all`",
            "- `none`",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover project candidates for batch context-map generation.")
    parser.add_argument("roots", nargs="*", help="Project root directories to scan")
    parser.add_argument("--config", help="Path to ~/.context-map/config.json")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
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

    rows = discover_roots(roots, args.max_depth, legacy_names, folder_pattern)
    payload = {
        "version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "roots": [str(root) for root in roots],
        "projects": rows,
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(markdown(rows, roots))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
