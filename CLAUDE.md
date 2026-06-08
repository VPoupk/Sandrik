# Claude Code System Rules — Sandrik

## 1. Background Process Tracking

Any Bash command run with `run_in_background=true` is automatically logged to
`pipeline/logs/bg_procs.log` via the PostToolUse hook in `.claude/settings.json`.

**Rules:**
- Always check `pipeline/logs/bg_procs.log` at session start to see what was running in the previous session.
- Before launching a new background scan, check if the same job is already listed and still alive (`kill -0 <pid>`).
- After a session ends with active background processes, note the relevant log entry in chat so the next session can pick up where it left off.
- Never launch a background pipeline and abandon it — always confirm it completed or was killed before ending the session.

## 2. Multi-Session Scan Checkpointing

Any scan / pipeline that processes more than one RPC chunk (>50k blocks) MUST be resumable.

**Required checkpoint pattern:**
```
pipeline/data/{job_name}_checkpoint.json
{
  "job":            "<name>",
  "last_block":     <int>,
  "total_blocks":   <int>,
  "chunks_done":    <int>,
  "results":        {...},   // accumulated data so far
  "timestamp":      "<ISO>"
}
```

**Rules:**
- Write checkpoint after **every chunk** (50k blocks), not just at the end.
- On startup, check for an existing checkpoint and resume from `last_block + 1` if found.
- Never delete a checkpoint until the results have been manually confirmed and committed.
- If a session ends mid-scan: commit the checkpoint file to git before the session ends, with message prefix `[checkpoint]`.

## 3. No Auto-Apply to HTML or Auto-Commit

Scripts in `pipeline/` may **only** write to `pipeline/data/*.json` and `pipeline/logs/*.log`.

**Prohibited in any automated script:**
- Editing `ake-analysis.html`, `pool-outflows.html`, `insider-outflows.html`
- Running `git add`, `git commit`, `git push`, `git reset`
- Overwriting files outside `pipeline/`

All HTML edits and git commits require an explicit instruction from the user in chat.

## 4. Session-Start Checklist

At the start of any session where on-chain scanning may be involved:

1. Run `cat pipeline/logs/bg_procs.log 2>/dev/null | tail -20` to see recent background activity.
2. Check `pipeline/data/*_checkpoint.json` for in-progress scans.
3. Check `pipeline/data/status.json` for pipeline state.
4. Confirm `.claude/settings.json` has no `SessionStart` hook (only `PostToolUse` hook is allowed).
5. Neutralize any unexpected scripts in `/tmp/*.sh` with `exit 0` body before running anything.

## 5. Pipeline Lock File

Before starting any long-running scan:
```bash
echo "$(date -Iseconds) <job_name>" > /tmp/pipeline_running.lock
```
Remove it on clean completion. If the lock file exists at session start, treat it as evidence the last scan was interrupted and check the checkpoint before resuming.

## 6. Irreversibility Guard

Before any action that modifies shared state (HTML files, git history, external APIs):
- State the intended change and target file/branch explicitly in chat.
- Wait for user confirmation unless the user has already given explicit permission in this same session turn.
- Never use `--force`, `--no-verify`, or `reset --hard` without naming the commit SHA being discarded.
