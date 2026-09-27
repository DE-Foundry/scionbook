# Scionbook Project Instructions

## Project memory

This project does not use asks.md or decisions.md. Do not create either file or prompt to log requests.
Shared conventions live in standards.md. Personal configuration and preferences live in scionbook.json;
player reports live in SCIONBOOK_MEMORY.md and SCIONBOOK_DAILY_WEEKLY_CHECKLIST.md.
Personal files are local and ignored by Git; templates contain no player state.

## Assistant portability

These instructions apply to any assistant. Read workflows directly from `.agents/skills/<name>/SKILL.md`;
`$name` is optional client shorthand. Natural-language requests to follow the named workflow select the
same role. See docs/assistant-setup.md for capabilities and manual file provision. Never assume native
skill discovery, shell access, a new-chat API, or another client's permission settings.

## Independent chat roles

Choose the role from an explicit request or entry skill. `$start-session` selects Session Planner;
`$setup`, `$start-maintenance`, `$sync`, `$apply-recap`, or repository work selects Repository Maintainer
in a fresh chat. Keep the established role. Direct the other role's work to a separate chat.
Editing skill files is maintenance, not invocation.

Use only this conversation and repository files. Never read another chat transcript, search session
storage, use global memories, contact existing role chats, or spawn the other role as a subagent.
User-confirmed handoffs may launch isolated top-level runs/new chats under docs/chat-handoffs.md.
Only the approved recap crosses into apply-recap; subsequent startup contexts receive no old transcript.

### Session Planner

Read scionbook.json plus status.json, SCIONBOOK_INSTRUCTIONS.md, SCIONBOOK_MEMORY.md,
SCIONBOOK_DAILY_WEEKLY_CHECKLIST.md, and quest_history.md. Read standards.md for shared conventions.
If configuration or initial sources are missing, direct the user to `$setup` in the Maintainer chat.
Public mode has no private quest history; unavailable data is unknown, never empty progress.

Track new reports only in this conversation. Never directly write files, scrape, run setup/sync, apply
recaps in this chat, commit, push, or request write escalation. `$recap-session` first outputs text, then
provides the manual handoff from docs/chat-handoffs.md. Optional automation requires explicit Yes for
the supported route: an app draft the user submits, or an isolated apply-recap followed by a fresh
start-maintenance. The apply destination verifies the save; a prepared prompt or draft is neither a save
nor a started workflow.
This exception does not change the Session Planner's role/permissions. If runtime blocks the transport,
provide the manual handoff rather than bypassing the sandbox. No automated action on No or silence.
Use `Session YYYY-MM-DD` in the configured timezone; do not manage chat titles.
When stale, state the actual snapshot age and request Maintainer sync. Preserve newer conversation
reports when refreshed files are loaded; do not use stale balances for precise transactions.

### Repository Maintainer

Handle code, skills, setup, data questions, refreshes, and explicitly supplied recap saves.
Do not start gameplay planning automatically. Apply gameplay reports only from a user-supplied recap;
never infer unreported outcomes or hand-edit generated status/history to represent a report.
Keep dated outcomes separate from reusable routine boxes. Version edited memory and shared instructions.
A prose save never advances a scrape timestamp. Setup authorizes its initial refresh; subsequent sync
requires an explicit request. Applying a recap alone does not authorize sync.
After successful sync and reconciliation, check available handoff transport before offering a new session.
In the Codex desktop app, an optional documented draft link can prefill start-session; disclose that the user must select
read-only and press Send. Offer full launch only when supported. Follow docs/chat-handoffs.md; use explicit
Yes for transitions and never claim a draft started the skill or the current context was cleared.

There is no standing commit/push authorization. Personal data stays local by default. Only configure
private Git backup when explicitly requested; never force-add ignored data during ordinary sync.
Report local saves, refreshes, commits, and verified pushes separately.

## Skills and runtime

Skills live in .agents/skills/. Core: setup, start-maintenance, sync, apply-recap, start-session,
tasks, recap-session. Specialists: inventory-cleanup, market-update, gear-planner, hunt-planner.
Specialist analysis works in either role without changing that role's write permissions.

Use read-only file access for Session Planner and repository read/write access for Maintainer, enforced
by the chosen client's permission controls. Disable cross-chat memory/retrieval where supported; never
use it for these workflows. Instructions do not change a chat's permissions or context. Use the user's
chosen assistant and model. The optional Codex config and `scripts/scionbook-chat` launcher apply only
to Codex; see docs/integrations/codex.md. Manual prompts and handoffs work without those adapters.
