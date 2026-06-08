#!/usr/bin/env python3
"""
PostToolUse hook: called by Claude Code after every Bash tool invocation.
Reads the tool-use JSON from stdin and, if run_in_background=true, appends
an entry to pipeline/logs/bg_procs.log.
"""
import sys, json, datetime, os

try:
    data = json.load(sys.stdin)
    inp = data.get("tool_input", {})
    cmd = str(inp.get("command", "")).strip()
    bg = inp.get("run_in_background", False)
    if bg and cmd:
        ts = datetime.datetime.now().isoformat(timespec="seconds")
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "bg_procs.log"), "a") as f:
            f.write(f"{ts}  BG_LAUNCHED: {cmd[:400]}\n")
except Exception:
    pass  # hook must never fail or block tool use
