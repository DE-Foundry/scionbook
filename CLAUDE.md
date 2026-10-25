@AGENTS.md

## Claude Code

The shared instructions apply unchanged. `.claude/skills` links to `.agents/skills` in checkouts and is
materialized in release ZIPs. Use `/skill-name` or read the named SKILL.md directly if discovery is absent.

`SCIONBOOK_CLIENT=claude bash scripts/scionbook-chat session|maintainer` starts an optional fresh chat.
Both keep normal client write approval controls. Player sessions save ignored preferences/progress and
run explicitly requested setup/sync in the same conversation; no mandatory handoff or read-only role.
`.claude/settings.json` disables automatic memory and subagents. The legacy isolated recap proposal
retains its tool restrictions; interactive player permissions do not broaden that proposal process.

Codex desktop draft links are specific to Codex. See docs/chat-handoffs.md for optional portable prompts
and legacy CLI routes; ordinary play uses direct local saves without another chat.
