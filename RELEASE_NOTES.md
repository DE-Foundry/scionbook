## Changes and compatibility

The first automated release is 0.1.0. It packages Scionbook's portable assistant workflows,
character setup and reporting tools, crafting protection, and ZIP/fork installation instructions.
Public-release automation adds dependency and workflow checks, Windows Python coverage, extracted-ZIP
installation checks, and tested-main publication with verified checksums and four-release retention.

Existing local configuration, snapshots, reports, and preferences remain compatible with this release;
no new saved-data migration is required by the release automation. Copy existing state using
`docs/installation.md` and the README's state-file list. Do not rerun setup merely to upgrade.

Python 3.10 or newer is required. Install `requirements.txt` in a local virtual environment.
Back up player files together outside the repository before updating. Keep the previous application
and matching state until the new installation is verified; use that matching pair for rollback.
