---
name: start-session
description: Start or resume the read-only Scionbook Session Planner, load the five saved sources, check freshness and resets, and plan gameplay. Keeps all new progress in this conversation.
---

# Start session

Read root AGENTS.md and standards.md. Establish the Session Planner role in a fresh gameplay chat; if this is an established Maintainer chat, direct the user to a separate session chat instead. Never write files, run sync/scrapers, request write escalation, or communicate with another agent except the user-confirmed recap transport defined in docs/chat-handoffs.md.

A confirmed post-sync launch must be a new context, not a continuation/fork of the Maintainer transcript. Load all sources anew; do not import maintenance messages or credentials. Invoking this skill inside the old chat is not a context reset.

Read scionbook.json first. If missing, direct setup to a Maintainer chat; do not invent a character.

Read status.json (fetched_at_utc, notes, and still_not_available first), SCIONBOOK_INSTRUCTIONS.md, SCIONBOOK_MEMORY.md, SCIONBOOK_DAILY_WEEKLY_CHECKLIST.md, and quest_history.md. A new public setup has no private quest_history.md; a checkout switched from full to public may retain an older history, which is historical only. Neither case establishes current private completion. If status.json or the local memory/checklist files are missing, direct completion of setup to Maintainer.

These sources plus this conversation are the session's context; do not read other chat histories or global memories.

- Label the session `Session YYYY-MM-DD` using the timezone in scionbook.json. Only the session name is needed; do not change the chat title or mention title controls. Resume same-day outcomes already in this conversation or the source files without duplicating them.
- Reconcile newer player reports with the actual snapshot date. If today's refresh is missing or a substantial inventory cleanup invalidates it, identify the source age and direct the user to `$sync` in the Maintainer chat. Continue with supported advice only, avoiding precise transactions from stale balances/inventories. Do not request scraper credentials. If the user reports that sync is ready, reload the five files without discarding newer in-conversation reports.
- Check the clock and verify applicable daily/weekly reset rules from current authoritative sources. Compare reset boundaries with dated completions; a local date change alone does not prove a reset. Keep ambiguous availability unknown and ask only when it affects the plan. Do not hardcode reset times into the reusable checklist.
- Briefly state progression, what has reset, outstanding follow-ups, and one primary objective. Include useful setup, one or two relevant detours matching the player's goals, and a stopping point. Ask about time only when it materially changes the plan; avoid dumping the full checklist.
- Apply configured spoiler, platform, input, and goal preferences. Load inventory-cleanup, market-update, gear-planner, or hunt-planner only when relevant. Verify patch-sensitive mechanics/rewards. Do not browse character databases as a substitute for the snapshot.
- Offer only unlocked tasks as immediately runnable. Accepted quests, queues, proposed purchases, and unlocked Savage duties are not clears. Keep daily chores, weekly rewards, and longer progression distinct.

Use [tasks](../tasks/SKILL.md) for in-conversation progress and next actions. Use [recap-session](../recap-session/SKILL.md) when asked for the combined worth-saving recap. Tasks never saves files; recap-session can offer a confirmed isolated apply handoff but never directly edits gameplay files. Do not emit running worth-saving summaries.
