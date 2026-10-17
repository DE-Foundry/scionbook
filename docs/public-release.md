# Public-release controls and verification

The approved delivery method is a reviewed PR, required CI checks, a squash merge into protected
`main`, and automated publication of the tested commit. The first release is 0.1.0. Players choose
a [release ZIP or personal fork](installation.md); contributors use branches and PRs.

## Repository settings

Maintain these GitHub settings alongside the workflow configuration:

| Setting | Policy |
|---|---|
| Main protection | Require PRs, up-to-date passing checks, and resolved conversations; enforce for administrators; block force pushes/deletion |
| Review minimum | Zero while there is one maintainer; add independent approval when another maintainer is available |
| Merging | Squash only, using the Conventional Commit PR title and reviewed PR body |
| External contributions | Allow PRs from everyone; require maintainer approval of all external-contributor workflows |
| Actions tokens | Read-only default; no workflow permission to approve PRs; release job alone requests contents write |
| Actions dependencies | Full commit SHA pins, maintained by weekly Dependabot updates |
| Secret protection | Secret scanning and push protection enabled; review alerts privately |
| Dependency security | Dependabot alerts/security updates plus weekly Python and Actions version updates |
| Code scanning | CodeQL default setup for Python and Actions, including its weekly schedule |
| Vulnerability reports | Private reporting enabled; route reports through SECURITY.md |

Required PR checks are `pytest (ubuntu-latest, 3.10)`, `pytest (ubuntu-latest, 3.14)`,
`pytest (macos-latest, 3.14)`, `pytest (windows-latest, 3.14)`, `quality`, `pr-title`,
`package (ubuntu-latest)`, and `package (windows-latest)`. Require the GitHub Actions app as their source.
The release job is deliberately not a required PR check: it runs after merge. CodeQL uses GitHub's
managed workflow; review its security findings before merge as well.

Python fixture tests block live HTTP and remove the Lodestone cookie. Bash adapter execution remains
Linux/macOS-only. Package checks build from committed source, extract into a new directory, install
requirements in a fresh environment, verify hidden adapter/template files, and start all five CLI entry
points with `--help`. They exercise installation, not authenticated scraping or every assistant client.
Weekly tests/audits can detect newly reported dependency problems without a source change; scheduled
runs do not publish releases. No CI job needs a Lodestone cookie or player files.

## Before merging

1. Review the exact diff, dependency updates, CodeQL findings, and any secret alerts. Use synthetic
   fixtures. Never include player state, profile/account links, real captures, or personal preferences.
2. Ensure the PR title selects the intended version bump. Update RELEASE_NOTES.md with changes,
   compatibility, and migration/rollback instructions; do not copy personal data into release notes.
3. Wait for all required checks on the current PR revision and resolve conversations. For outside
   contributors, review code/workflow changes before approving execution. Never run untrusted PR code
   with write tokens or secrets through a privileged pull-request-target workflow.
4. Squash merge. This authorizes the tested-main release workflow, not a manual bypass of checks.

## After the first release, and after packaging changes

1. Verify that the main workflow and release job succeeded and the version tag points to the tested SHA.
2. Download the release ZIP and checksum without GitHub authentication. Verify SHA-256, extract into a
   fresh directory, and follow the documented installation. Confirm skills/templates and CLI startup.
3. For state-format changes, test migration on a private copy and verify character identity, report
   continuity, and original snapshot timestamps. Keep the matching prior application/state backup.
4. Confirm that the release listing contains the current and previous three stable versions (or fewer
   before four exist), with source tags retained. Drafts and prereleases are outside that cleanup policy.
5. If publication fails, follow [release retry instructions](releasing.md#retry-a-failed-release).
   Do not overwrite a published ZIP or move its tag. Correct faulty code through a PR and a new version.
   Stop promoting a release if installation, integrity, or state preservation fails.

Public visibility and green CI do not certify all historical content as private-data-free. Review
reachable Git history, metadata, and binary assets before sharing it; secret scanning detects supported
credential patterns, not every personal detail. Existing contributor attribution remains in history.
History rewrites require a separate, coordinated decision rather than incidental cleanup.
