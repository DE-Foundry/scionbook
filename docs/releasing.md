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
existing workflows does not itself break compatibility. Published contents must never be overwritten. Platform immutability is evaluated below.

Stable releases use `vMAJOR.MINOR.PATCH` tags. The initial automated release is **0.1.0**.
The package builder currently accepts stable versions only; prerelease and build-metadata channels
are not part of the publishing workflow.

Keep the current release plus the previous three versions: four ZIP/checksum pairs total, ordered
numerically by version. After verifying a new hosted release, remove older hosted release assets and
release entries beyond that window. Keep source tags for provenance; never rewrite history merely to
prune downloads. The builder enforces this window in its output directory. The automated publication job enforces
the same window on GitHub only after downloading and verifying the newly published assets. Local
builds never delete hosted releases. Drafts, prereleases, and non-versioned releases are left alone.

## Automatic publication after merge

The `release` job in `.github/workflows/tests.yml` depends on the entire offline test matrix, workflow/dependency checks, and Linux/Windows ZIP smoke tests. A push
to `main` in the source repository (including a merged PR) publishes once those tests pass. Feature
branches, pull-request events, tags, and personal forks cannot publish through this job. A manual
run of the **Tests** workflow on `main` also runs the matrix and can retry publication.
The job uses the built-in GitHub token with `contents: write`; tests retain read-only permissions.
No personal access token or player credentials are needed.

The job checks out the exact tested commit with full history and tags. Publication is serialized,
and an older run is skipped if a newer descendant is already tagged. The first version is `0.1.0`;
subsequent versions use all non-merge commit messages since the highest stable version tag:

- A `BREAKING CHANGE:` / `BREAKING-CHANGE:` footer or Conventional Commit `!` bumps MAJOR at 1.0.0+,
  or MINOR while the major version is zero.
- Otherwise, any `feat` commit bumps MINOR.
- Ranges containing only `ci`, `test`, `docs`, or `chore` commits can skip publication. Those subjects
  remain in the range for the next release. Skipping also requires every changed path to be under
  `.github/` or `tests/`, or exactly `requirements-dev.txt` or `requirements-ci.txt`. Changes to any other
  path warrant at least a PATCH, including skills, templates, documentation, runtime dependencies, and
  removed/renamed product files. Markdown can change agent behavior and is part of the shipped product.
- Other changes bump PATCH. Breaking markers take precedence over maintenance filtering.

Use Conventional Commits for individual commits and squash-merge titles. An ordinary merge includes
its underlying commits in version analysis; the generated merge-message wrapper is ignored. Keep tags
even after release retention deletes old download entries. Do not manually move or reuse version tags.

Follow the [approved public-release procedure](public-release.md). Generated notes list non-merge commit
subjects since the previous stable tag (reviewed squash PR titles). Author metadata and commit bodies
are not copied. Generated notes and existing draft notes are scanned using the release denylist before
creation/publication; a match stops the job without printing the term. `RELEASE_NOTES.md` is an optional
reviewed compatibility/migration appendix: it is appended
only when changed relative to the previous release, or when present for the first release. Update it
when a change needs installation, migration, backup, or rollback guidance; routine dependency PRs need
no manual notes edit. Approval and merge authorize automated publication, not an assistant merge.

Publication requires a nonempty `SCIONBOOK_RELEASE_DENYLIST` secret for content scanning, checks private
paths, builds the ZIP, and creates a draft for the tested SHA, uploads ZIP/checksum,
and downloads both to verify them against the local build before publishing. It verifies the published
assets against their hosted checksum again before deleting older release entries and assets. Source
tags are retained. Already-published retries never rebuild or compare compressed bytes against a new
runner; compression implementations can differ. Hosted checksums detect corruption, not malicious
replacement of both assets.
Fork owners who deliberately want their own releases must opt in by changing the fork guard themselves;
ordinary fork updates never publish player data.

### Retry a failed release

Re-run the failed workflow for its original commit. A matching draft can have incomplete uploads
replaced; a published release is only verified and never overwritten. A retry at an already released
commit does not increment the version, and completes retention if publication previously succeeded.
If an unfinished draft belongs to another commit, newer publication stops: finish the original run
before proceeding. If draft repair needs a workflow fix, review/remove that unpublished draft before
retrying the corrected main commit. Do not delete a published release to bypass a verification failure.
Investigate an asset mismatch or divergent tag ancestry rather than changing existing release contents.

For setup, enable Actions and allow the workflow's `contents: write` permission under repository or
organization policy. The first successful main run containing this workflow publishes `v0.1.0` when no
stable version tags exist; older merged commits without this job cannot publish retroactively.

## Privacy before push

A public push exposes content before CI runs. Everyone who pushes from a clone or personal fork must
configure a local denylist and install the privacy hook in **each checkout**, including maintainers and
agent-assisted contributors. ZIP-only users who do not use Git do not need a hook.

1. Create `.scionbook-release-denylist` in the repository root using a local editor. Add the identifying
   terms you want kept private, one per line. Include character names, Lodestone character IDs, retainer
   names, real names, private email addresses, private account handles, and personal profile URLs as
   applicable. Do not include the public GitHub contributor handle or GitHub-provided noreply address:
   these are expected public attribution on PRs and commits. Contributors without characters should
   still protect their personal identifiers.
2. Use distinctive terms of at least four characters. Matching is case-insensitive and checks substrings,
   including multiword names joined with
   punctuation/underscores, concatenated names, and percent-encoded URL forms.
   Blank lines and lines beginning with `#` are ignored. Avoid generic world/job names or ordinary words
   that would match legitimate source text. Do not add passwords or tokens; use credential scanning for
   secrets. Local character/snapshot identities are also loaded automatically when available, but a
   separate development checkout often has no such files.
3. Install the hook and confirm Git ignores the denylist:

   ```bash
   python3 scripts/check_push.py --install
   git check-ignore .scionbook-release-denylist
   ```

4. Review staged files and commit metadata before pushing. Keep the denylist current as identifiers
   change. Never force-add it, its backups, or player files. Never copy real terms into documentation,
   test fixtures, PRs, issues, or logs. The denylist is intentionally absent from clones and release ZIPs;
   create it privately for each checkout instead of committing it for others.

For illustration only, a synthetic denylist could contain:

```text
# Replace these fictional examples locally; they do not protect your own identifiers.
Example Adventurer
example-person@example.invalid
```

Do not use dummy terms merely to satisfy the nonempty check. If a push reports no configured terms,
populate the ignored file and retry. If it reports a match, inspect the files/history privately; do not
disable the hook or remove a legitimate term to get the push through. An agent must stop and report the
block if it cannot resolve it within the user's authorized scope.

The hook reuses `export_release.scan` and checks all
reachable commit files, commit messages/author metadata, and pushed ref names, including files deleted
before the tip. It fails closed without effective terms. Existing custom hook configurations are not
overwritten; integrate `python3 scripts/check_push.py` into the existing pre-push hook, passing its stdin.
Hooks require installation in each clone and can be bypassed; they supplement review, not enforce it
for every contributor. Use a nonpersonal Git identity before committing (see below). A finding in
history requires private investigation; deleting the file at HEAD does not remove it from a push.

### Contributor identity and GitHub web merges

Before merging, each maintainer must enable **Keep my email addresses private** in
[GitHub email settings](https://github.com/settings/emails). GitHub uses a noreply address for web commits
and merges when this is enabled; a local hook cannot inspect commits created on GitHub. See
[GitHub's commit email guidance](https://docs.github.com/en/account-and-profile/how-tos/email-preferences/setting-your-commit-email-address).
For local commits, configure a project identity or the GitHub-provided noreply address in Git. The public
GitHub handle and its noreply attribution are permitted; do not add them to the privacy denylist. This
exception does not permit character/account links, private handles, or personal email addresses.

Changing settings does not anonymize existing commits. The hook scans all reachable history, so a newly
added private email may reveal an old exposure and block subsequent pushes. Resolve that finding with
an explicit owner decision about coordinated history cleanup versus accepting the existing exposure;
do not silently remove the term, bypass the hook, or rewrite shared history. Accepting an exposure does
not itself configure a scanner exception; any such implementation requires separate review. Do not copy
the identifying value into an issue or PR while discussing the finding.

The hook currently rescans all reachable commits. If measured push latency becomes a problem, consider
a reviewed local cache keyed by both commit SHA and a hash of effective denylist terms, invalidated when
scanner rules change. No persistent scan cache or historical allowlist is implemented today.

### Release-job privacy backstop

Maintainers must separately configure the Actions secret `SCIONBOOK_RELEASE_DENYLIST` with the
identifying terms relevant to the release repository, using the same one-term-per-line format. The local
file and secret serve different stages; neither replaces the other. GitHub secrets are not downloaded
into local checkouts. Ordinary contributors need only their local file and hook; do not send private
denylists to maintainers or add secrets to a personal fork merely to use it. Only the release step
receives the secret; PR/test/package jobs never do. `build_release.build` fails
closed under CI without effective terms. Package smoke tests explicitly use structural-only mode
(`require_terms=False`) to test installation without exposing private terms; they do not certify content
privacy. Local builds scan available terms but cannot certify absent or unknown identifiers. No term
scanner can recognize all personal information or binary metadata. CI is a publication backstop for
ZIPs and cannot undo a public Git push.

## Build a release ZIP locally

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
5. Normal publication is handled by the main workflow above. A local build is for inspection and does
   not publish or tag anything. Do not substitute the hosting service's automatic source archive: it
   lacks the builder's adapter handling and checks.

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

## Platform integrity options

[Immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases)
lock published assets and tags and generate a release attestation. GitHub allows deleting an entire
immutable release; its tag name cannot be reused afterward. This is compatible with retaining source
tags while pruning entire old release entries. The draft/upload/publish sequence already fits that model.
Platform immutability is not enabled by this code change; validate retention with it before enabling it
on the production repository.

[Build provenance attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations)
record where and how an artifact was built. Adding `actions/attest-build-provenance` would require a pinned
action, release-job `id-token: write` and `attestations: write`, and exposing the exact built ZIP to that
step before publication. Document `gh attestation verify` for consumers and test retries against the
original artifact. This is a separate future enhancement; the current checksum does not prove provenance.
