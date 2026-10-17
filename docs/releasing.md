# Releases

A release is `scionbook-MAJOR.MINOR.PATCH.zip`, accompanied by a SHA-256 checksum.
It contains the committed project source, dependencies manifest, instructions, neutral templates,
skills, documentation, and client adapters needed to set up and run Scionbook. It contains no Git
history, installed Python environment, credentials, or player state. Python 3.10+ and installing
`requirements.txt` are prerequisites; this is not an offline bundle of Python and third-party packages.
The Claude skills link is materialized as ordinary files so ZIP extractors need no symlink support.

## Versioning and retention

Use [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html) and
[Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/).
The compatibility contract covers documented CLI arguments, configuration and saved-data formats,
and documented skill entry points. Backward-compatible features increment MINOR, fixes increment
PATCH, and incompatible changes increment MAJOR. During initial 0.y.z development, incompatible
changes increment MINOR and must still be clearly documented. A transparent migration preserving
existing workflows does not itself break compatibility. Published contents are immutable.

Stable releases use `vMAJOR.MINOR.PATCH` tags. The package builder currently accepts stable versions
only; prerelease and build-metadata channels are not part of the publishing workflow. Select the
initial baseline at the first authorized release; no tag or release is implied by this policy.

Keep the current release plus the previous three versions: four ZIP/checksum pairs total, ordered
numerically by version. After verifying a new hosted release, remove older hosted release assets and
release entries beyond that window. Keep source tags for provenance; never rewrite history merely to
prune downloads. The builder enforces this window in its output directory. Hosted cleanup is a
maintainer step, not an automated side effect of building locally.

## Build a release ZIP

1. Review shared files and history using the checklist below, run `python3 -m pytest tests/ -q`,
   and commit the intended source with a Conventional Commit. Do not include personal files.
2. Put private identifying terms in ignored `.scionbook-release-denylist` (one per line), optionally
   adding `--deny FILE`. Local configuration/snapshot identity terms are checked automatically.
3. From the project root, run, substituting the intended version:

   ```bash
   python3 scripts/build_release.py 1.0.0
   ```

4. Inspect `local/releases/scionbook-1.0.0.zip` and its `.zip.sha256` file. Extract into a fresh
   directory, install dependencies, and verify the documented setup files and skill adapters exist.
   The generated `VERSION` identifies the package. Never repackage an already published version.
5. On separately authorized publication, tag the reviewed commit, upload the ZIP and checksum as
   release assets, verify downloads, and enforce the hosted retention window above. Do not substitute
   the hosting service's automatic source archive: it lacks the builder's adapter handling and checks.

The builder reads HEAD, rejects tracked edits, private filenames/storage directories, and known
identifying terms, and refuses overwriting or building below retained versions. Retention removes
only matching stable Scionbook ZIP/checksum pairs after the new pair is written. Keep all retained
packages in the same output directory. Untracked working files are not packaged.
Checks cannot identify every possible personal detail; review prose, unknown links/identifiers,
binary metadata, commit messages, and author metadata too. Use a nonpersonal project author identity
when publishing; current ignores cannot remove information already committed.

Players may install a release ZIP or use a personal fork; contributors use a local clone and
policy-named branches. See [installation and updates](installation.md). Character data stays local
and untracked in every method; character branches must never store personal state.

Release notes must describe installation/update steps, supported Python versions, and any changes to
saved-data formats. Document and verify a migration preserving existing state when formats change;
include backup and rollback guidance. Never require users to discard reports or rerun setup merely
to upgrade. A release without data-format changes should say that existing local state is compatible.

## Publication privacy review

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
