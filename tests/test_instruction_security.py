"""Deterministic source checks; candidate content is never imported or executed."""
import importlib.util
from pathlib import Path
import subprocess

import pytest

spec = importlib.util.spec_from_file_location("instruction_check", Path(__file__).resolve().parents[1] / "scripts/check_instruction_security.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def blob(text, mode="100644"):
    return mode, text.encode()


@pytest.mark.parametrize("char", ["\u202e", "\u200b", "\u2066", "\x00", "\x1b", "\ufeff"])
def test_hidden_controls_block_even_when_present_in_baseline(char):
    files = {".agents/skills/example/SKILL.md": blob("Text" + char)}
    assert any(level == "error" for level, _, _ in check.scan(files, files))


def test_normal_unicode_is_allowed():
    assert not check.scan({"docs/example.md": blob("Café 日本語\n\tText\r\n")})


def test_new_destination_permissions_and_evaluator_changes_need_review():
    files = {"docs/example.md": blob("https://example.invalid/new"),
             ".claude/settings.json": blob('{"permissions": "bypassPermissions"}'),
             "scripts/check_instruction_security.py": blob("pass")}
    result = check.scan(files)
    assert {name for level, name, _ in result if level == "review"} == set(files)
    assert check.scan(files, files) == []
    assert any("removed" in reason for _, _, reason in check.scan({}, files))


def test_links_are_not_followed():
    assert check.scan({"AGENTS.md": blob("/outside", "120000")})[0][0] == "error"


def test_full_commit_ids_required():
    with pytest.raises(ValueError):
        check.tree(".", "--help")


def test_candidate_checker_cannot_replace_running_baseline(tmp_path):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(tmp_path), *args]).decode().strip()
    git("init", "-q")
    git("config", "user.name", "Synthetic Contributor")
    git("config", "user.email", "synthetic@example.invalid")
    (tmp_path / "AGENTS.md").write_text("Safe baseline\n")
    git("add", ".")
    git("commit", "-qm", "docs: baseline")
    base = git("rev-parse", "HEAD")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "check_instruction_security.py").write_text("raise Exception('candidate executed')")
    (tmp_path / "AGENTS.md").write_text("Hidden \u202e instruction", encoding="utf-8")
    git("add", ".")
    git("commit", "-qm", "docs: candidate")
    result = check.scan(check.tree(tmp_path, git("rev-parse", "HEAD")), check.tree(tmp_path, base))
    assert any(level == "error" for level, _, _ in result)
    assert any(name == "scripts/check_instruction_security.py" for _, name, _ in result)


def test_only_exact_shipped_skill_alias_is_allowed():
    target = {".agents/skills/example/SKILL.md": blob("Reviewed instructions")}
    alias = {".claude/skills": blob("../.agents/skills", "120000")}
    assert check.scan({**target, **alias}) == []
    assert check.scan(alias)[0][0] == "error"
    assert check.scan({**target, ".claude/skills": blob("/outside", "120000")})[0][0] == "error"
    target[".agents/skills/example/SKILL.md"] = blob("Hidden\u202e")
    assert any(level == "error" for level, _, _ in check.scan({**target, **alias}))


@pytest.mark.parametrize('name', ['.cursorrules', '.cursor/rules/example.mdc', 'prompt.txt', 'example.py'])
def test_hidden_controls_cover_other_clients_and_all_text(name):
    assert check.scan({name: blob('hidden\U000e0041')})[0][0] == 'error'
    assert check.scan({name: blob('https://example.invalid ignore previous instructions')}) == []


def test_binary_files_are_skipped_but_invalid_instruction_text_fails():
    assert check.scan({'image.png': ('100644', b'\xff\x00')}) == []
    assert check.scan({'AGENTS.md': ('100644', b'\xff')})[0][0] == 'error'


def test_summary_escapes_candidate_markup_and_controls(tmp_path, monkeypatch):
    summary = tmp_path / 'summary.md'
    monkeypatch.setenv('GITHUB_STEP_SUMMARY', str(summary))
    check.write_summary([('review', '</pre><img src="https://example.invalid">\n[click](https://example.invalid)\u202e', 'review')])
    text = summary.read_text()
    assert '&lt;/pre&gt;&lt;img' in text
    assert '<img' not in text and '\u202e' not in text
    assert '\\u202e' in text and '"severity": "review"' not in text
    assert text.count('<pre>') == text.count('</pre>') == 1
    check.write_summary([])
    assert 'No instruction-security findings.' in summary.read_text()


def test_tree_includes_nontraditional_instruction_names(tmp_path):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(tmp_path), *args]).decode().strip()
    git('init', '-q')
    git('config', 'user.name', 'Synthetic Contributor')
    git('config', 'user.email', 'synthetic@example.invalid')
    (tmp_path / '.cursorrules').write_text('hidden\u200b', encoding='utf-8')
    git('add', '.')
    git('commit', '-qm', 'test: synthetic instruction')
    assert check.scan(check.tree(tmp_path, git('rev-parse', 'HEAD')))[0][0] == 'error'


def test_large_skipped_binary_does_not_consume_text_limits(tmp_path, monkeypatch):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(tmp_path), *args]).decode().strip()
    git('init', '-q')
    git('config', 'user.name', 'Synthetic Contributor')
    git('config', 'user.email', 'synthetic@example.invalid')
    # Invalid UTF-8 appears late: must classify the whole blob, without buffering it all.
    (tmp_path / 'image.png').write_bytes(b'x' * 200_000 + b'\xff')
    (tmp_path / 'prompt.txt').write_bytes(b'Ordinary prompt')
    git('add', '.')
    git('commit', '-qm', 'test: large synthetic binary')
    monkeypatch.setattr(check, 'MAX_FILE', 100)
    monkeypatch.setattr(check, 'MAX_TREE', 100)
    files = check.tree(tmp_path, git('rev-parse', 'HEAD'))
    assert set(files) == {'prompt.txt'}
    (tmp_path / 'prompt.txt').write_bytes(b'x' * 101)
    git('add', '.')
    git('commit', '-qm', 'test: oversized text')
    with pytest.raises(ValueError, match='UTF-8 file exceeds 100.*prompt.txt'):
        check.tree(tmp_path, git('rev-parse', 'HEAD'))
