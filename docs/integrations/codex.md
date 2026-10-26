# Optional Codex integration

Scionbook works through [portable workflows](../assistant-setup.md). Codex-specific configuration and
launchers are conveniences; ordinary use does not require a new-chat API, draft link, or CLI handoff.
Use the user's configured model. .codex/config.toml disables automatic/global memory and subagents.

## Interactive launchers

Run in a user-accessible terminal with Bash and Codex CLI:

```bash
bash scripts/scionbook-chat session
bash scripts/scionbook-chat maintainer
```

Both request workspace-write/on-request. The Session Planner now saves local preferences/progress and
can run requested syncs. Maintainer handles explicit application work. Normal host approval controls
remain active; no permission bypass is used. Existing read-only chats need the host's normal write
permission change for saving, not a role handoff. If that is unavailable, disclose unsaved changes.
Claude Code mappings are in [CLAUDE.md](../../CLAUDE.md).

## Same-chat persistence

Use [save-state](../../.agents/skills/save-state/SKILL.md) and scionbook_state.py. Prepare an original
snapshot before composing an edit; apply the proposal through stdin, then verify the receipt. This
calls no model or external service. It changes only permitted local player files and checks Git privacy.
The host still has its configured filesystem permissions; the helper is not a sandbox for other tools.

## Optional desktop drafts and legacy CLI

The existing `codex://threads/new` adapter accepts a URL-encoded local path and startup prompt.
Generate a draft only when the user wants another chat:

```bash
python3 scionbook_handoff.py draft --role session
python3 scionbook_handoff.py draft --role maintainer
python3 scionbook_handoff.py draft --role apply
```

The user selects workspace-write and presses Send. Apply drafts require the actual recap pasted after
the label. No permission or auto-submit query parameters are provided; the link does not save anything.
After applying a recap the conversation can continue; no follow-up draft is required. Never put player
reports or credentials in URLs. Local paths in generated links stay conversational, never shared source.

The optional `scionbook_handoff.py recap --confirmed` CLI still performs an isolated proposal, verified
save, and separate Maintainer launch for users choosing that legacy route. It requires a user-accessible
terminal and explicit launch approval. Proposal processes retain their restricted read-only settings;
only normal interactive player sessions gain write access. See [continuation guidance](../chat-handoffs.md)
and [instruction security](../instruction-security.md) for boundaries and recovery.
