## Changes and compatibility

Automated CLI recap handoffs now ask the model for proposed changes. Python validates permitted player
files and preference fields, installs them, and verifies saved bytes before opening the next chat.
Existing player files need no migration. Manual handoffs and desktop drafts retain their normal client
permissions; the deterministic installer applies to the automated CLI route.

Proposal runs suppress user client settings and unrelated environment variables. Use a current Codex or
Claude Code CLI that supports the documented restriction flags. Set `SCIONBOOK_MODEL` explicitly if you
want a particular proposal model; otherwise the client default applies. Custom provider settings and
credential helpers are not inherited. If the client cannot run with these restrictions, use a manual
handoff instead of removing the restrictions. See [instruction security](docs/instruction-security.md)
for authentication limits, source review, and interrupted-save recovery.

Python 3.10 or newer is required. Install `requirements.txt` in a local virtual environment.
Back up player files together outside the repository before updating. Keep the previous application
and matching state until the new installation is verified; use that matching pair for rollback.
