---
name: tasks
description: Record confirmed FFXIV progress locally during the ongoing player conversation, show remaining tasks, and recommend next actions. Questions and proposed activities do not establish completion.
---

# Tasks

Follow AGENTS.md and [preference rules](../../../docs/gameplay-preferences.md). Use sources loaded by
[start-session](../start-session/SKILL.md), re-reading relevant evidence and configuration as needed.
Current reports can supersede older readings without making the scrape fresh. No role change is needed.

When the player reports progress:

- Record clear confirmed completions, levels, gear/purchases, unlocks, corrections, and durable preferences
  immediately through [save-state](../save-state/SKILL.md). Preserve the report date/timezone and known
  reset-cycle context. Merge repeated reports without duplicates. Do not require a recap or another chat.
- Only record what was reported: a duty clear does not prove roulette credit, a queue is not a clear, and
  a full book is not a hand-in. Pending outcomes and temporary choices remain separate. Discuss tentative
  ideas freely without turning them into saved standing preferences. Clarify only material ambiguity.
- After significant inventory cleanup, mark prior inventory/listing advice historical. A requested sync
  runs in this conversation; a cleanup report alone does not authorize it. Never infer sales or funds
  from missing items or modify generated snapshot/history to represent player reports.
- Say saved only after verification. If the host cannot write, retain the report in this conversation,
  say it is unsaved, and provide proposed changes/manual steps. Keep summaries concise unless requested.

For next actions, verify reset availability as in start-session and choose one useful action with a brief
reason and at most a couple of alternatives. Asking what is next does not establish a completion.
Acknowledge saved reports briefly and continue. [recap-session](../recap-session/SKILL.md) summarizes the
current session on request; it is not a prerequisite for persistence.
