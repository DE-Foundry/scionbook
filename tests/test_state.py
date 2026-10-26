"""Same-chat persistence with synthetic state only; no accounts, network, or models."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scionbook_recap as store
import scionbook_state as state


@pytest.fixture
def player(tmp_path):
    config = {"version": 1, "character_id": "12345", "name": "Example Adventurer",
              "world": "Example World", "data_center": "Example DC", "timezone": "UTC",
              "mode": "public", "preferences": {"spoilers": "minimal", "gameplay": {
                  "priorities": ["Exploration"], "combat_leveling_routine": ["One available duty"]}}}
    (tmp_path / "scionbook.json").write_text(json.dumps(config), encoding="utf-8")
    (tmp_path / "SCIONBOOK_MEMORY.md").write_text("# Memory v1\nExisting dated report\n")
    (tmp_path / "SCIONBOOK_DAILY_WEEKLY_CHECKLIST.md").write_text("# Checklist\n- [ ] Reusable routine\n")
    (tmp_path / "status.json").write_text('{"fetched_at_utc":"2026-01-01T00:00:00Z"}')
    for name in (store.SKILL, "docs/gameplay-preferences.md"):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("Synthetic instructions\n")
    return tmp_path


def proposal(name, content):
    return {"status": "proposed", "changes": [{"path": name, "content": content}]}


def test_immediate_preference_save_preserves_identity_reports_and_snapshot(player):
    before = store.snapshot(player)
    config = json.loads(before["scionbook.json"])
    config["preferences"]["gameplay"]["priorities"] = ["Crafting", "Exploration"]
    token = state.prepare(player)
    result = state.apply(token, proposal("scionbook.json", json.dumps(config)), player)
    assert result["status"] == "applied"
    after = store.snapshot(player)
    assert json.loads(after.pop("scionbook.json")) == config
    assert after == {name: value for name, value in before.items() if name != "scionbook.json"}
    assert not list(player.glob(".scionbook-state-*"))
    assert not list(player.glob(".scionbook-recap-*"))


def test_repeated_report_is_noop_without_timestamp_or_version_churn(player):
    token = state.prepare(player)
    path = player / "SCIONBOOK_MEMORY.md"
    unchanged = proposal(path.name, path.read_text())
    before = path.stat().st_mtime_ns
    assert state.apply(token, unchanged, player)["status"] == "unchanged"
    assert path.stat().st_mtime_ns == before


def test_multi_file_report_save_leaves_generated_sources_unchanged(player):
    before = (player / "status.json").read_bytes()
    token = state.prepare(player)
    update = {"status": "proposed", "changes": [
        {"path": "SCIONBOOK_MEMORY.md", "content": "# Memory v2\n2026-01-02: Reported quest clear\n"},
        {"path": "SCIONBOOK_DAILY_WEEKLY_CHECKLIST.md", "content":
         "# Checklist\n- [ ] Reusable routine\n\n2026-01-02\n- [x] Reported quest clear\n"}]}
    assert state.apply(token, update, player)["status"] == "applied"
    assert (player / "status.json").read_bytes() == before
    assert "- [ ] Reusable routine" in (player / "SCIONBOOK_DAILY_WEEKLY_CHECKLIST.md").read_text()


@pytest.mark.parametrize("name", ["AGENTS.md", "status.json", "quest_history.md", "../outside", "local/arbitrary.json"])
def test_shared_source_generated_data_and_arbitrary_paths_are_not_outputs(player, name):
    before = store.snapshot(player)
    token = state.prepare(player)
    with pytest.raises(ValueError):
        state.apply(token, proposal(name, "Unapproved output"), player)
    assert store.snapshot(player) == before
    state.cancel(token, player)


def test_preference_save_cannot_change_character_or_workspace_identity(player):
    token = state.prepare(player)
    config = json.loads((player / "scionbook.json").read_text())
    config["name"] = "Other Adventurer"
    with pytest.raises(ValueError, match="character configuration"):
        state.apply(token, proposal("scionbook.json", json.dumps(config)), player)


@pytest.mark.parametrize("name", ["scionbook.json", "SCIONBOOK_MEMORY.md", "status.json", "docs/gameplay-preferences.md"])
def test_edit_prepared_before_concurrent_change_does_not_overwrite_it(player, name):
    token = state.prepare(player)
    path = player / name
    newer = path.read_text() + "\n"
    path.write_text(newer)
    with pytest.raises(RuntimeError, match="sources changed"):
        state.apply(token, proposal("SCIONBOOK_MEMORY.md", "# Memory v2\nOlder proposal\n"), player)
    assert path.read_text() == newer
    assert state.edit_directory(player, token).exists()
    state.cancel(token, player)


def test_large_combined_originals_are_supported_without_increasing_per_file_limit(player):
    (player / "status.json").write_text("s" * 1_100_000)
    (player / "SCIONBOOK_MEMORY.md").write_text("m" * 1_100_000)
    token = state.prepare(player)
    update = proposal("SCIONBOOK_MEMORY.md", (player / "SCIONBOOK_MEMORY.md").read_text())
    assert state.apply(token, update, player)["status"] == "unchanged"


@pytest.mark.parametrize("token", ["../outside", "/tmp/outside", ".", "a/b", "a" * 40])
def test_tokens_cannot_select_arbitrary_directories(player, token):
    with pytest.raises(ValueError):
        state.cancel(token, player)


def test_git_privacy_checks_outputs_and_temporary_storage(player):
    subprocess.run(["git", "init", "-q", str(player)], check=True)
    (player / ".gitignore").write_text("\n".join(store.OUTPUTS) + "\n")
    with pytest.raises(ValueError, match="untracked and ignored"):
        state.prepare(player)
    with (player / ".gitignore").open("a") as output:
        output.write(".scionbook-*\n/local/\n")
    token = state.prepare(player)
    state.cancel(token, player)
    subprocess.run(["git", "-C", str(player), "add", "-f", "scionbook.json"], check=True)
    with pytest.raises(ValueError, match="untracked and ignored"):
        state.prepare(player)


def test_privacy_rules_are_checked_again_before_apply(player):
    subprocess.run(["git", "init", "-q", str(player)], check=True)
    ignore = player / ".gitignore"
    ignore.write_text("\n".join(store.OUTPUTS) + "\n.scionbook-*\n/local/\n")
    token = state.prepare(player)
    ignore.write_text("")
    before = (player / "SCIONBOOK_MEMORY.md").read_text()
    with pytest.raises(ValueError, match="untracked and ignored"):
        state.apply(token, proposal("SCIONBOOK_MEMORY.md", "# Memory v2\nReport\n"), player)
    assert (player / "SCIONBOOK_MEMORY.md").read_text() == before


def test_release_copy_inside_another_git_checkout_still_checks_privacy(player):
    subprocess.run(["git", "init", "-q", str(player)], check=True)
    nested = player / "extracted"
    nested.mkdir()
    with pytest.raises(ValueError, match="untracked and ignored"):
        state.check_private_destinations(nested)


def test_cancel_does_not_change_player_files(player):
    before = store.snapshot(player)
    token = state.prepare(player)
    state.cancel(token, player)
    assert store.snapshot(player) == before
    assert not list(player.glob(".scionbook-state-*"))
