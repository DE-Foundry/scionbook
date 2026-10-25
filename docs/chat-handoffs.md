# Continue play and optionally start another chat

Normal play stays in one ongoing conversation: setup, requested sync, discussion, planning, and verified
local saves. No handoff is needed after setup, a saved preference, a progress report, or a refresh.
Sync reloads installed sources and updates current advice without erasing newer reports or temporary
choices. A new conversation remains an option when the user wants a fresh context.

## Optional fresh start

First verify outstanding explicit reports are saved with save-state. Open a chat in the same checkout
with local read/write access and submit:

```text
Read AGENTS.md and follow .agents/skills/start-session/SKILL.md.
```

It reads local files; do not forward transcripts, search another chat, or claim the old conversation was
cleared. If reports remain unsaved because writes were unavailable, the user can supply a recap with:

```text
Read AGENTS.md and follow .agents/skills/apply-recap/SKILL.md.
Apply the recap below to local player files and verify the save. Do not sync, commit, or push.

Recap to apply:
[Paste the report here.]
```

The receiving conversation can continue play after saving. No additional Maintainer startup is required.
A recap or prepared prompt is not evidence of persistence; the destination verifies its own save.

## Optional existing adapters

`python3 scionbook_handoff.py prompt --role session|maintainer|apply` prints portable startup text.
The `draft` action is a Codex desktop convenience, not a general-client URL scheme. Drafts require the
user to select permissions and press Send; an apply draft also needs the actual recap pasted. Do not
claim a draft started a workflow, saved data, or changed permissions. See [Codex integration](integrations/codex.md).

For users who deliberately choose the legacy isolated CLI route in a user-accessible terminal:

```bash
python3 scionbook_handoff.py recap --client claude --confirmed
python3 scionbook_handoff.py session --client claude --confirmed
```

The recap adapter proposes changes without write tools, then Python validates/installs/verifies them
before opening a separate maintenance conversation. This remains an optional compatibility route,
not the everyday workflow. `--confirmed` records explicit approval for that exact launch; no or silence
means no action. Never run hidden unattended interactive clients or bypass runtime restrictions.
Failed saves/launches stop the sequence. An already verified save remains saved even if launch fails.
Use save-state directly when the current host supports it. See [instruction security](instruction-security.md)
for proposal isolation, permitted writes, and interrupted-save recovery.
