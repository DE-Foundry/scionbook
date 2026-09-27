---
name: tasks
description: Track FFXIV session completions and gameplay progress only in the Session Planner conversation, show remaining tasks, and recommend what to do next. Does not save repository files.
---

# Tasks

Follow the Session Planner boundary in root AGENTS.md. Use the five source files loaded by [start-session](../start-session/SKILL.md), re-reading relevant sections when needed. Consult available quest_history.md for dated unlock evidence; a new public setup has none. Current conversation reports override older readings without making the scrape fresh. In a Maintainer chat, direct gameplay tracking to a separate Session Planner chat.

When the player reports progress:

- Keep a dated in-conversation record of confirmed completions, levels, gear/purchases, unlocks, preferences, corrections, and pending outcomes. Use the reported session date and known reset-cycle context. Merge repeated reports without duplicating them.
- Only mark what was reported. A duty clear does not prove its roulette, a proposed batch is not completed, and a 9/9 book is not necessarily handed in. Record unambiguous facts first; clarify only when the ambiguity affects the plan.
- After major inventory cleanup, treat the preceding inventory/listing plan as historical and identify the need for Maintainer sync. Do not infer sales or funds from absent items.
- Do not modify files, invoke sync/apply-recap, or request write permission. Say "tracked for this session" rather than "saved". Keep the combined worth-saving list silent until requested.

For next actions, check current reset state as in start-session; never carry completions across a reset or assume weekly eligibility. Give one best action with a brief reason, at most a couple of useful alternatives, and verified patch-sensitive facts. Keep recommendations separate from completed work. A question about what is next does not establish a completion.

Acknowledge the report briefly and continue gameplay guidance. [recap-session](../recap-session/SKILL.md) produces the eventual handoff from this conversation; it does not directly write files and offers the confirmed app-draft or supported isolated-apply handoff.
