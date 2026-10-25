"""Configured refresh modes and credential errors through the real CLI entry point."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scionbook_config as config
import scionbook_report as report
import scionbook_setup as setup
import scionbook_quest_history as history
from scionbook_http import HTTP_HEADERS, LODESTONE, LODESTONE_HEADERS, USER_AGENT

PROFILE = '<p class="frame__chara__name">Example Adventurer</p><p class="frame__chara__world">Example World [Example DC]</p>'


def configured(tmp_path, mode):
    path = tmp_path / 'scionbook.json'
    path.write_text(json.dumps({
        'version': 1, 'character_id': '12345', 'name': 'Example Adventurer',
        'world': 'Example World', 'data_center': 'Example DC',
        'timezone': 'UTC', 'mode': mode, 'preferences': {},
    }))
    return path


@pytest.mark.parametrize('disabled', ['--no-pricing', '--no-retainers'])
def test_saved_complete_pricing_preference_prevents_downgrade(monkeypatch, tmp_path, disabled, capsys):
    path = configured(tmp_path, 'full')
    data = json.loads(path.read_text())
    data['preferences']['sync'] = {'require_complete_pricing': True}
    path.write_text(json.dumps(data))
    monkeypatch.setattr(report.requests, 'Session', lambda: pytest.fail('network session opened'))
    monkeypatch.setattr(sys, 'argv', ['scionbook_report.py', '--config', str(path), disabled])
    with pytest.raises(SystemExit) as exc:
        report.main()
    assert exc.value.code == 2
    assert 'complete pricing conflicts' in capsys.readouterr().err


@pytest.mark.parametrize('sync', [None, [], {'require_complete_pricing': 'yes'}, {'require_complete_pricing': 1}])
def test_invalid_sync_preferences_rejected(sync):
    with pytest.raises(ValueError, match='preferences.sync'):
        config.validate_preferences({'sync': sync})


@pytest.mark.parametrize('saved,override,standalone,expected', [
    ('full', None, False, 'full'), ('public', None, False, 'public'),
    ('full', 'public', False, 'public'), ('public', 'full', False, 'full'),
    ('public', None, True, 'full'), ('full', 'public', True, 'public'),
])
def test_mode_precedence(tmp_path, saved, override, standalone, expected):
    path = configured(tmp_path, saved)
    before = path.read_bytes()
    assert config.resolve_mode(override, path, explicit_identity=standalone) == expected
    assert path.read_bytes() == before


@pytest.mark.parametrize('saved,flags', [
    ('public', []), ('full', ['--mode', 'public']), ('full', ['--anon']),
])
def test_public_cli_never_prompts_or_fetches_private_data(monkeypatch, tmp_path, saved, flags):
    path = configured(tmp_path, saved)
    out = tmp_path / 'status.json'
    monkeypatch.setenv('LODESTONE_COOKIE', 'synthetic-unused-cookie')
    monkeypatch.setattr(report.getpass, 'getpass', lambda *a: pytest.fail('credential prompt'))
    def private(*a, **kw):
        pytest.fail('private fetch in public mode')
    for name in ('fetch_quests', 'fetch_currency', 'find_retainer_index'):
        monkeypatch.setattr(report, name, private)
    def public_fetch(url, session, *a, **kw):
        assert url.startswith(LODESTONE + '/character/12345/')
        assert 'Cookie' not in report.HEADERS
        assert 'Cookie' not in session.headers
        assert session.headers['User-Agent'] == USER_AGENT
        return BeautifulSoup(PROFILE, 'html.parser'), PROFILE
    monkeypatch.setattr(report, 'HEADERS', {**LODESTONE_HEADERS, 'Cookie': 'stale-synthetic-cookie'})
    monkeypatch.setattr(report, 'fetch', public_fetch)
    monkeypatch.setattr(sys, 'argv', ['scionbook_report.py', '--config', str(path),
        '--fast', '--out', str(out)] + flags)
    report.main()
    data = json.loads(out.read_text())
    assert data['mode'] == 'public' and data['authenticated'] is False
    assert data['lodestone_url'] == LODESTONE
    assert data['quests']['total_completed'] is None
    assert data['currencies'] is None
    assert json.loads(path.read_text())['mode'] == saved


@pytest.mark.parametrize('flags', [[], ['--cookie-env'], ['--cookie', '   ']])
def test_blank_full_credentials_preserve_outputs_without_network(monkeypatch, tmp_path, flags):
    path = configured(tmp_path, 'full')
    out, cleanup = tmp_path / 'status.json', tmp_path / 'cleanup.md'
    out.write_text('Previous snapshot')
    cleanup.write_text('Previous report')
    monkeypatch.setenv('LODESTONE_COOKIE', '   ')
    monkeypatch.setattr(report.sys.stdin, 'isatty', lambda: True)
    monkeypatch.setattr(report.getpass, 'getpass', lambda *a: '   ')
    monkeypatch.setattr(report.requests, 'Session', lambda: pytest.fail('session opened'))
    monkeypatch.setattr(sys, 'argv', ['scionbook_report.py', '--config', str(path),
        '--out', str(out), '--report', str(cleanup)] + flags)
    with pytest.raises(SystemExit, match='Cookie is empty'):
        report.main()
    assert out.read_text() == 'Previous snapshot'
    assert cleanup.read_text() == 'Previous report'


@pytest.mark.parametrize('flags', [['--cookie-env'], ['--cookie', 'synthetic']])
def test_public_mode_rejects_explicit_credentials(monkeypatch, tmp_path, flags):
    path = configured(tmp_path, 'public')
    monkeypatch.setattr(report.requests, 'Session', lambda: pytest.fail('session opened'))
    monkeypatch.setattr(sys, 'argv', ['scionbook_report.py', '--config', str(path)] + flags)
    with pytest.raises(SystemExit, match='Public mode conflicts'):
        report.main()


@pytest.mark.parametrize('flags', [
    ['--anon', '--mode', 'full'], ['--cookie', 'synthetic', '--cookie-env'],
])
def test_conflicting_flags_fail_before_network(monkeypatch, flags):
    monkeypatch.setattr(report.requests, 'Session', lambda: pytest.fail('session opened'))
    monkeypatch.setattr(sys, 'argv', ['scionbook_report.py'] + flags)
    with pytest.raises(SystemExit) as error:
        report.main()
    assert error.value.code == 2


@pytest.mark.parametrize('source', ['prompt', 'environment', 'argument'])
def test_full_cookie_is_returned_without_printing_secret(monkeypatch, capsys, source):
    token = 'synthetic-secret'
    monkeypatch.setenv('LODESTONE_COOKIE', token)
    monkeypatch.setattr(report.sys.stdin, 'isatty', lambda: True)
    monkeypatch.setattr(report.getpass, 'getpass', lambda *a: token)
    args = SimpleNamespace(mode='full', cookie=token if source == 'argument' else None,
                           cookie_env=source == 'environment')
    assert report.resolve_cookie(args) == token
    captured = capsys.readouterr()
    assert token not in captured.out + captured.err


def test_noninteractive_full_mode_does_not_downgrade(monkeypatch):
    monkeypatch.setattr(report.sys.stdin, 'isatty', lambda: False)
    with pytest.raises(SystemExit, match='No TTY'):
        report.resolve_cookie(SimpleNamespace(mode='full', cookie=None, cookie_env=False))


def test_public_config_blocks_standalone_private_quest_scrape(monkeypatch, tmp_path):
    path = configured(tmp_path, 'public')
    out = tmp_path / 'quest_history.md'
    out.write_text('Previous history')
    monkeypatch.setenv('LODESTONE_COOKIE', 'synthetic')
    monkeypatch.setattr(report, 'fetch_quests', lambda *a, **kw: pytest.fail('private fetch'))
    monkeypatch.setattr(sys, 'argv', ['scionbook_quest_history.py', '--config', str(path),
                                    '--cookie-env', '--out', str(out)])
    with pytest.raises(SystemExit, match='requires configured full mode'):
        history.main()
    assert out.read_text() == 'Previous history'


def test_setup_and_scraper_use_shared_identity_without_shared_cookie(monkeypatch):
    assert setup.BASE == report.BASE == LODESTONE + '/character'
    monkeypatch.setitem(report.HEADERS, 'Cookie', 'synthetic')
    assert setup.LODESTONE_HEADERS['User-Agent'] == report.HEADERS['User-Agent'] == USER_AGENT
    assert 'Cookie' not in HTTP_HEADERS and 'Cookie' not in LODESTONE_HEADERS
