## Changes and compatibility

Pricing now filters known market prohibitions and asks before smaller-batch retries. One answer covers
both the home World and DC; `--no-retry-pricing-single-items` disables retry prompts in agent shells.
After approval, `--pricing-only-from` recovers missing prices from a staged snapshot without a character
re-scrape. New snapshots include optional versioned pricing recovery context. Existing snapshots remain
readable without migration, but pricing-only recovery requires context from a separately requested new
sync. Recovery preserves the character timestamp and saved protections and records its attempt time
separately. Keep the original staged snapshot/report and matching history/protection until the recovered
pair is validated; rollback uses that original set. See the README for commands and installation steps.
Saved recovery prices contain only numeric valuation inputs and HQ/unit-price samples, excluding
third-party names/IDs and unused metadata. Recovery trims earlier raw contexts in its output without
modifying the source snapshot; the context version remains compatible.

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
