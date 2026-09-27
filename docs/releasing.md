# Preparing a public release

The repository already uses the MIT license. Before publishing a checkout or changing repository
visibility, review the exact files and history being released. Local preparation does not publish anything.

## Release review

- Run the offline test suite and inspect CI results for the intended commit.
- Walk through the provider-neutral setup and manual recap handoff. State which client integrations and
  live services were actually tested; offline fixtures do not certify live Lodestone parsing.
- Review tracked files, assets, generated reports, fixtures, author metadata, branches, and tags for
  private player/account information and secrets. Confirm ownership and redistribution rights for assets.
- Review full reachable Git history, not just the current tree or `.gitignore`. The original development
  checkout contained character-data sync commits. A source-only export excludes that history; never merge
  it back into a public repository without a separate privacy review.
- Choose a reviewed history rewrite or a fresh source-only public repository if old history contains
  private data. Do not rewrite or publish the working repository as an incidental cleanup step. Preserve
  private backups separately. Revoke exposed credentials if any are discovered.
- Confirm the public repository name, destination, visibility, and support/reporting channels with the
  owner. Enable private vulnerability reporting where the host supports it and update SECURITY.md if a
  dedicated contact is established.

A source-only release must include shared dot-directories such as `.agents`, optional `.codex`, and
`.github`, while excluding `.git`, virtual environments, caches, credentials, raw captures, and all local
player state. Inspect the actual export, including custom-named files. Do not assume a recursive directory
copy or an old Git archive is safe. Templates and test fixtures must remain neutral/synthetic.

Commit, push, release creation, repository creation, and visibility changes are separate publishing
actions. Report what was locally prepared, tested, and actually published separately.
