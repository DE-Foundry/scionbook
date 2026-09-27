"""Home-World estimates stay distinct from provisional non-home price references."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import scionbook_report as report


def price_entry(price, velocity, hq=False):
    return {
        "recentHistory": [{"pricePerUnit": price, "hq": hq}] * 8,
        "listings": [{"pricePerUnit": price * 2, "hq": hq}],
        "hqSaleVelocity" if hq else "nqSaleVelocity": velocity,
    }


@pytest.mark.parametrize("hq", [False, True])
def test_higher_dc_price_and_velocity_cannot_raise_sale_estimates(hq):
    row = {"item_id": 1, "quantity": 99, "hq": hq}
    world = {1: price_entry(1000, 1, hq)}
    baseline = report.verdict_for(row, world, {}, {1}, 100, "Home", "Region")
    compared = report.verdict_for(
        row, world, {1: price_entry(10000, 100, hq)}, {1}, 100, "Home", "Region")
    for field in ("verdict", "unit_price", "est_value", "est_value_optimistic",
                  "est_value_realistic", "weeks_to_clear", "gil_per_slot_week",
                  "price_source", "price_confidence"):
        assert compared[field] == baseline[field]
    assert compared["verdict"] == "sell"
    assert compared["unit_price"] == 1000
    assert compared["est_value"] == 1000 * 7 * report.DEPTH_HORIZON_WEEKS
    assert compared["price_suspect"]  # DC evidence still flags discrepancies.


@pytest.mark.parametrize("world_entry", [None, {}, {"minPriceNQ": 0}])
@pytest.mark.parametrize("vendor_price", [None, 500])
def test_missing_home_price_uses_labeled_dc_reference_without_proceeds(world_entry, vendor_price):
    row = {"item_id": 1, "quantity": 10, "vendor_price": vendor_price}
    world = {} if world_entry is None else {1: world_entry}
    out = report.verdict_for(
        row, world, {1: price_entry(10000, 100)}, {1}, 100, "Home", "Region")
    assert out["verdict"] == "non_home_world_price"
    assert out["unit_price"] == 10000
    assert out["price_reference_scope"] == "Region"
    assert out["price_source"] == "history_median"
    assert out["price_confidence"] == "low"
    assert "starting listing price on Home" in out["reason"]
    for field in ("est_value", "est_value_optimistic",
                  "est_value_realistic", "weeks_to_clear"):
        assert out[field] is None
    assert out["gil_per_slot_week"] == 0


def test_busy_dc_does_not_make_a_slow_home_market_liquid():
    out = report.verdict_for(
        {"item_id": 1, "quantity": 1}, {1: price_entry(50000, 0.02)},
        {1: price_entry(100000, 100)}, {1}, 100, "Home", "Region")
    assert out["verdict"] == "sell_slow"
    assert out["unit_price"] == 50000
    assert "on Home" in out["reason"]


def test_vendor_comparison_uses_home_price_even_when_dc_price_is_higher():
    out = report.verdict_for(
        {"item_id": 1, "quantity": 10, "vendor_price": 600},
        {1: price_entry(500, 100)}, {1: price_entry(10000, 100)},
        {1}, 100, "Home", "Region")
    assert out["verdict"] == "vendor_or_discard"
    assert out["est_value"] == 6000
    assert out["unit_price"] == 500
    assert "on Home" in out["reason"]


@pytest.mark.parametrize("hq", [False, True])
def test_reference_price_preserves_requested_quality(hq):
    dc = price_entry(10000, 100, hq)
    dc["recentHistory"] += [{"pricePerUnit": 100, "hq": not hq}] * 8
    out = report.verdict_for(
        {"item_id": 1, "quantity": 1, "hq": hq}, {}, {1: dc}, {1},
        100, "Home", "Region")
    assert out["verdict"] == "non_home_world_price"
    assert out["unit_price"] == 10000


def test_missing_prices_in_both_scopes_remain_unknown():
    out = report.verdict_for(
        {"item_id": 1, "quantity": 10}, {}, {}, {1}, 100, "Home", "Region")
    assert out["verdict"] == "keep_unknown"
    assert out["unit_price"] is None
    assert "no usable non-home-World reference" in out["reason"]


@pytest.mark.parametrize("protection", ["quest", "leveling"])
def test_reference_price_does_not_bypass_material_or_leveling_protection(protection):
    row = {"item_id": 1, "quantity": 10,
           "name": "Craft Material" if protection == "quest" else "Engineering Manual"}
    row.update(report.verdict_for(
        row, {}, {1: price_entry(10000, 100)}, {1}, 100, "Home", "Region"))
    if protection == "quest":
        assert report.apply_quest_material_protection([row], {"craft material"}) == 1
        assert row["verdict"] == "protected_quest_material"
    else:
        assert report.apply_never_discard_protection([row]) == 1
        assert row["verdict"] == "protected_leveling_item"


@pytest.mark.parametrize("marketable", [None, {1}])
@pytest.mark.parametrize("entry", [None, {}, {"minPriceNQ": 0}])
def test_missing_prices_preserve_known_vendor_value(marketable, entry):
    prices = {} if entry is None else {1: entry}
    out = report.verdict_for(
        {"item_id": 1, "quantity": 10, "vendor_price": 50},
        prices, prices, marketable, 100, "Home", "Region")
    assert out["verdict"] == "vendor_or_discard"
    assert out["est_value"] == out["est_value_realistic"] == 500
    assert out["est_value_optimistic"] == 500
    assert out["unit_price"] is None
    assert out["weeks_to_clear"] is None
    assert "Check Home's market board" in out["reason"]


@pytest.mark.parametrize("vendor_price", [500, 600])
def test_vendor_value_beats_or_ties_dc_reference(vendor_price):
    out = report.verdict_for(
        {"item_id": 1, "quantity": 10, "vendor_price": vendor_price},
        {}, {1: price_entry(500, 100)}, {1}, 100, "Home", "Region")
    assert out["verdict"] == "vendor_or_discard"
    assert out["est_value"] == out["est_value_realistic"] == vendor_price * 10
    assert out["unit_price"] == 500
    assert out["price_reference_scope"] == "Region"
    assert out["weeks_to_clear"] is None
    assert out["gil_per_slot_week"] == 0
    assert "vendor proceeds only" in out["reason"]


@pytest.mark.parametrize("hq", [False, True])
def test_dc_reference_gets_npc_warning_without_hard_cap(hq):
    out = report.verdict_for(
        {"item_id": 1, "quantity": 10, "hq": hq}, {},
        {1: price_entry(5000, 100, hq)}, {1}, 100, "Home", "Region",
        vendor_buy={1: 1000})
    assert out["verdict"] == "non_home_world_price"
    assert out["unit_price"] == 5000
    assert out["est_value"] is None
    assert any("NPC sells this for 1,000" in n for n in out["price_notes"])
    assert "quest/level-gated" in out["reason"]


def test_dc_vendor_comparison_uses_adjusted_reference_price():
    entry = price_entry(1000, 100)
    entry["listings"] = [{"pricePerUnit": 500, "hq": False}]
    out = report.verdict_for(
        {"item_id": 1, "quantity": 10, "vendor_price": 500},
        {}, {1: entry}, {1}, 100, "Home", "Region")
    assert out["verdict"] == "vendor_or_discard"
    assert out["unit_price"] == round(500 * report.UNDERCUT_FACTOR)
    assert out["est_value"] == 5000
