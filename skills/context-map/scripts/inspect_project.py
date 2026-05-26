#!/usr/bin/env python3
"""Inspect a project and print facts useful for generating context-map.md."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    ".next",
    "dist",
    "build",
    ".build",
    "DerivedData",
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "coverage",
    ".turbo",
    ".cache",
    "Pods",
    "vendor",
}

SOURCE_EXTENSIONS = {
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".py",
    ".swift",
    ".kt",
    ".java",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".cs",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".css",
    ".scss",
    ".html",
    ".vue",
    ".svelte",
    ".sql",
}

DOC_NAMES = {
    "readme",
    "claude",
    "agents",
    "gemini",
    "architecture",
    "prd",
    "decisions",
    "decision",
    "adr",
    "known-issues",
    "known_issues",
    "troubleshooting",
    "fixed-errors",
    "context-map",
}

TODO_RE = re.compile(
    r"(^\s*[-*]\s*(TODO|FIXME|HACK|XXX)\b)|"
    r"(^\s*(#|//|/\*|<!--|--|;)\s*(TODO|FIXME|HACK|XXX)\b)|"
    r"(^\s*(TODO|FIXME|HACK|XXX)\b[:\s-])",
    re.IGNORECASE,
)


@dataclass
class FileInfo:
    path: str
    lines: int
    bytes: int


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def should_skip_dir(path: Path) -> bool:
    return path.name in EXCLUDED_DIRS


def iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS and not d.startswith(".Trash")]
        if should_skip_dir(current):
            continue
        for filename in filenames:
            files.append(current / filename)
    return sorted(files)


def count_lines(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return 0


def detect_stacks(root: Path, files: list[Path]) -> list[str]:
    names = {rel(p, root) for p in files}
    stacks: set[str] = set()

    def has(path: str) -> bool:
        return path in names

    def any_name(name: str) -> bool:
        return any(p.name == name for p in files)

    if has("package.json"):
        stacks.add("Node.js")
        pkg = read_json(root / "package.json")
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})} if isinstance(pkg, dict) else {}
        if "next" in deps or any(p.name.startswith("next.config") for p in files):
            stacks.add("Next.js")
        if "react" in deps:
            stacks.add("React")
        if "vite" in deps or any(p.name.startswith("vite.config") for p in files):
            stacks.add("Vite")
        if "tailwindcss" in deps:
            stacks.add("Tailwind CSS")
    if any_name("pyproject.toml") or any_name("requirements.txt"):
        stacks.add("Python")
    if any_name("manage.py"):
        stacks.add("Django")
    if any("fastapi" in p.name.lower() for p in files) or any("uvicorn" in safe_read(p, 2000).lower() for p in files if p.name in {"requirements.txt", "pyproject.toml"}):
        stacks.add("FastAPI")
    if any_name("Cargo.toml"):
        stacks.add("Rust")
    if any_name("go.mod"):
        stacks.add("Go")
    if any_name("Dockerfile") or any_name("docker-compose.yml") or any_name("compose.yml"):
        stacks.add("Docker")
    if any(p.suffix == ".swift" for p in files) or any(p.suffix in {".xcodeproj", ".xcworkspace"} for p in files):
        stacks.add("Swift/iOS/macOS")
    if any("wrangler" in p.name for p in files):
        stacks.add("Cloudflare Workers")
    if any(p.name == "schema.prisma" for p in files):
        stacks.add("Prisma")
    if any("migrations" in p.parts for p in files) or any("alembic" in p.parts for p in files):
        stacks.add("Database migrations")
    if any(".github/workflows" in rel(p, root) for p in files):
        stacks.add("GitHub Actions")
    return sorted(stacks)


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def safe_read(path: Path, limit: int) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            return handle.read(limit)
    except OSError:
        return ""


def package_scripts(root: Path) -> dict[str, str]:
    pkg = read_json(root / "package.json")
    scripts = pkg.get("scripts", {}) if isinstance(pkg, dict) else {}
    return scripts if isinstance(scripts, dict) else {}


def find_docs(root: Path, files: list[Path]) -> list[str]:
    docs: list[str] = []
    for path in files:
        stem = path.stem.lower()
        name = path.name.lower()
        relpath = rel(path, root)
        if path.suffix.lower() in {".md", ".mdx", ".txt"} and (
            stem in DOC_NAMES
            or any(token in name for token in ["decision", "known", "troubleshoot", "context", "architecture", "prd", "adr"])
            or relpath in {"CLAUDE.md", "AGENTS.md", "GEMINI.md", "README.md"}
        ):
            docs.append(relpath)
    return sorted(docs)


def find_entry_points(root: Path, files: list[Path]) -> list[str]:
    candidates = []
    patterns = {
        "main.py",
        "app.py",
        "server.py",
        "index.py",
        "main.ts",
        "main.tsx",
        "index.ts",
        "index.tsx",
        "server.ts",
        "app.ts",
        "App.tsx",
        "page.tsx",
        "main.go",
        "lib.rs",
        "main.rs",
        "Package.swift",
        "Dockerfile",
        "docker-compose.yml",
        "compose.yml",
        "wrangler.toml",
        "wrangler.jsonc",
    }
    for path in files:
        relpath = rel(path, root)
        if path.name in patterns:
            candidates.append(relpath)
        elif ".github/workflows/" in relpath:
            candidates.append(relpath)
        elif path.name.endswith("App.swift"):
            candidates.append(relpath)
    return sorted(set(candidates))[:80]


def find_env_examples(root: Path, files: list[Path]) -> list[str]:
    result = []
    for path in files:
        name = path.name.lower()
        if name.startswith(".env") or name.endswith(".env") or ".env.example" in name or name in {"env.example", "example.env"}:
            result.append(rel(path, root))
    return sorted(result)


def find_largest_files(root: Path, files: list[Path], limit: int) -> list[FileInfo]:
    infos = []
    for path in files:
        if path.suffix.lower() not in SOURCE_EXTENSIONS and path.suffix.lower() not in {".md", ".yml", ".yaml", ".json", ".toml"}:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        lines = count_lines(path)
        infos.append(FileInfo(rel(path, root), lines, size))
    infos.sort(key=lambda item: (item.lines, item.bytes), reverse=True)
    return infos[:limit]


def find_todos(root: Path, files: list[Path], limit: int) -> list[dict[str, Any]]:
    hits = []
    for path in files:
        if path.suffix.lower() not in SOURCE_EXTENSIONS and path.suffix.lower() not in {".md", ".txt"}:
            continue
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as handle:
                for number, line in enumerate(handle, start=1):
                    if TODO_RE.search(line):
                        hits.append({"path": rel(path, root), "line": number, "text": line.strip()[:220]})
                        if len(hits) >= limit:
                            return hits
        except OSError:
            continue
    return hits


def _run_git(root: Path, args: list[str], limit_bytes: int = 200_000) -> str | None:
    if shutil.which("git") is None:
        return None
    if not (root / ".git").exists():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    output = result.stdout or ""
    return output[:limit_bytes]


def extract_git_signals(root: Path, max_commits: int = 50, churn_window: int = 200) -> dict[str, Any] | None:
    """Collect recent history and churn signals. Returns None if no git repo."""
    if not (root / ".git").exists():
        return None

    branch = _run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"])
    head = _run_git(root, ["rev-parse", "HEAD"])
    remote = _run_git(root, ["remote", "get-url", "origin"])
    last_commit_date = _run_git(root, ["log", "-1", "--format=%cd", "--date=short"])
    commit_count_30d = _run_git(root, ["rev-list", "--count", "--since=30.days", "HEAD"])

    recent_raw = _run_git(
        root,
        ["log", f"-n{max_commits}", "--pretty=format:%h|%ad|%s", "--date=short"],
    ) or ""
    recent_commits: list[dict[str, str]] = []
    for line in recent_raw.splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3:
            recent_commits.append({"sha": parts[0], "date": parts[1], "subject": parts[2][:200]})

    churn_raw = _run_git(
        root,
        ["log", f"-n{churn_window}", "--name-only", "--pretty=format:"],
    ) or ""
    top_dir_counter: Counter[str] = Counter()
    file_counter: Counter[str] = Counter()
    for line in churn_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        file_counter[line] += 1
        parts = line.split("/", 1)
        top_dir_counter[parts[0] if len(parts) > 1 else "(root)"] += 1
    top_dirs = [{"dir": d, "touches": c} for d, c in top_dir_counter.most_common(10)]
    top_files = [{"path": f, "touches": c} for f, c in file_counter.most_common(20)]

    # Recently changed directories in the last 14 days.
    recent14_raw = _run_git(
        root,
        ["log", "--since=14.days", "--name-only", "--pretty=format:"],
    ) or ""
    recent_dirs: Counter[str] = Counter()
    for line in recent14_raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("/", 1)
        recent_dirs[parts[0] if len(parts) > 1 else "(root)"] += 1
    recently_changed = [d for d, _ in recent_dirs.most_common(8)]

    return {
        "branch": (branch or "").strip() or None,
        "head": (head or "").strip() or None,
        "remote": (remote or "").strip() or None,
        "last_commit_date": (last_commit_date or "").strip() or None,
        "commit_count_30d": int((commit_count_30d or "0").strip() or 0) or 0,
        "recent_commits": recent_commits,
        "top_churn_dirs": top_dirs,
        "top_churn_files": top_files,
        "recently_changed_dirs": recently_changed,
    }


_BACKTICK_TOKEN_RE = re.compile(r"`([^`\n]{2,200})`")
_DOC_FOR_DRIFT = {"readme.md", "claude.md", "agents.md", "gemini.md"}
_DRIFT_DOC_TOKEN_SUFFIXES = (".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".swift",
                             ".kt", ".java", ".rb", ".cs", ".cpp", ".c", ".h", ".md",
                             ".yml", ".yaml", ".toml", ".json", ".html", ".css", ".sql")


def _looks_like_path_token(token: str) -> bool:
    if not token or len(token) > 160:
        return False
    if any(c in token for c in [" ", "\t", "\"", "'"]):
        return False
    if token.startswith(("http://", "https://", "git@")):
        return False
    if "/" in token:
        return True
    return token.endswith(_DRIFT_DOC_TOKEN_SUFFIXES)


def extract_doc_drift(root: Path, files: list[Path]) -> list[dict[str, Any]]:
    """Scan README and agent files for backticked path-like tokens that don't exist in repo."""
    existing = {rel(p, root) for p in files}
    # Index file names for loose matching.
    basenames = {p.name for p in files}
    drift: list[dict[str, Any]] = []
    for path in files:
        if path.name.lower() not in _DOC_FOR_DRIFT:
            continue
        content = safe_read(path, 200_000)
        if not content:
            continue
        seen: set[str] = set()
        for match in _BACKTICK_TOKEN_RE.finditer(content):
            token = match.group(1).strip().strip("/")
            if not _looks_like_path_token(token):
                continue
            if token in seen:
                continue
            seen.add(token)
            found = token in existing or token.split("/")[-1] in basenames
            if found:
                continue
            # Compute line number of the match.
            line_num = content.count("\n", 0, match.start()) + 1
            drift.append({
                "doc": rel(path, root),
                "doc_line": line_num,
                "claim": token,
                "confidence": "stale",
                "evidence": "not found in repo files",
            })
            if len(drift) >= 80:
                return drift
    return drift


# Directories that are containers, not domains — expand to their children.
_CONTAINER_DIRS = {"apps", "packages", "services", "modules", "libs", "crates"}
# Directories that are tooling/noise, never a domain on their own.
_NON_DOMAIN_DIRS = {
    "node_modules", ".git", "dist", "build", ".next", "out", "target", "vendor",
    ".venv", "venv", "__pycache__", ".turbo", "coverage", ".cache", "tmp",
    "tests", "test", "__tests__", "fixtures", "e2e",
}


def derive_domain_candidates(root: Path, files: list[Path], git: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Propose navigation-layer domain candidates from the file tree + churn.

    These are SEED suggestions for the skill's Decompose phase — the human
    edits/accepts them. Each candidate clusters a directory (expanding monorepo
    containers like apps/ and packages/ to their children) with its source-file
    count and recent churn, so the largest/most-active areas surface first.
    Returns up to ~14 candidates ranked by source count.
    """
    source = [p for p in files if p.suffix.lower() in SOURCE_EXTENSIONS]
    if not source:
        return []

    # churn touches per top-level dir, for ranking/rationale
    churn_by_top: dict[str, int] = {}
    if git:
        for item in git.get("top_churn_dirs", []):
            churn_by_top[item.get("dir", "")] = item.get("touches", 0)

    # Count source files per candidate root.
    counts: Counter[str] = Counter()
    for p in source:
        parts = p.relative_to(root).parts
        if not parts or len(parts) < 2:
            continue  # top-level loose files aren't a domain
        top = parts[0]
        if top in _NON_DOMAIN_DIRS or top.startswith("."):
            continue
        if top in _CONTAINER_DIRS and len(parts) >= 3:
            # expand: apps/web/..., packages/ui/... -> "apps/web", "packages/ui"
            counts[f"{top}/{parts[1]}"] += 1
        else:
            counts[top] += 1

    candidates: list[dict[str, Any]] = []
    for root_path, n in counts.most_common(14):
        if n < 2:
            continue
        top = root_path.split("/", 1)[0]
        candidates.append({
            "suggested_name": root_path.replace("/", "-"),
            "roots": [root_path],
            "source_files": n,
            "churn_touches": churn_by_top.get(top, 0),
            "why": "high churn" if churn_by_top.get(top, 0) >= 10 else "size",
        })
    return candidates


def classify_scale(source_count: int, stacks: list[str], files: list[Path], root: Path) -> str:
    rels = {rel(p, root) for p in files}
    has_prod_signal = any(
        signal in stacks
        for signal in ["Docker", "GitHub Actions", "Database migrations", "Prisma", "Cloudflare Workers"]
    )
    major_dirs = {part for p in files for part in p.relative_to(root).parts[:1]}
    app_like_dirs = major_dirs & {"frontend", "backend", "admin", "web", "ios", "android", "apps", "packages", "worker", "workers"}
    if len(app_like_dirs) >= 3 or "packages" in app_like_dirs or "apps" in app_like_dirs:
        return "L" if source_count < 1000 else "XL"
    if source_count <= 5 and not has_prod_signal:
        return "XS"
    if source_count <= 25 and not has_prod_signal:
        return "S"
    if source_count <= 150:
        return "M"
    if source_count <= 1000:
        return "L"
    return "XL"


def inspect(root: Path, largest_limit: int, todo_limit: int) -> dict[str, Any]:
    root = root.resolve()
    files = iter_files(root)
    source_files = [p for p in files if p.suffix.lower() in SOURCE_EXTENSIONS]
    stacks = detect_stacks(root, files)
    scale = classify_scale(len(source_files), stacks, files, root)
    docs = find_docs(root, files)
    decision_docs = [p for p in docs if any(t in p.lower() for t in ["decision", "adr"])]
    known_issue_docs = [p for p in docs if any(t in p.lower() for t in ["known", "troubleshoot", "fixed-error"])]
    git = extract_git_signals(root)

    return {
        "root": str(root),
        "scale": scale,
        "counts": {
            "files_total": len(files),
            "source_files": len(source_files),
        },
        "stacks": stacks,
        "package_scripts": package_scripts(root),
        "entry_points": find_entry_points(root, files),
        "env_examples": find_env_examples(root, files),
        "docs": docs,
        "decision_docs": decision_docs,
        "known_issue_docs": known_issue_docs,
        "largest_files": [asdict(info) for info in find_largest_files(root, files, largest_limit)],
        "todo_hits": find_todos(root, files, todo_limit),
        "git": git,
        "drift_candidates": extract_doc_drift(root, files),
        "domain_candidates": derive_domain_candidates(root, files, git),
    }


def markdown_report(data: dict[str, Any]) -> str:
    lines = []
    lines.append(f"# Project Inspection: {Path(data['root']).name}")
    lines.append("")
    lines.append(f"- Root: `{data['root']}`")
    lines.append(f"- Suggested scale: **{data['scale']}**")
    lines.append(f"- Files: {data['counts']['files_total']} total, {data['counts']['source_files']} source")
    lines.append(f"- Stacks: {', '.join(data['stacks']) or 'none detected'}")
    lines.append("")

    def section(title: str, values: list[str]) -> None:
        lines.append(f"## {title}")
        lines.append("")
        if values:
            for value in values:
                lines.append(f"- `{value}`")
        else:
            lines.append("- None found")
        lines.append("")

    section("Entry Points", data["entry_points"])
    section("Docs", data["docs"])
    section("Decision Docs", data["decision_docs"])
    section("Known Issue Docs", data["known_issue_docs"])
    section("Env Examples", data["env_examples"])

    lines.append("## Package Scripts")
    lines.append("")
    scripts = data["package_scripts"]
    if scripts:
        for name, command in scripts.items():
            lines.append(f"- `{name}`: `{command}`")
    else:
        lines.append("- None found")
    lines.append("")

    lines.append("## Largest Files")
    lines.append("")
    if data["largest_files"]:
        lines.append("| File | Lines | Bytes |")
        lines.append("|------|-------|-------|")
        for item in data["largest_files"]:
            lines.append(f"| `{item['path']}` | {item['lines']} | {item['bytes']} |")
    else:
        lines.append("- None found")
    lines.append("")

    lines.append("## Domain Candidates (navigation layer seed)")
    lines.append("")
    if data.get("domain_candidates"):
        lines.append("| Suggested domain | Roots | Source files | Churn | Why |")
        lines.append("|------------------|-------|--------------|-------|-----|")
        for item in data["domain_candidates"]:
            roots = ", ".join(f"`{r}`" for r in item["roots"])
            lines.append(
                f"| {item['suggested_name']} | {roots} | {item['source_files']} "
                f"| {item['churn_touches']} | {item['why']} |"
            )
        lines.append("")
        lines.append("_Seed suggestions — the skill's Decompose phase edits/confirms these with the user._")
    else:
        lines.append("- None (too small for the navigation layer; memory layer only)")
    lines.append("")

    lines.append("## TODO / FIXME / HACK")
    lines.append("")
    if data["todo_hits"]:
        lines.append("| File | Line | Text |")
        lines.append("|------|------|------|")
        for item in data["todo_hits"]:
            text = item["text"].replace("|", "\\|")
            lines.append(f"| `{item['path']}` | {item['line']} | {text} |")
    else:
        lines.append("- None found")
    lines.append("")

    lines.append("## Git Signals")
    lines.append("")
    git = data.get("git")
    if not git:
        lines.append("- No git repository detected.")
    else:
        lines.append(f"- Branch: `{git.get('branch') or '?'}`")
        lines.append(f"- HEAD: `{git.get('head') or '?'}`")
        lines.append(f"- Remote: `{git.get('remote') or 'none'}`")
        lines.append(f"- Last commit: {git.get('last_commit_date') or '?'}")
        lines.append(f"- Commits last 30 days: {git.get('commit_count_30d', 0)}")
        if git.get("recently_changed_dirs"):
            lines.append(f"- Recently changed dirs (14d): {', '.join(f'`{d}`' for d in git['recently_changed_dirs'])}")
        if git.get("top_churn_dirs"):
            lines.append("- Top churn dirs:")
            for item in git["top_churn_dirs"][:5]:
                lines.append(f"  - `{item['dir']}` — {item['touches']} touches")
    lines.append("")

    lines.append("## Doc Drift Candidates")
    lines.append("")
    drift = data.get("drift_candidates") or []
    if drift:
        lines.append("| Doc | Line | Claim | Confidence | Evidence |")
        lines.append("|-----|------|-------|------------|----------|")
        for item in drift[:40]:
            lines.append(
                f"| `{item['doc']}` | {item['doc_line']} | `{item['claim']}` | "
                f"{item['confidence']} | {item['evidence']} |"
            )
    else:
        lines.append("- None flagged")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect project facts for context-map generation.")
    parser.add_argument("project", nargs="?", default=".", help="Project root path")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    parser.add_argument("--largest", type=int, default=20, help="Number of largest files to report")
    parser.add_argument("--todos", type=int, default=50, help="Number of TODO/FIXME/HACK hits to report")
    args = parser.parse_args()

    root = Path(args.project)
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Project path is not a directory: {root}")

    data = inspect(root, args.largest, args.todos)
    if args.format == "json":
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(markdown_report(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
