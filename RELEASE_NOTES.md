## Changes and compatibility

Pricing-only recovery can now fill missing prices from an explicitly accepted partial snapshot
without re-scraping character data. Existing complete-pricing defaults and automatic batch reduction
remain intact. Recovery requires approval and matching versioned context; existing snapshots remain
readable without migration. New recovery outputs preserve character source time and saved protections,
record attempt time separately, and recompute coverage before writing. Retain the original staged
snapshot/report with matching history/protections until validation; roll back using that original set.
Saved price inputs exclude third-party identities and unused response metadata, including when trimming
an earlier raw recovery context. See README.md for commands, validation, and partial-coverage overrides.

The player workflow now stays in one conversation across setup, sync, discussion, planning, and local
saves. Clear standing preferences and confirmed reports save immediately through save-state; recaps
and fresh chats are optional. Interactive Session launchers now request write access with normal host
approval controls. Existing read-only chats need their host's normal permission change to save; where
unavailable, changes stay explicitly unsaved. Optional isolated recap proposals remain restricted.

No player-file schema migration or new scrape is required. Restart/reload the shared workflow instructions
and saved sources after updating. Existing reports/preferences are preserved; ambiguous old preference
prose is not automatically migrated. scionbook_state.py adds validated same-chat persistence without an
AI-provider dependency. All real-data checks and artifacts stay local and ignored.

Authenticated refreshes now assume complete pricing unless explicitly overridden. Persistent failures
let the user retry, reduce batches down to one, or ignore remaining gaps with --allow-partial-pricing.
That one-run option does not alter the saved default. Explicit --no-pricing/--no-retainers choices still
work; with a saved full-pricing requirement, also pass --allow-partial-pricing. Public mode is unchanged.
Failed required-pricing runs leave snapshot/report/protection outputs untouched. See README.md for
coverage semantics. To roll back, retain the prior application with its matching local-state backup;
older versions can still read the unchanged player-file formats.


Automated CLI recap handoffs now ask the model for proposed changes. Python validates permitted player
files and preference fields, installs them, and verifies saved bytes before opening the next chat.
Existing player files need no migration. Manual saves retain their normal client permissions; same-chat helper saves and automated CLI
proposals use the deterministic installer.

Proposal runs suppress user client settings and unrelated environment variables. Use a current Codex or
Claude Code CLI that supports the documented restriction flags. Set `SCIONBOOK_MODEL` explicitly if you
want a particular proposal model; otherwise the client default applies. Custom provider settings and
credential helpers are not inherited. If the client cannot run with these restrictions, use a manual
handoff instead of removing the restrictions. See [instruction security](docs/instruction-security.md)
for authentication limits, source review, and interrupted-save recovery.

Python 3.10 or newer is required. Install `requirements.txt` in a local virtual environment.
Back up player files together outside the repository before updating. Keep the previous application
and matching state until the new installation is verified; use that matching pair for rollback.
