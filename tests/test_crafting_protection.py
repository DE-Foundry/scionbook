"""Persistent materials survive sessions, reuse research, and shrink with evidence."""
import copy
import json
import pathlib
import sys

import pytest
import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import crafting_protection as cp
import scionbook_quest_mats as mats
import scionbook_report as report

STAMP = "2026-01-01T00:00:00+00:00"


def quest(qid, level, item, job="Carpenter"):
    return {"qid": qid, "name": f"Quest {qid}", "job": job, "level": level,
            "kind": "ordinary", "sources": ["https://example.invalid/quest"],
            "verified_at_utc": STAMP,
            "turnins": [{"name": item, "quantity": 1, "hq": False}]}


def plan():
    return {"version": 2, "character_id": "12345", "coverage": {"Carpenter": 20, "Weaver": 20},
            "quests": [quest("a", 5, "Old Craft"), quest("b", 10, "New Craft"),
                       quest("c", 5, "Other Craft", "Weaver")], "keeps": []}


def snapshot(level=5, completed=()):
    return {"character_id": "12345", "authenticated": True, "fetched_at_utc": STAMP,
            "jobs": {"crafters": {"Carpenter": level, "Weaver": 5}},
            "quests": {"total_completed": len(completed),
                       "recent": [{"qid": qid, "name": f"Quest {qid}"} for qid in completed]}}


@pytest.fixture
def recipes(monkeypatch):
    calls = []
    def find(name, session):
        calls.append(name)
        if name not in ("Old Craft", "New Craft", "Other Craft"):
            return None
        return {"Ingredient": [{"row_id": 1, "fields": {"Name": "Shared Ore"}},
                               {"row_id": 2, "fields": {"Name": name + " Material"}}],
                "AmountResult": 1, "AmountIngredient": [1, 2]}
    monkeypatch.setattr(mats, "find_recipe", find)
    monkeypatch.setattr(mats.time, "sleep", lambda _: None)
    return calls


def test_saved_cache_reused_across_process_style_json_roundtrip(recipes, monkeypatch):
    previous = cp.reconcile(plan(), snapshot())
    previous = json.loads(json.dumps(previous))
    monkeypatch.setattr(mats, "find_recipe", lambda *a: pytest.fail("cached recipes must not be fetched"))
    current = cp.reconcile(plan(), snapshot(), previous)
    assert current["protected_materials"] == previous["protected_materials"]
    assert current["added_materials"] == current["released_materials"] == []
    assert current["material_reasons"]["Shared Ore"][0]["qid"] == "a"
    assert current["quests"][0]["sources"] == plan()["quests"][0]["sources"]


def test_level_up_adds_next_tier_but_keeps_unfinished_lower_quest(recipes):
    previous = cp.reconcile(plan(), snapshot())
    recipes.clear()
    current = cp.reconcile(plan(), snapshot(10), previous)
    assert "New Craft" in current["added_materials"]
    assert "Old Craft" in current["protected_materials"]
    assert "Shared Ore" not in recipes
    assert "Old Craft" not in recipes
    assert set(recipes) == {"New Craft", "New Craft Material"}


def test_completion_releases_unique_materials_but_keeps_shared_and_explicit(recipes):
    source = plan()
    source["keeps"] = [{"name": "Old Craft Material", "reason": "future crafting goal"}]
    previous = cp.reconcile(source, snapshot())
    current = cp.reconcile(source, snapshot(10, ("a",)), previous)
    assert "Old Craft" in current["released_materials"]
    assert {"Shared Ore", "Old Craft Material", "New Craft"} <= set(current["protected_materials"])
    assert current["material_reasons"]["Old Craft Material"][0]["kind"] == "explicit_keep"
    assert {r["qid"] for r in current["material_reasons"]["Shared Ore"]} == {"b", "c"}
    assert "Old Craft" in current["recipe_cache"]  # reference retained for reuse


def test_level_limited_keep_expires_independently_of_quest_keeps(recipes):
    source = plan()
    source["keeps"] = [{"name": "Leveling Material", "reason": "leveling", "job": "Carpenter", "until_level": 10}]
    previous = cp.reconcile(source, snapshot())
    current = cp.reconcile(source, snapshot(10), previous)
    assert "Leveling Material" in current["released_materials"]
    assert "Old Craft" in current["protected_materials"]


def test_all_quests_done_is_valid_empty_protection_not_unknown(recipes):
    current = cp.reconcile(plan(), snapshot(20, ("a", "b", "c")))
    assert current["protected_materials"] == []
    assert report.quest_mats_status_note(set(), "quest_mats.json", protection=current) is None
    assert not recipes


@pytest.mark.parametrize("change", [
    {"authenticated": False}, {"character_id": "999"},
    {"quests": {"recent": [], "total_completed": 10}},
    {"quests": {"recent": [], "total_completed": None}},
    {"quests": {"recent": [], "total_completed": 0, "note": "failed"}},
    {"quests": {"recent": [{"qid": "a"}, {"qid": "a"}], "total_completed": 2}},
    {"jobs": {}}, {"fetched_at_utc": "2020-01-01T00:00:00Z"},
])
def test_missing_incomplete_or_older_state_cannot_release_materials(recipes, change):
    previous = cp.reconcile(plan(), snapshot())
    before = copy.deepcopy(previous)
    with pytest.raises(ValueError):
        cp.reconcile(plan(), {**snapshot(), **change}, previous)
    assert previous == before


def test_completed_quest_or_level_regression_preserves_previous(recipes):
    previous = cp.reconcile(plan(), snapshot(10, ("a",)))
    with pytest.raises(ValueError, match="vanished"):
        cp.reconcile(plan(), snapshot(10), previous)
    with pytest.raises(ValueError, match="regressed"):
        cp.reconcile(plan(), snapshot(5, ("a",)), previous)


def test_unknown_tiers_and_special_quests_are_stored_as_gaps(recipes):
    source = plan()
    source["coverage"]["Carpenter"] = 5
    source["quests"][0]["kind"] = "special"
    current = cp.reconcile(source, snapshot(10))
    assert len(current["coverage_gaps"]) == 2
    assert "coverage incomplete" in report.quest_mats_status_note(set(), "x", protection=current)


def test_explicit_recipe_refresh_bypasses_persistent_cache(recipes):
    previous = cp.reconcile(plan(), snapshot())
    recipes.clear()
    cp.reconcile(plan(), snapshot(), previous, refresh_recipes=True)
    assert "Old Craft" in recipes


def test_network_failure_does_not_replace_prior_file(recipes, tmp_path, monkeypatch):
    source, state, output = (tmp_path / name for name in ("turnins.json", "status.json", "quest_mats.json"))
    cp.write_json(source, plan())
    cp.write_json(state, snapshot(10))
    cp.write_json(output, cp.reconcile(plan(), snapshot()))
    before = output.read_bytes()
    def fail(*a):
        raise requests.Timeout("offline")
    monkeypatch.setattr(mats, "find_recipe", fail)
    monkeypatch.setattr(sys, "argv", ["scionbook_quest_mats.py", "--turnins", str(source), "--status", str(state), "--out", str(output)])
    assert mats.main() == 1
    assert output.read_bytes() == before


def test_distinct_legacy_placeholder_quests_preserve_crafting_evidence(recipes):
    state = snapshot(10, ("a",))
    state["quests"]["recent"].extend([
        {"qid": "quest", "category": "Seasonal Quests", "name": "Festival One"},
        {"qid": "quest", "category": "Seasonal Quests", "name": "Festival Two"},
    ])
    state["quests"]["total_completed"] = 3
    current = cp.reconcile(plan(), state)
    assert current["quests"][0]["state"] == "completed"
    assert current["quests"][1]["state"] == "unfinished"
    assert "Old Craft" not in current["protected_materials"]
    assert "New Craft" in current["protected_materials"]


@pytest.mark.parametrize("entries", [
    [{"qid": "quest", "category": "Seasonal", "name": "Same"}] * 2,
    [{"qid": "quest", "name": "Missing category"}],
    [{"qid": "quest", "category": "Seasonal", "name": " "}],
])
def test_ambiguous_legacy_placeholder_history_is_rejected(entries):
    state = snapshot()
    state["quests"] = {"recent": entries, "total_completed": len(entries)}
    with pytest.raises(ValueError):
        cp.validated_snapshot(plan(), state, None)


def test_placeholder_is_never_a_researched_crafting_quest_id():
    source = plan()
    source["quests"][0]["qid"] = "quest"
    with pytest.raises(ValueError, match="real quest ID"):
        cp.validate_plan(source)


def test_batch_yields_survive_nested_cache_roundtrip(monkeypatch):
    def find(name, session):
        if name == "Old Craft":
            return {"AmountResult": 1, "AmountIngredient": [4],
                    "Ingredient": [{"row_id": 1, "fields": {"Name": "Batch Material"}}]}
        if name == "Batch Material":
            return {"AmountResult": 3, "AmountIngredient": [2],
                    "Ingredient": [{"row_id": 2, "fields": {"Name": "Raw Material"}}]}
        return None
    monkeypatch.setattr(mats, "find_recipe", find)
    monkeypatch.setattr(mats.time, "sleep", lambda _: None)
    source = plan()
    source["quests"] = source["quests"][:1]
    current = cp.reconcile(source, snapshot())
    tree = current["recipe_cache"]["Old Craft"]
    batch = tree["ingredients"][0]
    assert batch["qty_per_craft"] == 4
    assert batch["amount_result"] == 3
    assert batch["ingredients"][0]["qty_per_craft"] == 2
    # Four required intermediate items need two batches, hence four raw items.
    batches = (batch["qty_per_craft"] + batch["amount_result"] - 1) // batch["amount_result"]
    assert batches * batch["ingredients"][0]["qty_per_craft"] == 4
    previous = json.loads(json.dumps(current))
    monkeypatch.setattr(mats, "find_recipe", lambda *a: pytest.fail("cache not reused"))
    assert cp.reconcile(source, snapshot(), previous)["recipe_cache"] == previous["recipe_cache"]


def test_legacy_nested_and_inactive_cache_repaired(recipes):
    previous = cp.reconcile(plan(), snapshot())
    def downgrade(node):
        node.pop("amount_result", None)
        for child in node["ingredients"]:
            child["qty_per_unit"] = child.pop("qty_per_craft")
            downgrade(child)
    for node in previous["recipe_cache"].values():
        downgrade(node)
    before = copy.deepcopy(previous)
    current = cp.reconcile(plan(), snapshot(20, ("a", "b", "c")), previous)
    assert current["protected_materials"] == []
    assert "Old Craft" in recipes
    assert all(mats.cache_has_batch_yields(n) for n in current["recipe_cache"].values())
    assert current["recipe_checked_at_utc"]["Old Craft"] == current["generated_at_utc"]
    assert previous == before


@pytest.mark.parametrize("amount", [None, 0, -1, True, "3"])
def test_invalid_recipe_yield_fails_without_replacing_output(monkeypatch, tmp_path, amount):
    source, state, output = (tmp_path / n for n in ("plan.json", "status.json", "mats.json"))
    cp.write_json(source, plan())
    cp.write_json(state, snapshot())
    cp.write_json(output, {"recipe_cache": {}})
    before = output.read_bytes()
    monkeypatch.setattr(mats, "find_recipe", lambda *a: {"AmountResult": amount})
    monkeypatch.setattr(mats.time, "sleep", lambda _: None)
    monkeypatch.setattr(sys, "argv", ["scionbook_quest_mats.py", "--turnins", str(source),
                                   "--status", str(state), "--out", str(output)])
    assert mats.main() == 1
    assert output.read_bytes() == before
