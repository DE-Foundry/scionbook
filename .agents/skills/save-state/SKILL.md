---
name: save-state
description: Save clear FFXIV preferences, corrections, and confirmed progress immediately to ignored local player files during an ongoing discussion. Does not refresh character data or change shared application source.
---

# Save local player state

Follow AGENTS.md and [preference rules](../../../docs/gameplay-preferences.md). Use this workflow as
soon as the user clearly establishes a standing preference or reports confirmed progress. No recap,
role change, new chat, or repeated approval is needed. A discussion or tentative suggestion alone is
not a durable change. Session-only choices affect this conversation without replacing the baseline.
If durable intent is unclear, keep discussing and ask only about the ambiguous part.

1. Read current configuration, dated memory/checklist, and relevant snapshot/history evidence. Separate
   player-reported facts, generated facts, pending actions, and standing preferences. Use the configured
   timezone and preserve an explicitly supplied report date. Never infer a purchase, sale, clear, roulette,
   quest completion, or hand-in from a plan, level increase, queue, or disappearance from storage.
2. Before composing an edit, run `python3 scionbook_state.py prepare` from the repository root. It captures
   original sources in ignored .scionbook-state-<token>/ and returns an opaque token. Read the sources
   after preparation; changes since the captured originals will stop installation. Use the virtualenv Python.
3. Compose complete contents for only affected files: scionbook.json (preferences only),
   SCIONBOOK_MEMORY.md, and SCIONBOOK_DAILY_WEEKLY_CHECKLIST.md. Preserve unrelated settings and
   reports. Preferences are the current baseline; memory may retain useful dated history labeled as
   superseded, not a second current preference list. Keep dated completions separate from reusable routines.
   Bump memory version/date only for actual edits. Repeated identical reports produce no changes.
4. Supply a JSON proposal on stdin to `python3 scionbook_state.py apply TOKEN`, or write it with a file
   tool to ignored local/state-update.json and use `python3 scionbook_state.py apply TOKEN < local/state-update.json`.
   Create local/ first if necessary. The shape is `{"status":"proposed","changes":[{"path":"scionbook.json","content":"FULL FILE CONTENTS"}]}`.
   Never interpolate player text into shell syntax or arguments. Do not use tracked files for proposals.
   The helper validates allowed destinations, configuration, controls, concurrent edits, and saved bytes.
   It never calls an AI model, refreshes data, changes identity, or writes shared source. Cancel an unused
   preparation with `python3 scionbook_state.py cancel TOKEN`.
5. Report saved/already saved only after the receipt verifies applied/unchanged. Continue the discussion
   or plan in the same conversation. On conflicts, re-read sources and prepare a new edit; do not overwrite
   newer changes. Interrupted installation journals require [recovery](../../../docs/instruction-security.md#interrupted-saves).
   State the failure and keep unsaved reports visible; never claim persistence from proposed text alone.

If configuration is absent, an explicit gameplay preference can use the ignored pre-setup seed documented
in the preference rules, validated with initial_preferences; never invent identity or completion records.
The helper requires setup configuration. Setup/identity changes and crafting-research files use their
own workflows. The helper's output allowlist does not grant arbitrary writes to local/ or shared source.

If file writes or Python are unavailable, prepare the exact proposed changes for the user and say they
remain unsaved. Manual application must validate configuration and re-read saved files. Never bypass
host permission restrictions. A preference save does not authorize sync, commits, or pushes.
