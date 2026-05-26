#!/usr/bin/env python3
"""Tech-lead linter for the navigation layer (`agent-docs/`).

Run after writer subagents finish (Document phase) or after a multi-domain
update. Checks every domain doc for the structural invariants the skill
enforces:
- required headers present, in order;
- Last verified line;
- length ceiling (200 lines);
- banned marketing phrases;
- canonical table column headers;
- Neighbors graph references existing domains;
- bidirectional Neighbors consistency;
- _meta/domain-paths.json points to real directories;
- MAP.md domain table matches files in domains/.

Read-only. Exit 1 if any ERROR is found (WARNs do not fail).
This is the navigation-layer counterpart to `validate_context_map.py`
(which validates the gitignored memory layer). The two stay separate —
different schemas, different invariants — and `audit`/Verify run both.

Usage:
  python scripts/lint_docs.py
  python scripts/lint_docs.py --root /path/to/project
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


BANNED_PHRASES = [
    "robust",
    "elegant",
    "beautifully",
    "beautiful",
    "scalable",
    "production-grade",
    "seamlessly",
    "seamless",
    "powerful",
    "comprehensive",
    "blazing fast",
    "lightning fast",
    "battle-tested",
    "industry-standard",
    "best-in-class",
    "state-of-the-art",
]

REQUIRED_HEADERS = [
    "# Domain:",  # title
    "## When to read me",
    "## Responsibility",
    "## Entry points",
    "## Architecture",
    "## Files of interest",
    "## Conventions",
    "## Gotchas",
    "## How to extend",
    "## Neighbors",
    "## Tests",
    "## Notes",
]

CANONICAL_TABLE_HEADERS = {
    "Entry points": "| File | Symbol | What it does |",
    "Files of interest": "| Path | What it does |",
}

DOC_MAX_LINES = 200
DOC_MIN_LINES = 30


class Issue:
    __slots__ = ("severity", "where", "msg")

    def __init__(self, severity: str, where: str, msg: str):
        self.severity = severity
        self.where = where
        self.msg = msg

    def __str__(self) -> str:
        return f"[{self.severity}] {self.where}: {self.msg}"


def check_doc(doc_path: Path, root: Path) -> list[Issue]:
    issues: list[Issue] = []
    rel = doc_path.relative_to(root)
    text = doc_path.read_text()
    lines = text.splitlines()

    # Length
    n = len(lines)
    if n > DOC_MAX_LINES:
        issues.append(Issue("WARN", str(rel), f"length {n} > {DOC_MAX_LINES} — consider splitting"))
    if n < DOC_MIN_LINES:
        issues.append(Issue("WARN", str(rel), f"length {n} < {DOC_MIN_LINES} — consider merging into another domain"))

    # Last verified
    if not re.search(r"\*\*Last verified\*\*:\s*\d{4}-\d{2}-\d{2}", text):
        issues.append(Issue("ERROR", str(rel), "missing or malformed `**Last verified**: YYYY-MM-DD` line"))

    # Required headers in order
    pos = 0
    for header in REQUIRED_HEADERS:
        try:
            idx = text.index(header, pos)
            pos = idx + len(header)
        except ValueError:
            issues.append(Issue("ERROR", str(rel), f"missing required header: `{header}`"))

    # Canonical table headers
    for section, expected in CANONICAL_TABLE_HEADERS.items():
        section_marker = f"## {section}"
        if section_marker not in text:
            continue
        idx = text.index(section_marker)
        end_idx = len(text)
        for next_h in ("## ",):
            next_idx = text.find(next_h, idx + len(section_marker))
            if next_idx != -1 and next_idx < end_idx:
                end_idx = next_idx
        section_body = text[idx:end_idx]
        if expected not in section_body:
            issues.append(Issue(
                "ERROR",
                str(rel),
                f"section `{section}` missing canonical table header `{expected}`",
            ))

    # Banned phrases
    lowered = text.lower()
    for phrase in BANNED_PHRASES:
        if phrase in lowered:
            issues.append(Issue("WARN", str(rel), f"banned marketing phrase: `{phrase}`"))

    return issues


def parse_neighbors(doc_path: Path) -> tuple[set[str], set[str]]:
    text = doc_path.read_text()
    deps_in: set[str] = set()
    deps_out: set[str] = set()
    section_match = re.search(r"## Neighbors(.*?)(?:\n## |\Z)", text, re.DOTALL)
    if not section_match:
        return deps_in, deps_out
    body = section_match.group(1)
    for line in body.splitlines():
        # "- **Depends on**: [name1.md](name1.md) (...), [name2.md](name2.md) ..."
        if "depends on" in line.lower():
            for m in re.finditer(r"\[([\w-]+)\.md\]", line):
                deps_in.add(m.group(1))
        elif "depended on by" in line.lower():
            for m in re.finditer(r"\[([\w-]+)\.md\]", line):
                deps_out.add(m.group(1))
    return deps_in, deps_out


def check_bidirectional(domain_docs: dict[str, Path]) -> list[Issue]:
    issues: list[Issue] = []
    neighbors: dict[str, tuple[set[str], set[str]]] = {
        name: parse_neighbors(path) for name, path in domain_docs.items()
    }
    for a, (a_in, a_out) in neighbors.items():
        for b in a_in:
            if b not in neighbors:
                issues.append(Issue("ERROR", f"domains/{a}.md", f"depends on unknown domain `{b}`"))
                continue
            _, b_out = neighbors[b]
            if a not in b_out:
                issues.append(Issue(
                    "WARN",
                    f"domains/{a}.md",
                    f"says it depends on `{b}`, but `{b}.md` does not list `{a}` in 'Depended on by'",
                ))
        for b in a_out:
            if b not in neighbors:
                issues.append(Issue("ERROR", f"domains/{a}.md", f"depended on by unknown domain `{b}`"))
                continue
            b_in, _ = neighbors[b]
            if a not in b_in:
                issues.append(Issue(
                    "WARN",
                    f"domains/{a}.md",
                    f"says it is depended on by `{b}`, but `{b}.md` does not list `{a}` in 'Depends on'",
                ))
    return issues


def check_domain_paths(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    dp_file = root / "agent-docs" / "_meta" / "domain-paths.json"
    if not dp_file.exists():
        issues.append(Issue("ERROR", "_meta/domain-paths.json", "missing"))
        return issues
    try:
        mapping = json.loads(dp_file.read_text())
    except json.JSONDecodeError as e:
        issues.append(Issue("ERROR", "_meta/domain-paths.json", f"invalid JSON: {e}"))
        return issues
    domains_dir = root / "agent-docs" / "domains"
    doc_names = {p.stem for p in domains_dir.glob("*.md")} if domains_dir.exists() else set()
    for domain, paths in mapping.items():
        if domain not in doc_names:
            issues.append(Issue(
                "ERROR",
                "_meta/domain-paths.json",
                f"domain `{domain}` has no matching `agent-docs/domains/{domain}.md`",
            ))
        for p in paths:
            target = root / p
            if not target.exists():
                issues.append(Issue(
                    "WARN",
                    "_meta/domain-paths.json",
                    f"`{domain}` references missing path `{p}`",
                ))
            # Freshness-gate friendliness: directory roots should not be bare
            # prefixes of sibling dirs. The gate now segment-matches, but warn
            # so the mapping stays readable.
            if target.is_dir() and not p.endswith("/"):
                issues.append(Issue(
                    "WARN",
                    "_meta/domain-paths.json",
                    f"`{domain}` directory root `{p}` has no trailing slash "
                    "(gate segment-matches anyway, but a trailing slash is clearer)",
                ))
    for d in doc_names:
        if d not in mapping:
            issues.append(Issue(
                "WARN",
                "_meta/domain-paths.json",
                f"domain doc `{d}.md` has no entry in domain-paths.json",
            ))
    return issues


def check_map_md(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    map_path = root / "agent-docs" / "MAP.md"
    domains_dir = root / "agent-docs" / "domains"
    if not map_path.exists():
        issues.append(Issue("ERROR", "MAP.md", "missing"))
        return issues
    if not domains_dir.exists():
        issues.append(Issue("ERROR", "domains/", "missing"))
        return issues
    map_text = map_path.read_text()
    listed = set(re.findall(r"\[([\w-]+)\.md\]\(domains/\1\.md\)", map_text))
    actual = {p.stem for p in domains_dir.glob("*.md")}
    for missing in actual - listed:
        issues.append(Issue("WARN", "MAP.md", f"domain `{missing}` exists in domains/ but not listed in MAP"))
    for ghost in listed - actual:
        issues.append(Issue("ERROR", "MAP.md", f"MAP references `{ghost}` but `domains/{ghost}.md` is missing"))
    # Cross-link to the memory layer: only relevant when a memory layer EXISTS.
    # A nav-only project legitimately has no context-map-<slug>/ — don't warn.
    memory_exists = any(root.glob("context-map-*"))
    if memory_exists:
        links_file = root / "agent-docs" / "_meta" / "links.json"
        has_link = "context-map-" in map_text or links_file.exists()
        if not has_link:
            issues.append(Issue(
                "WARN",
                "MAP.md",
                "memory layer present but MAP.md has no cross-link to it "
                "(expected a `## Project memory` reference to ../context-map-<slug>/ "
                "or an _meta/links.json) — run `reconcile`",
            ))
    return issues


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="Project root (default: cwd)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    domains_dir = root / "agent-docs" / "domains"
    if not domains_dir.exists():
        print(f"[lint] FAIL: {domains_dir} does not exist. Run the context-map skill (`decompose` / `generate --layer nav`) first.")
        return 1

    domain_docs = {p.stem: p for p in domains_dir.glob("*.md")}
    if not domain_docs:
        print(f"[lint] FAIL: no domain docs found under {domains_dir}.")
        return 1

    all_issues: list[Issue] = []
    for name, path in sorted(domain_docs.items()):
        all_issues.extend(check_doc(path, root))
    all_issues.extend(check_bidirectional(domain_docs))
    all_issues.extend(check_domain_paths(root))
    all_issues.extend(check_map_md(root))

    errors = [i for i in all_issues if i.severity == "ERROR"]
    warns = [i for i in all_issues if i.severity == "WARN"]

    if not all_issues:
        print(f"[lint] OK: {len(domain_docs)} domain docs clean.")
        return 0

    print(f"[lint] {len(domain_docs)} domain docs: {len(errors)} errors, {len(warns)} warnings\n")
    for issue in all_issues:
        print(f"  {issue}")
    print()
    if errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
