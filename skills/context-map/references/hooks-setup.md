# Hooks-based maintenance policy (optional)

Use this when the user chose **Policy B** in Phase 4 — they want enforcement, not just instructions.

This file documents the `settings.json` patch that wires up an automatic reminder when domains are touched in a session. It does **not** auto-rewrite docs — that's still on-demand via `context-map update <domain>`. Silent auto-rewrites would be invasive and error-prone.

## What the hooks do

1. **PostToolUse hook on `Edit` and `Write`**: appends the changed file path to `.agent-docs-changed` in the project root.
2. **Stop hook**: reads `.agent-docs-changed`, maps changed paths to domains (via `agent-docs/_meta/domain-paths.json`), and prints a one-line reminder: *"Touched domains: auth, apps. Run context-map skill: update auth apps to refresh docs."* Then clears `.agent-docs-changed`.

## Files to install

### 1. The PostToolUse and Stop hook scripts

`agent-docs/_meta/hook-record-change.sh`:
```sh
#!/bin/sh
# Append changed file path to .agent-docs-changed
# Invoked by PostToolUse hook on Edit/Write tools.
# $CLAUDE_HOOK_INPUT contains JSON with tool_input.file_path
echo "$CLAUDE_HOOK_INPUT" | python3 -c "
import json, sys, pathlib
data = json.load(sys.stdin)
path = data.get('tool_input', {}).get('file_path', '')
if path:
    record = pathlib.Path('.agent-docs-changed')
    existing = set(record.read_text().splitlines()) if record.exists() else set()
    existing.add(path)
    record.write_text('\n'.join(sorted(existing)) + '\n')
"
```

`agent-docs/_meta/hook-stop-report.sh`:
```sh
#!/bin/sh
# At session end, summarize touched domains and clear the record.
python3 <<'PY'
import json, pathlib
record = pathlib.Path('.agent-docs-changed')
if not record.exists():
    raise SystemExit(0)
paths = [p for p in record.read_text().splitlines() if p.strip()]
domains_file = pathlib.Path('agent-docs/_meta/domain-paths.json')
if not domains_file.exists():
    raise SystemExit(0)
mapping = json.loads(domains_file.read_text())  # { "auth": ["backend/app/auth/"], ... }
touched = set()
for p in paths:
    for domain, roots in mapping.items():
        if any(p.startswith(r) for r in roots):
            touched.add(domain)
if touched:
    names = ' '.join(sorted(touched))
    print(f"\n[agent-docs] Touched domains: {names}. Run context-map skill: update {names} to refresh docs.")
record.unlink()
PY
```

Make both scripts executable: `chmod +x agent-docs/_meta/hook-*.sh`.

### 2. The `domain-paths.json` map

`agent-docs/_meta/domain-paths.json` — emitted at the end of Phase 3 alongside the domain docs:
```json
{
  "auth": ["backend/app/auth/"],
  "apps": ["apps/", "backend/app/apps/"],
  "agent": ["backend/app/agent/"]
}
```

### 3. The `settings.json` patch

Propose this via the `update-config` skill. Show the diff. Do not write directly.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "./agent-docs/_meta/hook-record-change.sh" }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          { "type": "command", "command": "./agent-docs/_meta/hook-stop-report.sh" }
        ]
      }
    ]
  }
}
```

If the user already has hooks for `PostToolUse` or `Stop`, **merge** by appending to the arrays. Do not replace existing hook entries.

## .gitignore

Add `.agent-docs-changed` to `.gitignore`. It's per-session ephemeral state, not project memory.

## Verifying the hooks work

After installing:
1. Edit any file in a known domain root.
2. Type `/exit` or end the session.
3. The Stop hook should print: `[agent-docs] Touched domains: <name>. Run context-map skill: update <name> ...`

If nothing prints:
- Check the script has execute permission.
- Check `agent-docs/_meta/domain-paths.json` exists and includes the touched path.
- Try `bash agent-docs/_meta/hook-stop-report.sh` manually with `.agent-docs-changed` populated.

## Limits and caveats

- Hooks fire per-session, not per-PR. If the user runs many sessions, they'll see many reminders. This is by design — reminders are cheap.
- The mapping is path-prefix only. Files outside any domain root won't trigger a domain reminder.
- The Stop hook output is a reminder, not an automatic action. The user (or agent) still has to invoke `update <domain>` explicitly. This is intentional — silent doc rewrites would be invasive.
