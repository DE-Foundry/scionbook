"""Clean-release export: fresh history, no personal files or identifying terms."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import export_release as export


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout


@pytest.fixture
def source(tmp_path, monkeypatch):
    repo = tmp_path / "source"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("Neutral project text\n")
    (repo / "templates").mkdir()
    (repo / "templates" / "SCIONBOOK_MEMORY.md").write_text("# Template\n")
    (repo / ".gitignore").write_text("scionbook.json\nstatus.json\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "first")
    (repo / "README.md").write_text("Second revision\n")
    git(repo, "commit", "-q", "-am", "second")
    monkeypatch.setattr(export, "REPO", repo)
    # CI runners have no global git identity for the release commit.
    for key, value in (("GIT_AUTHOR_NAME", "Test"), ("GIT_COMMITTER_NAME", "Test"),
                       ("GIT_AUTHOR_EMAIL", "test@example.invalid"),
                       ("GIT_COMMITTER_EMAIL", "test@example.invalid")):
        monkeypatch.setenv(key, value)
    return repo


def test_export_has_single_fresh_commit_and_only_head_files(source, tmp_path):
    (source / "status.json").write_text(json.dumps(
        {"character_id": "99999999", "character": {"name": "Sample Person"},
         "retainers": [{"name": "Sample-retainer"}]}))
    out = tmp_path / "release"
    export.main([str(out), "--commit"])
    assert git(out, "rev-list", "--count", "HEAD").strip() == "1"
    assert (out / "README.md").read_text() == "Second revision\n"
    assert not (out / "status.json").exists()


def test_identifying_term_in_committed_file_refuses_export(source, tmp_path):
    (source / "scionbook.json").write_text(json.dumps({"character_id": "12345678", "name": "Sample Person"}))
    (source / "notes.md").write_text("Planned with sample person yesterday\n")
    git(source, "add", "notes.md")
    git(source, "commit", "-q", "-m", "leak")
    out = tmp_path / "release"
    with pytest.raises(SystemExit, match="refused"):
        export.main([str(out)])
    assert not out.exists()


def test_denylist_file_terms_are_checked(source, tmp_path):
    (source / "doc.md").write_text("Retainer Placeholder-name\n")
    git(source, "add", "doc.md")
    git(source, "commit", "-q", "-m", "doc")
    deny = tmp_path / "deny.txt"
    deny.write_text("# comment\nplaceholder-NAME\n")
    with pytest.raises(SystemExit, match="refused"):
        export.main([str(tmp_path / "release"), "--deny", str(deny)])


def test_tracked_personal_state_file_refuses_export(source, tmp_path):
    (source / "nested").mkdir()
    (source / "nested" / "status.json.bak").write_text("{}")
    git(source, "add", "-f", "nested/status.json.bak")
    git(source, "commit", "-q", "-m", "backup")
    with pytest.raises(SystemExit, match="refused"):
        export.main([str(tmp_path / "release")])


def test_dirty_tree_or_nonempty_destination_is_rejected(source, tmp_path):
    busy = tmp_path / "busy"
    busy.mkdir()
    (busy / "x").write_text("x")
    with pytest.raises(SystemExit):
        export.main([str(busy)])
    (source / "README.md").write_text("uncommitted\n")
    with pytest.raises(SystemExit):
        export.main([str(tmp_path / "release")])


def test_short_terms_are_ignored_to_avoid_false_matches():
    assert export.scan({"a.py": b"import os\n"}, {"os", "12"}) == []


def test_this_repository_tracks_no_personal_state():
    tracked = git(Path(__file__).resolve().parent.parent, "ls-files").splitlines()
    assert export.personal_paths(tracked) == []
