"""Pre-push coverage includes history, metadata, names, and fail-closed setup."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
import check_push
from test_export_release import source, git


def update(source):
    head = git(source, 'rev-parse', 'HEAD').strip()
    return f'refs/heads/main {head} refs/heads/main {"0" * 40}\n'


@pytest.fixture(autouse=True)
def terms(monkeypatch):
    monkeypatch.setenv('SCIONBOOK_RELEASE_DENYLIST', 'Synthetic Private Identifier')


def test_clean_and_empty_terms(source, monkeypatch):
    check_push.check(update(source))
    monkeypatch.delenv('SCIONBOOK_RELEASE_DENYLIST')
    with pytest.raises(ValueError, match='No privacy terms'):
        check_push.check(update(source))
    check_push.check(f'refs/heads/main {"0" * 40} refs/heads/main {"1" * 40}')


def test_deleted_secret_in_history_still_blocks(source):
    private = source / 'ordinary.md'
    private.write_text('Synthetic Private Identifier')
    git(source, 'add', 'ordinary.md')
    git(source, 'commit', '-qm', 'test: intermediate private content')
    git(source, 'rm', '-q', 'ordinary.md')
    git(source, 'commit', '-qm', 'test: delete content')
    with pytest.raises(ValueError, match='reachable files'):
        check_push.check(update(source))


def test_metadata_blocks_without_printing_term(source):
    git(source, 'commit', '--allow-empty', '-qm', 'test: Synthetic Private Identifier')
    with pytest.raises(ValueError, match='commit metadata') as error:
        check_push.check(update(source))
    assert 'Synthetic Private Identifier' not in str(error.value)


def test_forbidden_filename_blocks(source):
    (source / 'status.json').write_text('{}')
    git(source, 'add', '-f', 'status.json')
    git(source, 'commit', '-qm', 'test: private path')
    with pytest.raises(ValueError, match='reachable files'):
        check_push.check(update(source))


def test_install_preserves_existing_hook_configuration(source):
    git(source, 'config', 'core.hooksPath', 'custom-hooks')
    with pytest.raises(ValueError, match='integrated manually'):
        check_push.install()
    assert git(source, 'config', '--get', 'core.hooksPath').strip() == 'custom-hooks'


def test_annotated_tag_metadata_blocks(source):
    git(source, 'tag', '-a', 'v1.0.0', '-m', 'Synthetic Private Identifier')
    tip = git(source, 'rev-parse', 'v1.0.0').strip()
    with pytest.raises(ValueError, match='tag metadata'):
        check_push.check(f'refs/tags/v1.0.0 {tip} refs/tags/v1.0.0 {"0" * 40}')


def test_install_sets_local_hook_path(source):
    check_push.install()
    assert git(source, 'config', '--local', '--get', 'core.hooksPath').strip() == '.githooks'
