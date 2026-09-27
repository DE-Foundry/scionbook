# Optional Codex integration

Scionbook does not require Codex. Use the [portable workflow](../assistant-setup.md) with any
assistant that meets its capability requirements. This page documents the existing Codex adapter;
these commands and URL schemes are not instructions for other clients.

Codex-specific files are `.codex/config.toml`, `scripts/scionbook-chat`, and the `draft`, `recap`,
and `session` actions in `scionbook_handoff.py`. The project config disables automatic memory and
multi-agent tools for new trusted chats; it does not configure another assistant or change an existing chat.
Use the user's configured model. The interactive launchers require Bash and Codex CLI:

```bash
bash scripts/scionbook-chat session
bash scripts/scionbook-chat maintainer
```

Run these in a user-accessible terminal. The Session launcher requests read-only/never permissions;
Maintainer requests workspace-write/on-request. Native `$skill-name` invocation is optional shorthand.
Follow the [shared handoff contract](../chat-handoffs.md) for consent and save verification.

## Codex desktop draft links

The documented `codex://threads/new` link accepts URL-encoded `path` (absolute repository directory) and
`prompt` (initial composer text). Generate the exact URL without opening a terminal or starting an agent:

```bash
python3 scionbook_handoff.py draft --role session
python3 scionbook_handoff.py draft --role maintainer
python3 scionbook_handoff.py draft --role apply
```

Present the returned URL as a clickable Markdown link, e.g. **Open Session Planner**. On click, the app
opens a fresh chat composer in that repository. The user selects read-only for Session or workspace-write
for Maintainer and presses Send. These query parameters do not set runtime permissions or send the prompt;
do not invent `sandbox` or auto-submit parameters. A prompt is not permission enforcement.
Do not substitute a hidden PTY or report a prepared link as a launched/running session. The exact skill
spelling is `$start-session`, with no space after `$`. Native app controls need not be exposed to offer a link.

After sync, use the session draft. For recap, the apply draft prefills instructions for applying the recap
and producing the post-save Maintainer link, plus a “Recap to apply:” label. The user must paste the displayed
recap there; the label alone is not content to save. Opening the draft does not apply anything. Only the
Apply Recap chat, after verifying the save, provides the maintainer draft. Keep recap
contents out of URLs and process arguments. A supported isolated apply transport may still automate the save,
but a draft follow-up requires Send and must be described accordingly.

[Official desktop deep-link documentation](https://learn.chatgpt.com/docs/reference/commands#chats).

## Codex CLI

Use an available, documented host action that creates genuinely new user-visible chats with the correct
repository and permissions. If it can only create a chat but cannot run and verify an isolated apply step,
do not claim the full recap sequence was automated. Never invent a tool, type `/new` as ordinary assistant
text and claim it executed, use `/compact`, fork/resume a chat, or edit session databases.

The CLI helper implements the full sequence in a **user-accessible terminal**:

```bash
# Paste the approved recap and end input with EOF, or pipe the exact text on stdin.
python3 scionbook_handoff.py recap --confirmed

# After a successful sync and explicit Yes:
python3 scionbook_handoff.py session --confirmed
```

`--confirmed` records an answer already received; it does not replace asking. Do not pass recap text as
shell command syntax, interpolate it into an unquoted heredoc, or put it in process arguments. Use structured
stdin transport where available. The helper runs a fresh `codex exec --ephemeral` for apply, checks its
structured success result, then launches a separate interactive Maintainer. It refuses to start without a
terminal, even before apply. No recap is persisted as an intermediate file. Temporary schemas/results live
under ignored `.scionbook-tmp/` and are removed after the run. Durable gameplay saves follow apply-recap.
The apply run uses workspace-write/never and stops if it needs approval or clarification; the follow-up
Maintainer uses workspace-write/on-request. Session uses read-only/never. No sandbox bypass is used.

The Session Planner has a narrow exception to invoke this confirmed handoff transport, subject to runtime
permissions. It may not use that exception to make arbitrary writes or start other work. Never escalate a
read-only session into a writer to bypass a launcher rejection; use the manual path if the host blocks it.
A hidden tool PTY is not a user-facing chat. Do not run an unattended nested interactive CLI from an app tool.

If no supported host action, desktop draft link, or user-accessible CLI transport is available, explain this
before asking for a transition and provide the
exact pending handoff: open a fresh Maintainer chat, submit `$apply-recap` plus the approved recap, and after
it confirms the save open another fresh chat with `$start-maintenance`. After sync, open a fresh read-only
chat and submit `$start-session`. Clearly distinguish prepared, applied, and launched states. This fallback
requires user action; do not say the automatic transition happened.

References: [CLI execution and structured output](https://learn.chatgpt.com/docs/developer-commands?surface=cli),
[separate chats and new CLI sessions](https://learn.chatgpt.com/docs/projects).
