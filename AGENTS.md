# Scionbook Project Instructions

## Shared source and private state

This project does not use asks.md or decisions.md. Do not create either or prompt to log requests.
Shared conventions live in standards.md. Character identity, preferences, progress, and workspace-specific
settings belong only in ignored local files, never shared instructions, skills, templates, fixtures,
branches, commit metadata, release assets, or repository history. This includes private forks.
One character per checkout; no invented identity. Personal files stay ignored; templates stay neutral.

## One ongoing player conversation

Setup, sync, discussion, planning, and local saves can all happen in the same conversation. Setup's first
validated sync makes that conversation ready for play; do not require or offer a chat handoff after every
save or refresh. A new chat is optional when the user wants one. It reloads durable local sources.
Starting another skill, reloading files, or compacting does not clear the existing conversation.

Read scionbook.json plus status.json, SCIONBOOK_INSTRUCTIONS.md, SCIONBOOK_MEMORY.md,
SCIONBOOK_DAILY_WEEKLY_CHECKLIST.md, and available quest_history.md for gameplay. Read standards.md.
Check fetched_at_utc, notes, and still_not_available before character-dependent advice. Missing private
history in public mode is unknown progress, not an empty completion list. Missing configuration or
initial sources routes to setup in this conversation when the host supports it.

Use only this conversation and local project files. Never read another chat transcript, search session
storage, use global memories, contact existing chats, or spawn another role as a subagent.
Use `Session YYYY-MM-DD` in the configured timezone; do not manage chat titles.

## Immediate local persistence

Follow docs/gameplay-preferences.md and .agents/skills/save-state/SKILL.md. Clear standing preferences,
corrections, and confirmed player reports authorize an immediate verified local save. Do not defer them
to a recap or ask the user to repeat an unambiguous instruction. Discussions, tentative ideas, proposed
actions, and session-only choices do not establish durable decisions or completions. Ask only when
scope or intent materially affects what would be saved; continue useful discussion meanwhile.

Current preferences live in scionbook.json; memory is dated evidence/history, not a competing preference
database. Preserve unrelated settings and distinguish durable preferences, temporary choices, proposed
actions, and completed outcomes. Missing configuration uses the documented ignored pre-setup seed.
Record dated outcomes separately from reusable routine boxes. Version edited memory/shared instructions.
Never hand-edit generated status.json or quest_history.md to represent reports or advance scrape times.
Re-read saved bytes before claiming a save. Repeated identical reports are no-ops.

## Refresh and reconciliation

Follow .agents/skills/sync/SKILL.md only for an explicit refresh request or setup's initial refresh.
A report save, changed preference, old snapshot, or recap mentioning sync does not authorize a scrape.
Fetch and validate first, reconcile evidence separately, then reload installed local sources in the same
conversation. Preserve newer player reports: a newer fetch can still contain lagging game data.
State actual snapshot age; avoid precise transactions from invalidated holdings or balances.

Assume full pricing for authenticated refreshes unless the user chooses otherwise. Check market
eligibility and known vendor sale value before market requests. Failed batches shrink toward one item.
If failures persist, let the user choose retry, smaller batches down to one, or ignore remaining pricing
failures for this run with gaps disclosed. Never silently reduce coverage for speed or change a standing
preference from a one-run choice. Ignoring prices does not waive authentication or history validation.

## Application maintenance

Repository Maintainer is a purpose for explicit code, skill, test, and shared documentation work, not a
required gateway for personal saves or refreshes. A separate maintenance chat is optional; do not start
gameplay planning automatically when the user requested development. Editing a skill is maintenance,
not invocation. Player discussion must never silently modify application behavior or shared source.

There is no standing commit/push authorization. Never force-add player data or configure Git backups.
Before any authorized push, verify this checkout's ignored denylist and local privacy hook under
docs/releasing.md#privacy-before-push. Keep private terms only in ignored local configuration. Never
bypass a blocked push or use dummy terms. The release secret does not replace local protection.
Public GitHub contributor handles and noreply attribution are permitted. Follow docs/releasing.md for
web-merge email privacy; a local hook does not protect server-created commits.
Report local saves, refreshes, commits, and verified pushes separately.

## Skills and runtime

Read workflows directly from .agents/skills/<name>/SKILL.md; `$name` is optional client shorthand.
Core: setup, start-session, tasks, save-state, recap-session, apply-recap, sync, start-maintenance.
Specialists: inventory-cleanup, market-update, gear-planner, hunt-planner. Load only relevant guidance.

The player agent needs local read/write access and Python/network access for requested setup/sync.
Use the selected client's actual permission controls; prompts do not enforce a file allowlist. Prefer the
validated player-state helper for saves. Skills do not bypass host restrictions. With read-only or
upload-only access, discuss/plan and prepare proposed changes, disclose that they are unsaved, and give
manual steps without claiming success. A permission limit does not automatically require another chat.
Disable cross-chat memory/retrieval where supported. Use the user's chosen assistant and model.
Optional client launchers/configuration are documented in docs/assistant-setup.md,
docs/integrations/codex.md, and CLAUDE.md. Optional new-chat tools are never prerequisites for play.
