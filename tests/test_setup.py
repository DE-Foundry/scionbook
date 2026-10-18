"""Character onboarding and local-state isolation; no live services or cookies."""
import json
import pathlib
import sys
from types import SimpleNamespace

import pytest
import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import scionbook_config as config
import scionbook_setup as setup
import scionbook_report as report
import scionbook_quest_history as history
import scionbook_quest_mats as mats

IDENTITY = {"character_id": "12345", "name": "Example Adventurer",
            "world": "Example World", "data_center": "Example DC"}
PROFILE = '<p class="frame__chara__name">Example Adventurer</p><p class="frame__chara__world">Example World [Example DC]</p>'


def entry(cid="12345", name="Example Adventurer", world="Example World"):
    return f'<a class="entry__link" href="/lodestone/character/{cid}/"><p class="entry__name">{name}</p><p class="entry__world">{world} [Example DC]</p></a>'


class Session:
    def __init__(self, *pages):
        self.pages = iter(pages)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        page = next(self.pages)
        if isinstance(page, Exception):
            raise page
        return SimpleNamespace(text=page, raise_for_status=lambda: None)


def test_search_filters_partial_names_and_other_worlds():
    html = entry() + entry("999", "Example Adventurer Jr") + entry("555", world="Other World")
    assert setup.parse_search(html, "  example   adventurer ", "example world") == [IDENTITY]


def test_lookup_paginates_and_verifies_exact_profile(monkeypatch):
    monkeypatch.setattr(setup.time, "sleep", lambda _: None)
    session = Session(entry("999", "Other Person") + '<a class="btn__pager__next"></a>',
                      entry() + '<a class="btn__pager__next btn__pager__no"></a>', PROFILE)
    assert setup.find_character(session, IDENTITY["name"], IDENTITY["world"]) == IDENTITY
    assert session.calls[1][1]["params"]["page"] == 2
    assert session.calls[0][1]["params"]["worldname"] == IDENTITY["world"]
    assert session.calls[-1][0].endswith("/12345/")


@pytest.mark.parametrize("html", ["", entry("999", "Other Person"), entry() + entry("999")])
def test_lookup_does_not_guess_when_missing_or_ambiguous(html):
    with pytest.raises(ValueError, match="exact matches"):
        setup.find_character(Session(html), IDENTITY["name"], IDENTITY["world"])


@pytest.mark.parametrize("html", ["<html>Maintenance</html>", PROFILE.replace("Example World", "Other World"), PROFILE.replace("Example Adventurer", "Other Person")])
def test_profile_verification_rejects_missing_or_mismatched_identity(html):
    with pytest.raises(ValueError):
        setup.verify_profile(Session(html), "12345", IDENTITY["name"], IDENTITY["world"])


def test_lookup_network_failure_propagates():
    with pytest.raises(requests.Timeout):
        setup.find_character(Session(requests.Timeout()), IDENTITY["name"], IDENTITY["world"])


@pytest.mark.parametrize("value", ["12345", "https://na.finalfantasyxiv.com/lodestone/character/12345/", "https://eu.finalfantasyxiv.com/lodestone/character/12345"])
def test_profile_id_accepts_official_links_and_numeric_ids(value):
    assert setup.profile_id(value) == "12345"


@pytest.mark.parametrize("value", ["0", "-1", "https://evil.example/lodestone/character/12345/", "https://na.finalfantasyxiv.com.evil.example/lodestone/character/12345/", "https://user@na.finalfantasyxiv.com/lodestone/character/12345/", "http://na.finalfantasyxiv.com/lodestone/character/12345/"])
def test_profile_id_rejects_untrusted_urls(value):
    with pytest.raises(ValueError):
        setup.profile_id(value)


def test_first_setup_initializes_templates_without_fake_snapshot(tmp_path):
    saved = setup.initialize(IDENTITY, "UTC", "public", tmp_path)
    assert config.load_config(tmp_path / "scionbook.json") == saved
    assert (tmp_path / "SCIONBOOK_MEMORY.md").exists()
    assert (tmp_path / "SCIONBOOK_DAILY_WEEKLY_CHECKLIST.md").exists()
    assert not (tmp_path / "status.json").exists()
    assert not (tmp_path / "quest_history.md").exists()
    assert "cookie" not in json.dumps(saved).lower()


def test_repeat_setup_preserves_reports_preferences_mode_and_timezone(tmp_path):
    saved = setup.initialize(IDENTITY, "Europe/London", "public", tmp_path)
    saved["preferences"]["goals"] = ["Explore"]
    (tmp_path / "scionbook.json").write_text(json.dumps(saved))
    memory = tmp_path / "SCIONBOOK_MEMORY.md"
    memory.write_text("A newer player report")
    snapshot = tmp_path / "status.json"
    snapshot.write_text("Existing snapshot")
    assert setup.initialize(IDENTITY, directory=tmp_path) == saved
    assert memory.read_text() == "A newer player report"
    assert snapshot.read_text() == "Existing snapshot"


def test_setup_refuses_another_character_without_overwriting(tmp_path):
    setup.initialize(IDENTITY, "UTC", "full", tmp_path)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises(ValueError, match="Another character"):
        setup.initialize({**IDENTITY, "character_id": "99999"}, "UTC", "full", tmp_path)
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


def test_setup_refuses_orphaned_player_state(tmp_path):
    (tmp_path / "status.json").write_text("Existing data")
    with pytest.raises(ValueError, match="Unconfigured player files"):
        setup.initialize(IDENTITY, "UTC", "full", tmp_path)
    assert list(tmp_path.iterdir()) == [tmp_path / "status.json"]


def test_invalid_timezone_writes_nothing(tmp_path):
    with pytest.raises(ValueError, match="timezone"):
        setup.initialize(IDENTITY, "Not/AZone", "full", tmp_path)
    assert not list(tmp_path.iterdir())


def test_config_requires_explicit_identity_or_setup(tmp_path):
    absent = tmp_path / "absent.json"
    with pytest.raises(ValueError, match="setup"):
        config.resolve_identity(config_path=absent)
    with pytest.raises(ValueError, match="together"):
        config.resolve_identity("12345", config_path=absent)
    assert config.resolve_identity("12345", "World", "DC", absent) == ("12345", "World", "DC")
    setup.initialize(IDENTITY, "UTC", "full", tmp_path)
    assert config.resolve_identity(config_path=tmp_path / "scionbook.json") == ("12345", "Example World", "Example DC")


@pytest.mark.parametrize("value", [[], {}, {"version": 100}, {"version": 1, **IDENTITY, "timezone": "UTC", "mode": "full", "preferences": []}])
def test_config_rejects_invalid_schema(tmp_path, value):
    path = tmp_path / "scionbook.json"
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        config.load_config(path)


def run_history(monkeypatch, tmp_path, total, quests, character_id="12345"):
    snapshot = {"character_id": character_id, "character": {"name": "Example Adventurer"},
                "world": "Example World", "fetched_at_utc": "2025-01-01T00:00:00+00:00",
                "quests": {"total_completed": total, "recent": quests}}
    status = tmp_path / "status.json"
    status.write_text(json.dumps(snapshot))
    monkeypatch.setattr(sys, "argv", ["scionbook_quest_history.py", "--from-status", "--config", str(tmp_path / "scionbook.json"), "--status", str(status), "--out", str(tmp_path / "history.md")])
    history.main()


def test_history_uses_snapshot_identity_for_zero_quests(monkeypatch, tmp_path):
    run_history(monkeypatch, tmp_path, 0, [])
    output = (tmp_path / "history.md").read_text()
    assert "Example Adventurer (Example World)" in output
    assert "**0** quests" in output


@pytest.mark.parametrize("total", [None, 4])
def test_incomplete_or_public_history_preserves_previous_output(monkeypatch, tmp_path, total):
    output = tmp_path / "history.md"
    output.write_text("Previous validated history")
    with pytest.raises(SystemExit, match="Incomplete or unavailable"):
        run_history(monkeypatch, tmp_path, total, [])
    assert output.read_text() == "Previous validated history"


def test_history_rejects_other_character(monkeypatch, tmp_path):
    setup.initialize(IDENTITY, "UTC", "full", tmp_path)
    with pytest.raises(SystemExit, match="different character"):
        run_history(monkeypatch, tmp_path, 0, [], "99999")
    assert not (tmp_path / "history.md").exists()


def test_quest_protection_uses_supplied_tiers(tmp_path, monkeypatch):
    source = tmp_path / "quest_turnins.json"
    source.write_text(json.dumps({"Carpenter": {"10": ["Example Turn-in"]}}))
    turns = mats.load_turnins(source)
    assert turns == {"Carpenter": {10: ["Example Turn-in"]}}
    monkeypatch.setattr(mats, "walk_closure", lambda name, *args: {"name": name, "is_craftable": True, "ingredients": [{"name": "Example Material", "is_craftable": False, "ingredients": []}]})
    result = mats.build_closure(turns)
    assert result["tiers_covered"] == {"Carpenter": [10]}
    assert set(result["protected_materials"]) == {"Example Turn-in", "Example Material"}


@pytest.mark.parametrize("value", [{}, [], {"Carpenter": []}, {"Carpenter": {"x": ["Item"]}}, {"Carpenter": {"10": []}}, {"Carpenter": {"10": [""]}}])
def test_invalid_protection_input_is_rejected(tmp_path, value):
    source = tmp_path / "quest_turnins.json"
    source.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        mats.load_turnins(source)


def test_unknown_turnin_preserves_previous_protection(monkeypatch, tmp_path):
    source, output = tmp_path / "turnins.json", tmp_path / "quest_mats.json"
    source.write_text(json.dumps({"Carpenter": {"10": ["Bad Item"]}}))
    output.write_text("Previous protection")
    monkeypatch.setattr(mats, "walk_closure", lambda name, *args: {"name": name, "is_craftable": False, "ingredients": []})
    monkeypatch.setattr(sys, "argv", ["scionbook_quest_mats.py", "--turnins", str(source), "--out", str(output)])
    assert mats.main() == 1
    assert output.read_text() == "Previous protection"


def test_anonymous_report_skips_private_requests_and_clears_old_report(monkeypatch, tmp_path):
    out, cleanup = tmp_path / "status.json", tmp_path / "cleanup.md"
    cleanup.write_text("An old inventory plan")
    soup = BeautifulSoup(PROFILE, "html.parser")
    monkeypatch.setattr(report, "fetch", lambda *args, **kwargs: (soup, PROFILE))
    monkeypatch.setattr(report, "parse_class_job", lambda *args: {"Archer": {"level": 1}})
    def private_fetch(*args, **kwargs):
        pytest.fail("Public mode requested a private page")
    monkeypatch.setattr(report, "fetch_quests", private_fetch)
    monkeypatch.setattr(report, "fetch_currency", private_fetch)
    monkeypatch.setattr(report, "HEADERS", {"Cookie": "synthetic stale header"})
    monkeypatch.setattr(sys, "argv", ["scionbook_report.py", "--anon", "--fast", "--id", "12345", "--world", "Example World", "--dc", "Example DC", "--out", str(out), "--report", str(cleanup)])
    report.main()
    data = json.loads(out.read_text())
    assert data["character_id"] == "12345"
    assert data["world"] == "Example World" and data["data_center"] == "Example DC"
    assert data["authenticated"] is False
    assert data["quests"]["total_completed"] is None and data["currencies"] is None
    assert cleanup.read_text() == ""
    assert "Cookie" not in report.HEADERS


def test_search_supports_mobile_cards_and_deduplicates_identity():
    mobile = entry().replace("entry__link", "entry__chara__link")
    assert setup.parse_search(mobile, IDENTITY["name"], IDENTITY["world"]) == [IDENTITY]
    assert setup.parse_search(entry() + mobile, IDENTITY["name"], IDENTITY["world"]) == [IDENTITY]


def test_failed_initialization_can_be_retried_without_orphaned_files(monkeypatch, tmp_path):
    def fail_replace(*args):
        raise OSError("simulated disk failure")
    monkeypatch.setattr(pathlib.Path, "replace", fail_replace)
    with pytest.raises(OSError, match="disk failure"):
        setup.initialize(IDENTITY, "UTC", "full", tmp_path)
    assert not list(tmp_path.iterdir())


def test_report_rejects_wrong_pricing_data_center(monkeypatch, tmp_path):
    soup = BeautifulSoup(PROFILE, "html.parser")
    monkeypatch.setattr(report, "fetch", lambda *args, **kwargs: (soup, PROFILE))
    out = tmp_path / "status.json"
    out.write_text("Previous snapshot")
    monkeypatch.setattr(sys, "argv", ["scionbook_report.py", "--anon", "--id", "12345", "--world", "Example World", "--dc", "Wrong DC", "--out", str(out)])
    with pytest.raises(SystemExit, match="differs from configuration"):
        report.main()
    assert out.read_text() == "Previous snapshot"


def test_pre_setup_preferences_import_once(tmp_path):
    seed = tmp_path / 'local' / 'gameplay-preferences.json'
    seed.parent.mkdir()
    preferences = {'gameplay': {'priorities': ['Explore optional areas'],
                               'combat_leveling_routine': ['Use a chosen activity when available']}}
    seed.write_text(json.dumps({'preferences': preferences}))
    saved = setup.initialize(IDENTITY, directory=tmp_path)
    assert saved['preferences']['gameplay'] == preferences['gameplay']
    assert saved['preferences']['inventory_policy'] == 'conservative'
    assert not (tmp_path / 'status.json').exists()
    seed.write_text('invalid obsolete seed')
    assert setup.initialize(IDENTITY, directory=tmp_path) == saved


@pytest.mark.parametrize('seed', [
    {'preferences': {'gameplay': []}},
    {'preferences': {'gameplay': {'priorities': 'Explore'}}},
    {'preferences': {'gameplay': {'combat_leveling_routine': ['']}}},
    {'preferences': {}, 'character_id': '999'},
    [],
])
def test_invalid_seed_does_not_initialize_state(tmp_path, seed):
    path = tmp_path / 'local' / 'gameplay-preferences.json'
    path.parent.mkdir()
    path.write_text(json.dumps(seed))
    with pytest.raises(ValueError):
        setup.initialize(IDENTITY, directory=tmp_path)
    assert not (tmp_path / 'scionbook.json').exists()
    assert not (tmp_path / 'SCIONBOOK_MEMORY.md').exists()


@pytest.mark.parametrize('preferences', [
    {}, {'goals': ['Explore'], 'custom': True},
    {'gameplay': {}}, {'gameplay': {'priorities': [], 'combat_leveling_routine': []}},
])
def test_optional_gameplay_preferences_preserve_legacy(preferences):
    assert config.validate_preferences(preferences) == preferences


@pytest.mark.parametrize('gameplay', [None, [], {'priorities': [42]},
                                      {'priorities': ['  ']}, {'combat_leveling_routine': False}])
def test_invalid_gameplay_preferences_rejected(gameplay):
    with pytest.raises(ValueError):
        config.validate_preferences({'gameplay': gameplay})


def test_repeat_setup_restores_missing_preferences_without_seed(tmp_path):
    saved = setup.initialize(IDENTITY, directory=tmp_path)
    del saved['preferences']
    (tmp_path / 'scionbook.json').write_text(json.dumps(saved))
    seed = tmp_path / 'local' / 'gameplay-preferences.json'
    seed.parent.mkdir()
    seed.write_text('invalid ignored seed')
    result = setup.initialize(IDENTITY, directory=tmp_path)
    assert result['preferences'] == config.default_preferences()


@pytest.mark.parametrize('field,value', [('goals', 'x'), ('retainer_order', 5),
                                         ('spoilers', None), ('goals', ['Explore'])])
def test_seed_rejects_non_gameplay_preferences(tmp_path, field, value):
    seed = tmp_path / 'local' / 'gameplay-preferences.json'
    seed.parent.mkdir()
    seed.write_text(json.dumps({'preferences': {field: value}}))
    with pytest.raises(ValueError, match='only preferences.gameplay'):
        setup.initialize(IDENTITY, directory=tmp_path)
    assert not (tmp_path / 'scionbook.json').exists()
    assert not (tmp_path / 'SCIONBOOK_MEMORY.md').exists()


@pytest.mark.parametrize('raw', [
    '{"preferences":{"gameplay":{}},"preferences":{}}',
    '{"preferences":{"gameplay":{"priorities":[],"priorities":["Explore"]}}}',
    '{"preferences":{"gameplay":{"extra":NaN}}}',
])
def test_invalid_seed_json_does_not_initialize(tmp_path, raw):
    seed = tmp_path / 'local' / 'gameplay-preferences.json'
    seed.parent.mkdir()
    seed.write_text(raw)
    with pytest.raises(ValueError):
        setup.initialize(IDENTITY, directory=tmp_path)
    assert not (tmp_path / 'scionbook.json').exists()
    assert not (tmp_path / 'SCIONBOOK_MEMORY.md').exists()


def test_config_loader_rejects_duplicate_keys(tmp_path):
    saved = setup.initialize(IDENTITY, directory=tmp_path)
    path = tmp_path / 'scionbook.json'
    path.write_text(json.dumps(saved)[:-1] + ',"preferences":{}}')
    with pytest.raises(ValueError, match='Cannot read configuration'):
        config.load_config(path)
