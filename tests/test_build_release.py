"""Release packages include adapters, reject private state, and retain four versions."""
import hashlib
from pathlib import Path
import sys
import zipfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
import build_release as release
from test_export_release import source, git


@pytest.fixture(autouse=True)
def isolated_ci(monkeypatch):
    monkeypatch.delenv('CI', raising=False)
    monkeypatch.delenv('SCIONBOOK_RELEASE_DENYLIST', raising=False)


@pytest.mark.skipif(sys.platform == "win32", reason="Synthetic symlink fixture needs POSIX; ZIP smoke covers Windows extraction")
def test_zip_is_complete_and_materializes_adapter(source, tmp_path):
    (source / '.agents/skills/example').mkdir(parents=True)
    (source / '.agents/skills/example/SKILL.md').write_text('Synthetic instructions')
    (source / '.claude').mkdir()
    (source / '.claude/skills').symlink_to('../.agents/skills')
    (source / 'requirements.txt').write_text('requests>=2.31\n')
    git(source, 'add', '-A')
    git(source, 'commit', '-qm', 'feat: test adapters')
    (source / 'status.json').write_text('{}')
    out = release.build('1.0.0', tmp_path / 'packages')
    with zipfile.ZipFile(out) as package:
        names = package.namelist()
        assert 'scionbook-1.0.0/.agents/skills/example/SKILL.md' in names
        assert 'scionbook-1.0.0/.claude/skills/example/SKILL.md' in names
        assert 'scionbook-1.0.0/requirements.txt' in names
        assert package.read('scionbook-1.0.0/VERSION') == b'1.0.0\n'
        assert not any('/.git/' in n or n.endswith('/status.json') for n in names)
    assert out.with_suffix('.zip.sha256').read_text().split()[0] == hashlib.sha256(out.read_bytes()).hexdigest()


def test_retention_uses_numeric_versions_and_preserves_unrelated_files(source, tmp_path):
    out = tmp_path / 'packages'
    out.mkdir()
    other = out / 'notes.zip'
    other.write_bytes(b'keep')
    for version in ['1.0.0', '1.1.0', '1.2.0', '1.9.0', '1.10.0']:
        release.build(version, out)
    assert not (out / 'scionbook-1.0.0.zip').exists()
    assert not (out / 'scionbook-1.0.0.zip.sha256').exists()
    assert len(list(out.glob('scionbook-*.zip'))) == 4
    assert other.read_bytes() == b'keep'
    with pytest.raises(ValueError, match='newer'):
        release.build('1.9.0', out)


@pytest.mark.parametrize('version', ['v1.0.0', '01.0.0', '1.0', '1.0.0-rc.1', '../1.0.0'])
def test_invalid_stable_version(version):
    with pytest.raises(ValueError):
        release.version_key(version)


@pytest.mark.parametrize('name', ['local/private.txt', 'nested/status.json.bak', '.env.secret', 'raw/page.html'])
def test_forced_private_paths_block_package(source, tmp_path, name):
    path = source / name
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_text('synthetic')
    git(source, 'add', '-f', name)
    git(source, 'commit', '-qm', 'test: forbidden file')
    with pytest.raises(ValueError, match='Privacy'):
        release.build('1.0.0', tmp_path / 'packages')
    assert not (tmp_path / 'packages').exists()


def test_content_denylist_and_dirty_tree_block_package(source, tmp_path):
    deny = tmp_path / 'deny'
    deny.write_text('Second revision')
    with pytest.raises(ValueError, match='Privacy'):
        release.build('1.0.0', tmp_path / 'packages', [deny])
    (source / 'README.md').write_text('changed')
    with pytest.raises(ValueError, match='Commit'):
        release.build('1.0.0', tmp_path / 'packages')


def test_ci_requires_effective_terms(source, tmp_path, monkeypatch):
    monkeypatch.setenv('CI', 'true')
    monkeypatch.setenv('SCIONBOOK_RELEASE_DENYLIST', '# comment\nabc')
    with pytest.raises(ValueError, match='denylist is empty'):
        release.build('1.0.0', tmp_path / 'packages')
    monkeypatch.setenv('SCIONBOOK_RELEASE_DENYLIST', 'Second revision')
    with pytest.raises(ValueError, match='Privacy check failed'):
        release.build('1.0.0', tmp_path / 'packages')
    monkeypatch.setenv('SCIONBOOK_RELEASE_DENYLIST', 'Synthetic blocked identifier')
    assert release.build('1.0.0', tmp_path / 'packages').is_file()
