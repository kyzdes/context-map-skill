#!/usr/bin/env python3
"""Navigation-layer freshness gate (context-map skill).

If files inside a domain root were modified in the change set but the
corresponding `agent-docs/domains/<name>.md` was NOT, fail with a clear
fix command. Used as a pre-commit hook locally and as a required CI check.

This file is a TEMPLATE shipped by the context-map skill. At Phase 4 / `sustain`
it is copied into the target project's `scripts/` (it must live in the target
repo so CI can run it from there). It is zero-dependency: stdlib + git only.

Escape hatch: include `[skip-agent-docs]` or `[skip-agent-docs: dom1, dom2]`
in any commit message in the change set. Use only for trivial changes.

Usage:
  python scripts/check_agent_docs_freshness.py                     # local: vs HEAD~1
  python scripts/check_agent_docs_freshness.py --base origin/main  # CI

Exit codes:
  0 — pass (no stale docs, or stale-and-explicitly-skipped)
  1 — stale docs detected
  2 — misconfigured (missing _meta/domain-paths.json)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
META_DIR = REPO / "agent-docs" / "_meta"


# Files that don't trigger the gate even when inside a domain root.
# Add to this list cautiously — anything that hides real structural change
# silently rots the docs.
IGNORE_PATTERNS = [
    re.compile(r".*\.md$"),
    re.compile(r".*/tests?/.*"),
    re.compile(r".*/__tests__/.*"),
    re.compile(r".*\.test\.[jt]sx?$"),
    re.compile(r".*\.spec\.[jt]sx?$"),
    re.compile(r".*\.lock$"),
    re.compile(r".*-lock\.(json|yaml|yml)$"),
    re.compile(r".*/fixtures?/.*"),
    re.compile(r".*\.snap$"),
    re.compile(r".*\.gitignore$"),
    re.compile(r".*\.editorconfig$"),
]


def changed_files(base_ref: str) -> list[str]:
    out = subprocess.check_output(
        ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
        cwd=REPO,
        text=True,
    )
    return [line.strip() for line in out.splitlines() if line.strip()]


def commit_messages(base_ref: str) -> str:
    return subprocess.check_output(
        ["git", "log", "--format=%B", f"{base_ref}..HEAD"],
        cwd=REPO,
        text=True,
    )


def parse_skip_flags(messages: str) -> tuple[bool, set[str]]:
    """Return (skip_all, named_skips).

    `[skip-agent-docs]` (no body) → skip_all=True.
    `[skip-agent-docs: a, b]` → named_skips includes a and b.
    """
    skip_all = False
    named: set[str] = set()
    for m in re.finditer(r"\[skip-agent-docs(?::\s*([^\]]+))?\]", messages):
        body = (m.group(1) or "").strip()
        if not body:
            skip_all = True
        else:
            for part in re.split(r"[,\s]+", body):
                part = part.strip()
                if part:
                    named.add(part)
    return skip_all, named


def map_path_to_domain(path: str, mapping: dict[str, list[str]]) -> str | None:
    """Map a changed file path to its domain.

    A root in domain-paths.json is either an exact file
    (e.g. `backend/app/services/ai_service.py`) or a directory
    (e.g. `backend/app`). Directory roots match by path SEGMENT, never by
    raw string prefix — so the root `backend/app` matches `backend/app/x.py`
    but NOT `backend/application/x.py`. Roots may be stored with or without a
    trailing slash; both behave identically.
    """
    for domain, roots in mapping.items():
        for root in roots:
            if not root:
                continue
            r = root.rstrip("/")
            # exact file root
            if path == r:
                return domain
            # directory root: segment-aware prefix
            if path.startswith(r + "/"):
                return domain
    return None


def is_ignored(path: str) -> bool:
    return any(p.match(path) for p in IGNORE_PATTERNS)


def main() -> int:
    parser = argparse.ArgumentParser(description="agent-docs freshness gate")
    parser.add_argument(
        "--base",
        default="HEAD~1",
        help="Base ref to diff against (default: HEAD~1)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print per-file mapping decisions",
    )
    args = parser.parse_args()

    dp_file = META_DIR / "domain-paths.json"
    if not dp_file.exists():
        print(
            f"[agent-docs-gate] WARN: {dp_file.relative_to(REPO)} missing — skipping gate.\n"
            "  Run the context-map skill (`decompose` / `generate --layer nav`) to set up the docs.",
            file=sys.stderr,
        )
        return 0

    try:
        mapping = json.loads(dp_file.read_text())
    except json.JSONDecodeError as e:
        print(f"[agent-docs-gate] ERROR: {dp_file.name} is not valid JSON: {e}", file=sys.stderr)
        return 2

    files = changed_files(args.base)
    msgs = commit_messages(args.base)
    skip_all, named_skips = parse_skip_flags(msgs)

    code_domains_touched: set[str] = set()
    doc_domains_touched: set[str] = set()

    for path in files:
        if args.verbose:
            print(f"  scan: {path}", file=sys.stderr)
        m = re.match(r"agent-docs/domains/([\w-]+)\.md$", path)
        if m:
            doc_domains_touched.add(m.group(1))
            continue
        if is_ignored(path):
            if args.verbose:
                print("    -> ignored by pattern", file=sys.stderr)
            continue
        domain = map_path_to_domain(path, mapping)
        if domain is not None:
            code_domains_touched.add(domain)
            if args.verbose:
                print(f"    -> domain: {domain}", file=sys.stderr)

    needs_update = code_domains_touched - doc_domains_touched
    if skip_all:
        if needs_update:
            print(
                f"[agent-docs-gate] OK: skipped via [skip-agent-docs]: "
                f"{', '.join(sorted(needs_update))}",
                file=sys.stderr,
            )
        return 0
    needs_update -= named_skips

    if not needs_update:
        if args.verbose:
            print("[agent-docs-gate] OK: docs in sync with code.", file=sys.stderr)
        return 0

    sorted_needs = sorted(needs_update)
    print(
        f"\n[agent-docs-gate] FAIL: domain doc updates missing for: "
        f"{', '.join(sorted_needs)}\n",
        file=sys.stderr,
    )
    print("To fix, choose ONE:", file=sys.stderr)
    print(
        f"  1. Run the context-map skill: `update {' '.join(sorted_needs)}`",
        file=sys.stderr,
    )
    print("     (then stage and commit the updated docs)\n", file=sys.stderr)
    print(
        "  2. If the change is genuinely trivial (typo, comment, formatting,",
        file=sys.stderr,
    )
    print(
        "     test-only, lockfile, generated file): add to any commit message",
        file=sys.stderr,
    )
    print(
        "     in this change set:",
        file=sys.stderr,
    )
    print(
        f"       [skip-agent-docs: {','.join(sorted_needs)}]",
        file=sys.stderr,
    )
    print(
        "     Or `[skip-agent-docs]` to skip all touched domains.\n",
        file=sys.stderr,
    )
    print(
        "  Read agent-docs/MAP.md for navigation; root CLAUDE.md documents",
        file=sys.stderr,
    )
    print("  when skipping is appropriate.\n", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
