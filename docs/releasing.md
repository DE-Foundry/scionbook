# Preparing a public release

The repository already uses the MIT license. Before publishing a checkout or changing repository
visibility, review the exact files and history being released. Local preparation does not publish anything.

## Release review

- Run the offline test suite and inspect CI results for the intended commit.
- Walk through the provider-neutral setup and manual recap handoff. State which client integrations and
  live services were actually tested; offline fixtures do not certify live Lodestone parsing.
- Review tracked files, assets, generated reports, fixtures, author metadata, branches, and tags for
  private player/account information and secrets. Confirm ownership and redistribution rights for assets.
- Review full reachable Git history, not just the current tree or `.gitignore`. A source-only export excludes prior history; do not import history from a checkout containing
  private player state.
- Choose a reviewed history rewrite or a fresh source-only public repository if old history contains
  private data. Do not rewrite or publish the working repository as an incidental cleanup step. Preserve
  private backups separately. Revoke exposed credentials if any are discovered.
- Confirm the public repository name, destination, visibility, and support/reporting channels with the
  owner. Enable private vulnerability reporting where the host supports it and update SECURITY.md if a
  dedicated contact is established.

A source-only release must include shared dot-directories such as `.agents`, optional `.codex` and `.claude`, and
`.github`, while excluding `.git`, virtual environments, caches, credentials, raw captures, and all local
player state. Inspect the actual export, including custom-named files. Do not assume a recursive directory
copy or an old Git archive is safe. Templates and test fixtures must remain neutral/synthetic.

Commit, push, release creation, repository creation, and visibility changes are separate publishing
actions. Report what was locally prepared, tested, and actually published separately.

## Optional fresh-history export

Use `python3 scripts/export_release.py DESTINATION` when a source-only copy with new history is
needed. Normal updates to an existing clean repository do not require a new export or history reset.

1. Commit the shared changes intended for export. The exporter reads HEAD and rejects tracked edits.
2. Add identifying terms to the ignored `.scionbook-release-denylist`, one per line, or supply
   `--deny FILE`. The exporter also checks character IDs, character names, and retainer names from
   local configuration and snapshots when available. Never add that private denylist to Git.
3. Export to a new directory outside the checkout and review every exported file:

   ```bash
   python3 scripts/export_release.py ../scionbook-release
   ```

The exporter refuses tracked player-state filenames and matching identifying terms, includes shared
client adapters, and initializes a new repository without importing prior history. `--commit` optionally
creates its initial commit using the configured Git identity; review author metadata before publication.
Nothing is pushed. Terms shorter than four characters are skipped to limit false matches. This scan
is an aid to review, not a guarantee: check for personal preferences, character-specific guidance,
unknown identifiers, and private data in binary assets as well. Templates must stay neutral and
fixtures synthetic.
