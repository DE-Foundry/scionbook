# Scionbook project instructions

Follow AGENTS.md, standards.md, and SCIONBOOK_INSTRUCTIONS.md in this repository.
Use the role-specific and specialist workflows in .agents/skills/. Personal configuration is in
scionbook.json; local state is initialized by the setup skill. Never embed player state in this file.
If the client does not support `$skill` invocation, read the corresponding SKILL.md and follow it.
Keep Session Planner read-only and Repository Maintainer in a separate chat with write permissions.
