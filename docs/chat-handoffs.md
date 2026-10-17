# Chat handoffs

The default handoff works by copying a prompt and an approved recap into a fresh chat in any suitable
assistant. No AI client, API key, deep link, or automated launcher is required. Optional integrations must
preserve the same boundaries. See [assistant setup](assistant-setup.md) for capabilities and file access.

A fresh context is a new conversation, not a renamed chat, compaction, fork, resumed thread, or another
workflow invoked in the old transcript. Load repository instructions and local sources afresh. Never read
chat storage or copy an entire transcript. Only the user-approved recap crosses into apply-recap.

## Recap to Maintainer

1. Show the complete recap. Producing a recap does not save it.
2. Provide this prompt for a fresh chat with repository file read/write access, followed by the recap:

   ```text
   Read AGENTS.md and follow .agents/skills/apply-recap/SKILL.md.
   Apply only the recap below. Verify the saved files. Do not sync, commit, or push.

   Recap to apply:
   [Paste the approved recap here.]
   ```

3. The user reviews and submits it. The destination applies and re-reads the saved files, reporting what
   was saved or already applied. Missing recap, partial save, or material ambiguity stops the sequence.
4. After verified success, the user can open another fresh Maintainer with only:

   ```text
   Read AGENTS.md and follow .agents/skills/start-maintenance/SKILL.md.
   ```

The source Session stays read-only. It must not retrieve the destination conversation or guess that the
save succeeded. A chat-only assistant can prepare the recap, but cannot claim it applied local changes.

## Sync to Session

After an explicitly requested sync has validated and installed matching sources and completed reconciliation,
report the snapshot timestamp and any gaps. Provide this prompt for a fresh chat with read-only file access:

```text
Read AGENTS.md and follow .agents/skills/start-session/SKILL.md.
```

The user opens and submits it. Pass no maintenance transcript, credentials, or hidden reports. Do not offer
this success transition after a failed or partial sync. A successful public sync is eligible with its limits
stated. Providing a prompt does not open a chat or start a workflow.

## Optional automation

Use automation only when the current host is known to support it and the user chooses that route. Check
capabilities and describe exactly what will happen before asking for Yes. A draft requires user submission;
a full recap handoff requires isolated apply, a verified success receipt, and a separate visible fresh chat.
Silence, a preselected answer, and a recap mentioning sync are not approval. Existing approval for the exact
handoff is sufficient. No or silence causes no action. Never retry a failed save or launch the follow-up
without resolving the failure. Do not sync, commit, or push as part of a recap handoff.

The [Codex integration](integrations/codex.md) supplies optional draft links and CLI automation. Do not
emit `codex://` links in another client. The [Claude Code adapter](../CLAUDE.md) uses
`SCIONBOOK_CLIENT=claude` for the launcher or `--client claude` for recap/session handoffs.
It has no desktop draft link. Other adapters must document their own
capabilities; never invent a new-chat API or treat a prompt as enforcement of file permissions.
If automation is unsupported or blocked by runtime permissions, use the manual prompts above without
requesting a Session Planner write escalation. A hidden tool terminal is not a user-visible chat.

## Print a portable prompt

From the repository root, these standard-library-only commands print text and exit. They do not read
player data, save files, contact a provider, or start a chat:

```bash
python3 scionbook_handoff.py prompt --role session
python3 scionbook_handoff.py prompt --role maintainer
python3 scionbook_handoff.py prompt --role apply
```

For apply, paste the recap after the printed label. Keep recap text out of URLs and command arguments.

## Claude Code CLI handoff

In a user-accessible terminal with Bash and Claude Code installed:

```bash
python3 scionbook_handoff.py recap --client claude --confirmed
python3 scionbook_handoff.py session --client claude --confirmed
```

Pass only the approved recap through stdin. The apply step uses a fresh, nonpersistent process,
file read/edit tools only, and a structured success receipt before the separate Maintainer launch.
The helper checks for an interactive terminal before any save. `--confirmed` records approval
already received, not permission to skip asking. Never run this as an unattended nested interactive
chat in an app tool; use manual handoff when a user-accessible terminal is unavailable.
