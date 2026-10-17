@AGENTS.md

## Claude Code

The shared instructions above apply unchanged. Client-specific mapping:

- Skills: `.claude/skills` links to `.agents/skills`, so `$start-session` in these docs is
  `/start-session` here. If the link is unavailable (for example a Windows checkout without symlinks),
  read the named `.agents/skills/<name>/SKILL.md` and follow it.
- Roles: `SCIONBOOK_CLIENT=claude bash scripts/scionbook-chat session|maintainer` starts a fresh chat.
  Session Planner runs with only read tools allowed; Maintainer keeps normal write approval prompts.
- `.claude/settings.json` disables auto memory and subagents, matching `.codex/config.toml`.
- Desktop draft links (`scionbook_handoff.py draft`) are Codex-app deep links. In Claude Code, use the
  CLI handoff with `--client claude` or the manual steps in docs/chat-handoffs.md.
