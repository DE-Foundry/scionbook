# Contributing to Scionbook

Start with README.md and standards.md. Scionbook keeps Python data tools independent of AI providers;
shared Markdown workflows must work through explicit file-based prompts. Put client-specific setup and
launch behavior in optional integrations, with a manual path that remains usable without that client.

## Clone and create a branch

Use a separate development clone with synthetic fixtures, keeping gameplay in a different local directory.
If you have upstream write access, clone upstream. Otherwise, fork the project and clone your fork; set
`origin` to the fork and add `upstream` pointing to the original repository as in the
[installation guide](docs/installation.md#personal-fork). Never put character data on development branches.

Start a focused branch from the current upstream default branch. The commands below assume `upstream`
points to the original repository; use `origin` instead when you cloned upstream directly:

```bash
git fetch upstream
git remote set-head upstream --auto
git switch -c feat/describe-your-change upstream/HEAD
```

Use `<type>/<kebab-case-summary>` for each branch, such as `fix/preserve-unknown-balances` or
`docs/clarify-setup`. Make Conventional Commits, run relevant checks, review the exact staged diff for
personal data, and push only the intended development branch when ready. Open a pull request against
the upstream default branch with a Conventional Commit title, a behavior summary, and validation results.
Do not commit directly to the upstream default branch. No workflow grants automatic commit/push approval
to an agent. A fork used for gameplay is not required to contribute changes.

## Development

Use Python 3.10 or newer in a virtual environment, then run:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest tests/ -q
```

The suite uses synthetic fixtures and requires no character account, cookie, or live service. Add tests
for changed parser, authentication, persistence, or launcher behavior. For workflow changes, check the
manual path, unavailable capabilities, role boundaries, and linked references. Describe checks actually
performed and remaining limits in the pull request. Do not claim fixture tests prove live compatibility.

Keep changes focused. Discuss larger features in an issue before implementation. For bugs, include the
command/workflow, Python version, operating system, expected behavior, and a sanitized error. Never attach
player snapshots, real account HTML, cookies, or private inventories. Reproduce parser problems using
minimal synthetic fixtures under tests/fixtures/.

Preserve unknown versus zero, complete-history validation, staged refresh installation, and newer dated
player reports. New unlock annotations need exact English quest names and source links; see
[unlock coverage](docs/unlock-coverage.md). Keep personal preferences and reports in ignored local files.

Contributions are provided under the repository's MIT license. Only contribute code, fixtures, and assets
you have the right to share. Public-release checks are documented in [release preparation](docs/releasing.md).


## Commits and versions

Use Conventional Commits for every new commit and PR title: `type(scope): summary` (scope optional).
Examples: `feat(setup): add public-mode setup`, `fix(report): preserve unavailable balances`,
`docs: clarify installation`. Allowed project types are `feat`, `fix`, `docs`, `test`, `refactor`,
`chore`, `ci`, `build`, `perf`, and `revert`. Mark incompatible changes with `!` and explain them in
a `BREAKING CHANGE:` footer. See standards.md and docs/releasing.md for SemVer and the compatibility
contract. Do not rewrite existing history simply to retrofit commit style.

Follow [release policy](docs/releasing.md) for version selection, release notes, and retries.
Add compatibility/migration guidance to RELEASE_NOTES.md when a change requires it.
Before your first push, configure the [local privacy hook](docs/releasing.md#privacy-before-push).

Never include real character names/IDs, character profile links, account links, personal information,
credentials, player reports, or preferences in contributions, branches, tags, releases, commit messages,
or author metadata. Use synthetic fixtures and a nonpersonal project Git identity. Private branches
are not a data-storage exception; ignored runtime files must never be force-added.


## Public CI and merge requirements

Public contributions are welcome. Maintainers must approve workflow execution for outside contributors
before CI runs. Never provide player credentials to CI. Required checks include the Python matrix,
workflow/dependency checks, package smoke tests, and a Conventional Commit PR title. Keep the branch
up to date and resolve review conversations before merging. Squash merge uses the PR title and body;
put a breaking marker in the title and explain compatibility/migration in the body and RELEASE_NOTES.md.

GitHub currently has one maintainer, so PRs and passing checks are required without a second-reviewer
minimum. Revisit that minimum when another maintainer joins. CodeQL runs through GitHub default setup.
Actions are pinned to full commit SHAs; Dependabot updates Python and Actions weekly. Dependabot's
own generated branch names are an exception to the human branch naming convention.
See [public-release controls and verification](docs/public-release.md).
