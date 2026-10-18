---
name: start-maintenance
description: Start the independent Scionbook Repository Maintainer chat for code, skills, instructions, data questions, sync, and applying an explicitly supplied session recap. Does not start gameplay.
---

# Start maintenance

Read root AGENTS.md and standards.md. Establish Repository Maintainer in a fresh chat. If this is an established Session Planner chat, direct the user to a separate Maintainer chat; do not switch roles or inherit gameplay context.

Use this chat and the repository only. Do not read other chats, global memories, or session storage; do not contact an existing Session Planner or spawn it as a subagent. A confirmed post-sync fresh-chat launch follows docs/chat-handoffs.md. Load code and Scionbook sources relevant to the actual request. Read status.json's timestamp, notes, and still_not_available before character-data answers.

Handle code and instruction changes directly within the user's scope. Use [sync](../sync/SKILL.md) for requested scrape/reconciliation work and [apply-recap](../apply-recap/SKILL.md) for gameplay reports explicitly supplied for saving. Do not run a sync merely because the Maintainer was started. Starting this role does not authorize a commit or push.

Explicit personal preference-save requests follow [gameplay preferences](../../../docs/gameplay-preferences.md).
Save durable preferences locally without requiring a gameplay recap or authorizing a refresh.

When started after a successful recap handoff, reload durable local sources as needed. Do not retrieve the previous execution, ask to reapply the recap, or automatically sync. A same-chat invocation never clears context.

If no task accompanies startup, briefly identify the role and available next actions: code/instruction work, `$sync`, or a pasted recap with `$apply-recap`. Do not produce a gameplay session plan.
