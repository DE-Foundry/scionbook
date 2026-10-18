# Install and update Scionbook

Players can use a release ZIP or a personal fork. Both run the same workflows with your chosen agent;
Git knowledge is optional for ZIP users. Contributors use a local Git clone and policy-named branches.

| Method | Choose it when | Updates |
|---|---|---|
| Release ZIP | You want to use Scionbook without managing Git | Extract a new release and copy your local state |
| Personal fork | You want your own source repository, with optional code changes | Fetch upstream and merge application changes |
| Contributor clone | You want to submit code or documentation | Create a focused branch and submit a pull request |

Use a separate local directory for each character. Character branches are not a storage mechanism:
ignored files remain in the working directory when branches change. In every method, character identity,
profile links, preferences, snapshots, reports, and progress stay local and untracked. A fork is not a
personal-data backup or a privacy barrier. Never force-add player files or include them in a pull request.
Keep private backups outside the project repository; keep credentials out of those backups too.

## Release ZIP

1. Open the upstream project's Releases page. Download the desired `scionbook-MAJOR.MINOR.PATCH.zip`
   asset and its `.zip.sha256` checksum, rather than the hosting service's automatic source archive.
   If no packaged release exists yet, use the fork method or wait for a release.
2. Have your agent verify the ZIP's SHA-256 against the downloaded checksum. Extract into a new local
   folder, keeping hidden directories such as `.agents`, `.claude`, and `.codex`.
3. Open the extracted folder in your agent. Follow [Get started](../README.md#get-started) to install
   Python dependencies and complete setup in a fresh Repository Maintainer chat. A ZIP includes all
   project files, but Python, third-party packages, and your agent are installed separately.

You do not need to initialize Git, create a fork, or configure a remote. Example agent request:

```text
Read AGENTS.md and docs/installation.md. Help me install this extracted release using the README,
then follow .agents/skills/setup/SKILL.md for the character and World I provide.
Keep all player data local. Ask me for any missing setup details; never ask me to paste credentials into chat.
```

### Update a ZIP installation

1. Finish active saves or refreshes. Save any outstanding session recap through Maintainer first.
2. Read the new release notes for compatibility changes and migration instructions. Back up the current
   local player files together outside the project repository, preserving their existing timestamps.
3. Download, verify, and extract the new release into a **new folder**. Do not extract over your current
   installation or replace your player files with neutral templates.
4. Follow [Move to a new directory without another sync](../README.md#move-to-a-new-directory-without-another-sync)
   for the exact state-file list and copy procedure. Recreate the Python environment in the new folder.
5. Apply any documented migration to the copied state, then open a fresh read-only Session Planner to
   load it. Moving/updating alone does not require setup or a scrape. Check that the character, saved
   reports, and snapshot date are correct before making the new folder your active installation.

Keep the original installation and private backup until the update is verified. If the new version
cannot read the data, stop and restore the matching prior application/state pair; do not reset setup,
run a sync to hide the problem, or feed migrated state to an older version without compatibility guidance.

## Personal fork

Create a fork through the upstream repository's hosting service, then clone **your fork** locally.
Set `origin` to your fork and `upstream` to the original Scionbook source repository. Use the actual
clone URLs from those repository pages; the placeholders below are not literal URLs.

```bash
git clone "YOUR_FORK_CLONE_URL" scionbook
cd scionbook
git remote add upstream "UPSTREAM_CLONE_URL"
git fetch upstream
git remote set-head upstream --auto
```

Follow [Get started](../README.md#get-started) in this directory. Setup writes ignored local files;
creating a fork does not copy your character data to the hosting service. Review `git status --short`
and any staged diff before every commit or push. Keep arbitrary personal exports under ignored `local/`.
Never change the ignore rules to publish player state. You can use an agent for these steps.

Before pushing any branch to your fork, complete [local privacy setup](releasing.md#privacy-before-push).
Each checkout needs its own ignored denylist and installed hook; include your character and other private
identifiers locally. Forking or cloning does not install hooks or copy private configuration. A GitHub
release secret is not needed merely to use a personal fork, and cannot protect local pushes.

### Update a fork installation

1. Finish saves/refreshes, read upstream release or change notes, and back up local player files outside
   the repository. The default branch may contain changes newer than the latest release ZIP.
2. Check `git status --short`. Resolve pending source edits deliberately before updating; do not discard
   them, commit player files, or stash ignored files as a shortcut. Use the fork's normal update branch.
3. Fetch upstream and attempt a fast-forward update:

   ```bash
   git fetch upstream
   git remote set-head upstream --auto
   git merge --ff-only upstream/HEAD
   ```

4. If Git reports divergent history or a file collision, stop for review. An agent can help merge source
   changes while preserving your customizations and local state. Never use a hard reset or a clean command
   that removes ignored files to force an update through. Do not resolve a collision by committing data.
5. Install the updated `requirements.txt` in your existing virtual environment, follow any documented
   data migration, and verify the saved sources with a fresh Session Planner. Existing state should remain
   local; application updates do not themselves refresh Lodestone or make old snapshots current.
6. Updating your hosted fork is optional: review the commits and diff first, then explicitly push the
   updated branch to `origin`. No player data should be included, and no push to upstream is needed.

If you customize code, keep those changes on policy-named branches and expect source merges when updating.
Saved preferences belong in local configuration rather than edited shared instructions. For release-only
updates without managing source history, use the ZIP method instead.

Example agent request, in a Repository Maintainer chat:

```text
Read AGENTS.md and docs/installation.md. Update my local fork from upstream using the documented
procedure. Preserve my ignored character files and source customizations. Check compatibility and
stop for review if a merge or undocumented migration is needed. Do not commit, push, or refresh Lodestone.
```

## Contribute changes

Use a separate development clone without live player state. Follow [CONTRIBUTING.md](../CONTRIBUTING.md)
for branch creation, Conventional Commits, tests, and pull requests. Contributors without upstream write
access clone their own fork and submit a pull request from it. Personal forks used only for gameplay do
not need to submit their updates or data upstream.
