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
    (tmp_path / "AGENTS.md").write_text("Hidden \u202e instruction")
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
