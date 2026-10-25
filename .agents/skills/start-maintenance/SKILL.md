---
name: start-maintenance
description: Begin explicit Scionbook code, skill, test, or shared documentation maintenance. Personal saves and refreshes are also available in the ongoing player conversation.
---

# Start maintenance

Read AGENTS.md and standards.md. Load only code and sources relevant to the actual request. Use this
conversation and local project files; never read other chats, global memories, or session storage.
A separate development conversation is optional and recommended for substantial application work,
not required for setup, sync, preferences, or progress saves. An invocation does not clear context.

Handle explicitly requested application changes within scope. Never put player identity, preferences,
workspace paths, or reports into shared source, examples, fixtures, or Git history. Development tests use
synthetic data. User-authorized checks with real data stay local and out of the permanent test suite.
Use [save-state](../save-state/SKILL.md) for explicit local reports/preferences, [apply-recap](../apply-recap/SKILL.md)
for a supplied recap, and [sync](../sync/SKILL.md) only for a requested refresh. No automatic commit/push.

If startup has no task, briefly identify available maintenance actions without starting gameplay or sync.
If the user explicitly asks to return to play, [start-session](../start-session/SKILL.md) can reload sources
in this conversation. Do not claim a context reset or require a new chat.
