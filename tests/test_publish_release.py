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
    ('0.1.0', ['docs: update usage', 'ci: update jobs'], '0.1.1'),
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


def test_first_release_creates_draft_at_tested_sha_before_publication(tmp_path, monkeypatch):
    calls = []
    state = []
    artifact = tmp_path / 'scionbook-0.1.0.zip'
    artifact.write_bytes(b'zip')
    monkeypatch.setattr(release, 'releases', lambda: state)
    monkeypatch.setattr(release, 'plan', lambda _: '0.1.0')
    monkeypatch.setattr(release, 'git', lambda *args: 'tested-sha')
    monkeypatch.setattr(release.package, 'build', lambda *args: artifact)
    def command(*args):
        calls.append(args)
        if args[:2] == ('release', 'create'):
            assert args[args.index('--target') + 1] == 'tested-sha'
            assert '--draft' in args
            assert 'Existing local configuration' in Path(args[args.index('--notes-file') + 1]).read_text()
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
