#!/usr/bin/env bash
# context-map · SessionStart memory-staleness notice
#
# Prints a one-line reminder to the session if the project's memory layer
# (context-map-<slug>/) looks stale vs. its last verification date. Cheap,
# read-only, and SILENT when there's nothing to say (no memory folder, or fresh).
#
# It never rewrites memory — surfacing a reminder is the whole job. The
# navigation layer's freshness is handled by the CI gate
# (check_agent_docs_freshness.py), not here.
#
# Threshold via CONTEXT_MAP_STALE_DAYS (default 21).

set -e

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
THRESHOLD_DAYS="${CONTEXT_MAP_STALE_DAYS:-21}"

command -v python3 >/dev/null 2>&1 || exit 0

python3 - "$PROJECT_DIR" "$THRESHOLD_DAYS" <<'PY' 2>/dev/null || true
import sys, glob, os, datetime, re

proj, thr = sys.argv[1], int(sys.argv[2])
folders = [f for f in sorted(glob.glob(os.path.join(proj, "context-map-*")))
           if os.path.isfile(os.path.join(f, "context-map.md"))]
if not folders:
    sys.exit(0)

today = datetime.date.today()
for f in folders:
    try:
        text = open(os.path.join(f, "context-map.md"), encoding="utf-8", errors="ignore").read()
    except OSError:
        continue
    m = re.search(r"^last_verified_vs_code:\s*(\d{4}-\d{2}-\d{2})", text, re.M)
    if not m:
        continue
    try:
        verified = datetime.date.fromisoformat(m.group(1))
    except ValueError:
        continue
    age = (today - verified).days
    if age >= thr:
        slug = os.path.basename(f)[len("context-map-"):]
        print(f"[context-map] {slug}: memory layer last verified {age}d ago "
              f"({m.group(1)}). If the project has moved on, run the context-map "
              f"skill `update --layer memory`.")
PY

exit 0
