# Use Scionbook with your assistant

Scionbook's Python tools fetch and process game data without calling an AI model. Its workflows are
Markdown files in `.agents/skills/`; the directory name does not require a particular client. You choose
the assistant and model. There is no model API dependency or Scionbook AI account to configure.

## Capabilities

| Task | Required access |
|---|---|
| Plan a session or produce a recap | Read the shared instructions and saved player sources; retain this chat's reports |
| Setup or sync | Read/write local files, execute Python, access the game-data services; full mode also needs locally supplied credentials |
| Apply a recap | Read/write local files and verify the saved result; no scrape or credentials needed |
| Verify current mechanics or prices | Public web/API access, or current references supplied by the user |

Give Session Planner read-only file access. Give Repository Maintainer write access in a separate chat.
Use the client's actual permission controls; a prompt cannot enforce them. Disable cross-chat memory or
retrieval for these chats where available. Do not load other conversations. If a client cannot isolate
context or restrict tools appropriately, use a fresh chat with manually supplied files and no write tools.

An assistant with uploads but no filesystem can plan from supplied files and prepare a recap. It cannot
execute setup/sync or verify local saves. Use a local-capable assistant or perform the documented steps
manually for those tasks, and supply the resulting files. When browsing is unavailable, identify which
current facts remain unverified; do not substitute remembered prices or patch details.

## First use

1. Install Python dependencies using the [README](../README.md#get-started).
2. Open a fresh Maintainer chat with this repository available. Paste:

   ```text
   Read AGENTS.md, standards.md, and SCIONBOOK_INSTRUCTIONS.md.
   Follow .agents/skills/setup/SKILL.md to set up [Character Name] on [Home World].
   ```

3. Complete setup and the initial validated refresh. Open a separate read-only chat and paste:

   ```text
   Read AGENTS.md and follow .agents/skills/start-session/SKILL.md.
   ```

If the assistant does not automatically discover AGENTS.md, explicitly provide it and each referenced
file it needs. File-upload clients need scionbook.json, status.json, SCIONBOOK_INSTRUCTIONS.md,
SCIONBOOK_MEMORY.md, SCIONBOOK_DAILY_WEEKLY_CHECKLIST.md, standards.md, and quest_history.md when
available, plus the requested workflow and its referenced guidance. Missing data remains unknown.
Refresh uploaded copies when the local sources change. Share player files only with a provider you choose;
never upload credentials, raw authenticated page dumps, or the repository's `.git` directory.

## Choose a workflow

Use `Read .agents/skills/<name>/SKILL.md and follow it: <your request>` for any workflow in the
[skill guide](skills.md). For example:

```text
Read .agents/skills/market-update/SKILL.md and follow it to review my listings.
```

`$market-update` and other `$name` examples are shorthand for clients with native skill discovery, not
portable commands. A skill is an instruction document, not an installed executable. Follow linked files
only as needed. Every client uses the same role, source-fidelity, consent, and save-verification rules.

Use the [manual handoff](chat-handoffs.md) to move between chats. Optional [Codex adapters](integrations/codex.md)
provide convenience only. `CLAUDE_PROJECT_CUSTOM_INSTRUCTIONS.md` is also a small optional instruction
pointer; it does not grant filesystem access or establish tested compatibility with every Claude client.
Other clients can use the prompts above without a new adapter. Compatibility is capability-based; this
repository does not claim end-to-end testing of every AI provider.
