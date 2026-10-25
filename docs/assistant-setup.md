# Use Scionbook with your assistant

Scionbook's Python tools fetch/process game data and verify local saves without an AI-provider SDK or
model API key. Workflows are Markdown in .agents/skills/. Choose your assistant and model; native skill
discovery is optional. Read a workflow directly and follow its linked guidance when needed.

## Capabilities

| Task | Required access |
|---|---|
| Discuss options or plan play | Read saved sources and retain this conversation's reports |
| Save preferences or confirmed progress | Local read/write access and Python for validated saves |
| Setup or explicitly requested sync | Local read/write, Python, network; full mode also needs local credentials |
| Verify current mechanics/prices | Public web/API access or current references provided by the user |
| Change application behavior | Explicit development request and shared-source write access |

Use one ongoing player conversation with local read/write access. It can set up, sync, plan, discuss,
and save reports/preferences without changing chats. Real host permissions still apply; a prompt does
not enforce a filesystem allowlist. The player-state helper enforces its own permitted destinations,
checks that those destinations/staging are ignored in Git checkouts, and verifies saves.

Read-only/upload-only clients can discuss and prepare proposed changes, but must say those changes are
unsaved. The user can apply them with a local-capable assistant or the documented manual/helper route,
then provide the resulting files. Never claim local persistence or a refresh from an uploaded proposal.
Missing tools do not automatically require a new chat or authorize a sandbox bypass.

Disable cross-chat memory/retrieval where supported. Use this conversation and local sources only;
never search chat storage or import another transcript. Application development may use a separate
maintenance conversation for focus, but ordinary saves and syncs do not depend on it.

## First use and continuation

Install Python dependencies using [Get started](../README.md#get-started), then send:

```text
Read AGENTS.md and follow .agents/skills/setup/SKILL.md for [Character Name] on [Home World].
```

After its first validated sync, continue playing in that conversation. Existing setups can send:

```text
Read AGENTS.md and follow .agents/skills/start-session/SKILL.md.
```

Clear durable preferences and confirmed reports save when supplied. Exploratory discussion and temporary
choices remain distinct. Later syncs require an explicit request, reload installed sources, and reconcile
current advice while preserving newer reports. A new chat is optional when you want a fresh context.

File-upload clients need configuration, status, shared instructions, local memory/checklist, standards,
and available quest history plus the requested workflow. Refresh uploads after local changes. Share
player data only with a provider you authorize; never upload credentials, raw authenticated HTML, or .git.
When browsing is unavailable, identify unverified current facts rather than substituting remembered prices.

See [skills](skills.md), [optional continuation tools](chat-handoffs.md), [Codex](integrations/codex.md),
and [Claude Code](../CLAUDE.md). These adapters do not establish universal client compatibility.
