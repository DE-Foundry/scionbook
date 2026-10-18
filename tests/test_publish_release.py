"""Version selection, retry safety, and hosted retention without network writes."""
import hashlib
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
import publish_release as release
from test_export_release import source, git


@pytest.mark.parametrize('previous,messages,expected', [
    (None, ['feat!: first version'], '0.1.0'),
    ('0.1.0', ['feat(setup): option'], '0.2.0'),
    ('0.1.0', ['fix: correct report'], '0.1.1'),
    ('0.1.0', ['docs: update usage', 'ci: update jobs'], None),
    ('0.1.0', ['fix!: new data format'], '0.2.0'),
    ('1.2.3', ['feat: something', 'fix: change\n\nBREAKING CHANGE: new format'], '2.0.0'),
    ('1.2.3', ['refactor: change\n\nBREAKING-CHANGE: new format'], '2.0.0'),
    ('1.2.3', ['feat: feature', 'fix: bug'], '1.3.0'),
    ('1.2.3', ['Legacy message'], '1.2.4'),
])
def test_version_bumps(previous, messages, expected):
    assert release.next_version(previous, messages) == expected


def test_plan_first_release_retry_and_new_changes(source):
    assert release.plan([]) == '0.1.0'
    git(source, 'tag', 'v0.1.0')
    assert release.plan([]) == '0.1.0'
    git(source, 'commit', '--allow-empty', '-qm', 'feat: new option')
    assert release.plan([]) == '0.2.0'


def test_plan_skips_superseded_commit(source):
    git(source, 'tag', 'v0.1.0')
    git(source, 'checkout', '-q', 'HEAD~1')
    # ancestry subprocess must run in the fixture repository too
    assert release.plan([]) is None


def test_draft_retry_requires_exact_commit(source):
    draft = {'draft': True, 'tag_name': 'v0.1.0', 'target_commitish': git(source, 'rev-parse', 'HEAD').strip()}
    assert release.plan([draft]) == '0.1.0'
    draft['target_commitish'] = 'main'
    with pytest.raises(RuntimeError, match='Unfinished'):
        release.plan([draft])


def test_retention_is_numeric_and_ignores_drafts_and_prereleases():
    rows = [{'tag_name': 'v' + version, 'draft': False, 'prerelease': False}
            for version in ['0.1.0', '0.2.0', '0.3.0', '0.9.0', '0.10.0']]
    rows += [{'tag_name': 'v8.0.0', 'draft': True, 'prerelease': False},
             {'tag_name': 'v9.0.0', 'draft': False, 'prerelease': True},
             {'tag_name': 'unrelated', 'draft': False, 'prerelease': False}]
    assert [r['tag_name'] for r in release.expired(rows)] == ['v0.1.0']


def test_download_checksum_mismatch_stops_verification(tmp_path, monkeypatch):
    artifact = tmp_path / 'scionbook-0.1.0.zip'
    artifact.write_bytes(b'expected')
    def download(*args):
        directory = Path(args[args.index('--dir') + 1])
        (directory / artifact.name).write_bytes(b'tampered')
        (directory / (artifact.name + '.sha256')).write_text(
            hashlib.sha256(b'tampered').hexdigest() + '  ' + artifact.name)
    monkeypatch.setattr(release, 'gh', download)
    with pytest.raises(RuntimeError, match='verification'):
        release.verify('v0.1.0', artifact)


@pytest.mark.parametrize('published,fail_verification', [(False, False), (False, True), (True, False)])
def test_publish_verifies_before_pruning_and_never_replaces_published_assets(
        tmp_path, monkeypatch, published, fail_verification):
    tag = 'v0.5.0'
    row = {'tag_name': tag, 'draft': not published, 'prerelease': False, 'target_commitish': 'tested-sha'}
    monkeypatch.setattr(release, 'git', lambda *args: 'tested-sha')
    older = [{'tag_name': f'v0.{i}.0', 'draft': False, 'prerelease': False} for i in range(1, 5)]
    monkeypatch.setattr(release, 'releases', lambda: [row, *older])
    monkeypatch.setattr(release, 'plan', lambda _: '0.5.0')
    artifact = tmp_path / 'scionbook-0.5.0.zip'
    artifact.write_bytes(b'zip')
    monkeypatch.setattr(release.package, 'build', lambda *args: artifact)
    calls = []
    def command(*args):
        calls.append(args)
        if args[:2] == ('release', 'edit'):
            row['draft'] = False
    def verify(*args):
        calls.append(('verified',))
        if fail_verification:
            raise RuntimeError('verification failed')
    monkeypatch.setattr(release, 'gh', command)
    monkeypatch.setattr(release, 'verify', verify)
    if fail_verification:
        with pytest.raises(RuntimeError):
            release.publish()
        assert row['draft']
        assert not any(c[:2] == ('release', 'delete') for c in calls)
    else:
        release.publish()
        assert calls[-1] == ('release', 'delete', 'v0.1.0', '--yes')
        assert calls.index(('verified',)) < len(calls) - 1
    if published:
        assert not any(c[:2] in [('release', 'upload'), ('release', 'edit')] for c in calls)


def test_first_release_creates_draft_at_tested_sha_before_publication(source, tmp_path, monkeypatch):
    calls = []
    state = []
    artifact = tmp_path / 'scionbook-0.1.0.zip'
    artifact.write_bytes(b'zip')
    monkeypatch.setattr(release, 'releases', lambda: state)
    monkeypatch.setattr(release, 'plan', lambda _: '0.1.0')
    (source / 'RELEASE_NOTES.md').write_text('Fixture compatibility notes')
    git(source, 'add', 'RELEASE_NOTES.md')
    git(source, 'commit', '-qm', 'feat: fixture release')
    tested_sha = git(source, 'rev-parse', 'HEAD').strip()
    monkeypatch.setattr(release.package, 'build', lambda *args: artifact)
    def command(*args):
        calls.append(args)
        if args[:2] == ('release', 'create'):
            assert args[args.index('--target') + 1] == tested_sha
            assert '--draft' in args
            assert 'Fixture compatibility notes' in Path(args[args.index('--notes-file') + 1]).read_text()
            state.append({'tag_name': 'v0.1.0', 'draft': True, 'prerelease': False})
        if args[:2] == ('release', 'edit'):
            assert calls[-2] == ('verified',)
            state[0]['draft'] = False
    monkeypatch.setattr(release, 'gh', command)
    monkeypatch.setattr(release, 'verify', lambda *args: calls.append(('verified',)))
    release.publish()
    assert [call[:2] for call in calls] == [
        ('release', 'create'), ('release', 'upload'), ('verified',),
        ('release', 'edit'), ('verified',)]


def test_notes_include_subjects_and_only_changed_appendix(source):
    (source / 'RELEASE_NOTES.md').write_text('Initial appendix')
    git(source, 'add', 'RELEASE_NOTES.md')
    git(source, 'commit', '-qm', 'feat: first release')
    assert 'Initial appendix' in release.release_notes('0.1.0')
    git(source, 'tag', 'v0.1.0')
    git(source, 'commit', '--allow-empty', '-qm', 'fix: reviewed subject\n\nUnreviewed body')
    notes = release.release_notes('0.1.1')
    assert 'fix: reviewed subject' in notes
    assert 'Initial appendix' not in notes
    assert 'Unreviewed body' not in notes
    (source / 'RELEASE_NOTES.md').write_text('New migration notes')
    git(source, 'add', 'RELEASE_NOTES.md')
    git(source, 'commit', '-qm', 'docs: migration')
    assert 'New migration notes' in release.release_notes('0.1.1')


def test_runtime_dependencies_publish_even_with_chore_title(source):
    git(source, 'tag', 'v0.1.0')
    git(source, 'commit', '--allow-empty', '-qm', 'ci: maintenance')
    assert release.plan([]) is None
    (source / 'requirements.txt').write_text('example>=1')
    git(source, 'add', 'requirements.txt')
    git(source, 'commit', '-qm', 'chore(deps): runtime update')
    assert release.plan([]) == '0.1.1'


def test_published_retry_verifies_hosted_checksum_without_rebuild(tmp_path, monkeypatch):
    artifact = tmp_path / 'scionbook-0.1.0.zip'  # deliberately absent
    def download(*args):
        directory = Path(args[args.index('--dir') + 1])
        (directory / artifact.name).write_bytes(b'original compression')
        (directory / (artifact.name + '.sha256')).write_text(
            hashlib.sha256(b'original compression').hexdigest() + '  ' + artifact.name)
    monkeypatch.setattr(release, 'gh', download)
    release.verify('v0.1.0', artifact, False)


@pytest.mark.parametrize('path', ['.agents/skills/example/SKILL.md', 'templates/example.md',
                                  'README.md', 'scripts/example.py', 'requirements.txt'])
def test_maintenance_title_releases_product_paths(source, path):
    git(source, 'tag', 'v0.1.0')
    file = source / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text('Synthetic behavior update')
    git(source, 'add', path)
    git(source, 'commit', '-qm', 'docs: update shipped behavior')
    assert release.plan([]) == '0.1.1'


@pytest.mark.parametrize('path', ['.github/workflows/example.yml', 'tests/example.py',
                                  'requirements-dev.txt', 'requirements-ci.txt'])
def test_maintenance_paths_can_skip(source, path):
    git(source, 'tag', 'v0.1.0')
    file = source / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text('Synthetic maintenance')
    git(source, 'add', path)
    git(source, 'commit', '-qm', 'chore: maintenance')
    assert release.plan([]) is None


def test_rename_product_into_tests_still_releases(source):
    git(source, 'tag', 'v0.1.0')
    (source / 'tests').mkdir()
    git(source, 'mv', 'README.md', 'tests/README.md')
    git(source, 'commit', '-qm', 'chore: move file')
    assert release.plan([]) == '0.1.1'


@pytest.mark.parametrize('appendix', [False, True])
def test_private_notes_block_before_github_create(source, tmp_path, monkeypatch, appendix):
    monkeypatch.setenv('SCIONBOOK_RELEASE_DENYLIST', 'Synthetic Private Identifier')
    if appendix:
        (source / 'RELEASE_NOTES.md').write_text('SyntheticPrivateIdentifier')
        git(source, 'add', 'RELEASE_NOTES.md')
        git(source, 'commit', '-qm', 'fix: neutral title')
    else:
        git(source, 'commit', '--allow-empty', '-qm', 'fix: synthetic-private-identifier')
    monkeypatch.setattr(release, 'releases', lambda: [])
    monkeypatch.setattr(release.package, 'build', lambda *a: tmp_path / 'scionbook-0.1.0.zip')
    monkeypatch.setattr(release, 'gh', lambda *a: pytest.fail('GitHub mutation before privacy validation'))
    with pytest.raises(ValueError, match='Privacy check failed in release notes'):
        release.publish()


def test_private_draft_notes_block_publication(source, tmp_path, monkeypatch):
    monkeypatch.setenv('SCIONBOOK_RELEASE_DENYLIST', 'Synthetic Private Identifier')
    row = {'tag_name': 'v0.1.0', 'draft': True, 'prerelease': False,
           'target_commitish': git(source, 'rev-parse', 'HEAD').strip(),
           'body': 'Synthetic%20Private%20Identifier'}
    monkeypatch.setattr(release, 'releases', lambda: [row])
    monkeypatch.setattr(release.package, 'build', lambda *a: tmp_path / 'scionbook-0.1.0.zip')
    monkeypatch.setattr(release, 'gh', lambda *a: pytest.fail('GitHub mutation before privacy validation'))
    with pytest.raises(ValueError, match='Privacy check failed in release notes'):
        release.publish()
