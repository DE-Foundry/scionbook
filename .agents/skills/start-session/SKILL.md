---
name: start-session
description: Start or resume the ongoing Scionbook player conversation, load saved state, check freshness and resets, and plan gameplay. Preferences and confirmed reports save locally without a handoff.
---

# Start or resume play

Read root AGENTS.md, standards.md, and [preference rules](../../../docs/gameplay-preferences.md).
Use the current conversation, including after setup, sync, or local saves. Do not require a new chat,
retrieve another transcript, use global memories, or treat this invocation as a context reset.

Read scionbook.json first, then status.json (fetched_at_utc, notes, still_not_available),
SCIONBOOK_INSTRUCTIONS.md, SCIONBOOK_MEMORY.md, SCIONBOOK_DAILY_WEEKLY_CHECKLIST.md, and available
quest_history.md. Missing configuration/initial files routes to [setup](../setup/SKILL.md) here when
supported. A new public setup has no private history; retained full-mode history is historical only.
Unknown data never establishes zero balances or no progress.

- Use `Session YYYY-MM-DD` in the configured timezone, without changing chat titles. Preserve newer
  conversation reports and dated saved outcomes; do not duplicate them when resuming.
- State actual snapshot age and material gaps. A stale snapshot alone does not authorize sync. A user
  refresh request invokes [sync](../sync/SKILL.md) here, then reloads local files and continues play.
  Avoid precise transactions from invalidated balances/holdings. Do not request credentials in chat.
- Verify current daily/weekly reset rules from authoritative sources and compare reset boundaries with
  dated completions. A local date change alone does not establish a reset. Ask about unknown availability
  only when it affects the plan. Do not hardcode reset times into reusable routines.
- Apply saved priorities, platform/input, spoiler tolerance, and session-only choices. Offer one feasible
  primary objective, useful setup, one or two relevant detours, and a stopping point. Ask about time only
  when it materially changes the plan. Only unlocked activities are immediately runnable.
- Use specialists when relevant; verify patch-sensitive mechanics and rewards. A queue, accepted quest,
  proposed purchase, or unlocked Savage duty is not a clear. Keep routines and longer progression distinct.
- Clear durable preferences and confirmed progress use [save-state](../save-state/SKILL.md) immediately.
  Discussion can explore possibilities without saving a decision. Use [tasks](../tasks/SKILL.md) for
  reports/next actions and [recap-session](../recap-session/SKILL.md) for a requested summary.

Local read/write access supports normal play. If the host only allows reading/uploaded files, continue
supported discussion and identify unsaved changes; do not pretend a write succeeded or require a handoff.
