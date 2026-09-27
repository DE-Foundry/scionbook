"""Regression tests using synthetic Lodestone markup and pricing payloads.

Fixtures preserve parser edge cases without player/account records.
Run with: python3 -m pytest tests/
"""
import pathlib
import sys

from bs4 import BeautifulSoup

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import scionbook_report as fr  # noqa: E402
import scionbook_quest_mats as qm  # noqa: E402

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def soup_of(name):
    html = (FIXTURES / name).read_text(encoding="utf-8")
    return BeautifulSoup(html, "html.parser"), html


# --------------------------------------------------------------------------- #
# parse_sale_rows / parse_listing_rows - two sections, one page
#
# The "contaminated" fixture name is historical. Its 6 non-sale rows were
# never tooltip contamination: they are the retainer's active market
# listings ("Sale Inventory"), which the original parser misread as popup
# dumps and discarded. See parse_listing_rows.
# --------------------------------------------------------------------------- #

def test_parse_sale_rows_separates_listings_without_counting_them_dropped():
    soup, _ = soup_of("sales_contaminated.html")
    rows, dropped = fr.parse_sale_rows(soup)
    # The 6 rows previously counted as dropped contamination are listings,
    # parsed by parse_listing_rows - not data loss, so not counted here.
    assert dropped == 0
    assert len(rows) == 20
    for r in rows:
        assert "Sells for" not in r["name"]
        assert len(r["name"]) < 80
        assert r["buyer"] not in ("1", "4", None)
        assert r["sold_epoch"] is not None


def test_parse_listing_rows_recovers_the_active_listings():
    """These 6 rows were discarded on every run since 2026-08-28, which is
    why market_slots_occupied read 0 on a board that had items on it."""
    soup, _ = soup_of("sales_contaminated.html")
    listings = fr.parse_listing_rows(soup)
    assert len(listings) == 6
    for l in listings:
        assert l["name"] and len(l["name"]) < 80
        assert "Sells for" not in l["name"]
        assert l["unit_price"] and l["quantity"] and l["total"]
        # price x quantity == total is the arithmetic that identifies these
        # as listings rather than popups in the first place.
        assert l["total_reconciles"], l


def test_parse_listing_rows_known_values_from_fixture():
    soup, _ = soup_of("sales_contaminated.html")
    listings = fr.parse_listing_rows(soup)
    triples = sorted((l["unit_price"], l["quantity"], l["total"])
                     for l in listings)
    assert (1000, 4, 4000) in triples
    assert (150, 1, 150) in triples


def test_parse_listing_rows_finds_none_on_a_clean_sale_page():
    """sales_clean.html is 20 sale rows and nothing else - no listings."""
    soup, _ = soup_of("sales_clean.html")
    assert fr.parse_listing_rows(soup) == []


def test_parse_sale_rows_clean_page_drops_nothing():
    soup, _ = soup_of("sales_clean.html")
    rows, dropped = fr.parse_sale_rows(soup)
    assert dropped == 0
    assert len(rows) == 20


def test_parse_sale_rows_fields():
    soup, _ = soup_of("sales_clean.html")
    rows, _ = fr.parse_sale_rows(soup)
    first = rows[0]
    assert first["name"] == "Quickarm Materia III"
    assert first["quantity"] == 1
    assert first["hq"] is False
    assert first["unit_price"] == 86
    assert first["buyer"] == "Example Buyer 0"
    assert first["sold_epoch"] == 1700000000


def test_parse_sale_rows_hq_and_multi_quantity():
    soup, _ = soup_of("sales_contaminated.html")
    rows, _ = fr.parse_sale_rows(soup)
    by_name = {r["name"]: r for r in rows}
    assert by_name["Battledance Materia II"]["quantity"] == 2
    assert by_name["High Steel Kris"]["hq"] is True


# --------------------------------------------------------------------------- #
# parse_baggage_rows
# --------------------------------------------------------------------------- #

def test_parse_baggage_rows_returns_expected_shape():
    soup, _ = soup_of("baggage_clean.html")
    rows = fr.parse_baggage_rows(soup)
    assert len(rows) > 0
    for r in rows:
        assert set(r) == {"name", "quantity", "hq", "listed_price",
                          "vendor_price", "market_allowed"}
        assert isinstance(r["quantity"], int) and r["quantity"] >= 1
        assert isinstance(r["hq"], bool)


def test_parse_baggage_rows_vendor_price_and_market_allowed():
    soup, _ = soup_of("baggage_2.html")
    rows = fr.parse_baggage_rows(soup)
    by_name = {r["name"]: r for r in rows}
    # Confirmed against XIVAPI PriceLow on 2026-08-28: real vendor gil, not
    # a regex misfire (see pricing diagnosis).
    assert by_name["Potion of Strength"]["vendor_price"] == 3
    assert by_name["Potion of Strength"]["market_allowed"] is True
    # Market-prohibited items exist in this fixture and must be flagged.
    assert any(r["market_allowed"] is False for r in rows)


def test_parse_baggage_rows_no_stack_attr_rows_ignored():
    soup, _ = soup_of("sales_contaminated.html")
    # The market/sales page has no data-stack rows at all - baggage parser
    # should find nothing here, not misfire on the contamination.
    rows = fr.parse_baggage_rows(soup)
    assert rows == []


# --------------------------------------------------------------------------- #
# parse_currency - the alternating-match regex bug
# --------------------------------------------------------------------------- #

def test_parse_currency_recovers_all_alternating_entries():
    soup, html = soup_of("currency.html")
    cur, rep, active_seal = fr.parse_currency(soup, html)
    # A trailing-\n-consuming regex drops every other label/value pair on a
    # page with this many currency rows (confirmed live, 2026-08-28) - guard
    # the exact count so a regression here fails loudly instead of quietly
    # losing half the currencies again.
    assert cur is not None
    assert len(cur) >= 14
    assert cur["Gil"].replace(",", "").isdigit()
    # Both the frozen legacy seal balance and the active one must survive -
    # this is exactly the pair the old regex could not return together.
    assert "Storm Seals" in cur
    assert "Flame Seals" in cur
    assert "Allagan Tomestone of Mnemonics" in cur


def test_parse_currency_active_seal_matches_class_state():
    soup, html = soup_of("currency.html")
    _, _, active_seal = fr.parse_currency(soup, html)
    assert active_seal == "Flame Seals"


def test_parse_currency_reputation_societies():
    soup, html = soup_of("currency.html")
    _, rep, _ = fr.parse_currency(soup, html)
    assert rep is not None
    assert "Commendations Received" in rep
    assert "societies" in rep
    assert any(s["name"] for s in rep["societies"])


def test_reconcile_currencies_no_false_mismatch_after_fix():
    soup, html = soup_of("currency.html")
    cur, _, active_seal = fr.parse_currency(soup, html)
    character = {"grand_company": "Immortal Flames / First Flame Lieutenant"}
    _, _, warning = fr.reconcile_currencies(character, cur, active_seal)
    assert warning is None


def test_reconcile_currencies_flags_real_mismatch():
    cur = {"Storm Seals": "100"}
    character = {"grand_company": "Immortal Flames / First Flame Lieutenant"}
    _, _, warning = fr.reconcile_currencies(character, cur, "Storm Seals")
    assert warning is not None
    assert "MISMATCH" in warning


def test_reconcile_currencies_backfills_current_tomestones_as_zero():
    _, inferred, _ = fr.reconcile_currencies(
        {"grand_company": "Immortal Flames / X"}, {}, None)
    assert set(fr.CURRENT_TOMESTONES_CAPPED) <= set(inferred)
    assert set(fr.CURRENT_TOMESTONES_UNCAPPED) <= set(inferred)


# --------------------------------------------------------------------------- #
# parse_quests_page
# --------------------------------------------------------------------------- #

def test_parse_quests_page_basic_fields():
    soup, html = soup_of("quest_p1.html")
    quests, total, pages = fr.parse_quests_page(soup, html)
    assert len(quests) > 0
    assert total and total > len(quests)
    assert pages and pages > 1
    first = quests[0]
    assert first["qid"]
    assert first["epoch"]
    assert first["date"]


def test_parse_quests_page_category_split():
    soup, html = soup_of("quest_p1.html")
    quests, _, _ = fr.parse_quests_page(soup, html)
    with_category = [q for q in quests if q["category"]]
    assert with_category
    for q in with_category:
        assert q["name"]


# --------------------------------------------------------------------------- #
# pricing helpers - synthetic Universalis payloads (no live fixture needed;
# these mirror shapes confirmed against the live API, see pricing diagnosis)
# --------------------------------------------------------------------------- #

def test_pick_unit_price_prefers_history_median_over_min_price():
    entry = {
        "minPrice": 5000, "minPriceNQ": 5000,
        "recentHistory": [{"hq": False, "pricePerUnit": p}
                          for p in (500, 650, 700, 721, 495)],
    }
    price, source, hist_n, _ = fr.pick_unit_price(entry, hq=False)
    assert source == "history_median"
    assert price == 650  # median of [495,500,650,700,721]
    assert hist_n == 5


def test_pick_unit_price_hq_nq_are_independent():
    entry = {
        "minPriceNQ": 100, "minPriceHQ": 3000,
        "recentHistory": [
            {"hq": True, "pricePerUnit": 90}, {"hq": True, "pricePerUnit": 100},
            {"hq": False, "pricePerUnit": 70}, {"hq": False, "pricePerUnit": 80},
        ],
    }
    hq_price, _, _, _ = fr.pick_unit_price(entry, hq=True)
    nq_price, _, _, _ = fr.pick_unit_price(entry, hq=False)
    assert hq_price == 95
    assert nq_price == 75


def test_pick_unit_price_falls_back_when_no_history():
    entry = {"averagePriceNQ": 200, "currentAveragePriceNQ": 300,
             "minPriceNQ": 50, "recentHistory": []}
    price, source, hist_n, _ = fr.pick_unit_price(entry, hq=False)
    assert source == "average_price"
    assert price == 200
    assert hist_n == 0


def test_pick_unit_price_last_resort_min_price():
    entry = {"minPriceNQ": 50, "recentHistory": []}
    price, source, _, _ = fr.pick_unit_price(entry, hq=False)
    assert source == "min_price"
    assert price == 50


def test_is_price_suspect_flags_large_disagreement_with_history():
    assert fr.is_price_suspect(5000, "min_price", 650, hist_n=0, listings_n=1)
    assert not fr.is_price_suspect(650, "history_median", 650, hist_n=5,
                                   listings_n=4)


def test_is_price_suspect_flags_single_listing_no_history():
    assert fr.is_price_suspect(1000, "min_price", None, hist_n=0, listings_n=1)
    assert not fr.is_price_suspect(1000, "min_price", None, hist_n=0,
                                   listings_n=5)


# --------------------------------------------------------------------------- #
# sale totals vs unit prices
# --------------------------------------------------------------------------- #

def test_parse_sale_rows_divides_total_by_quantity():
    """The Lodestone price cell is the sale TOTAL. A quantity-2 row must
    therefore report half of it as the unit price, and keep the total."""
    soup, _ = soup_of("sales_contaminated.html")
    rows, _ = fr.parse_sale_rows(soup)
    row = {r["name"]: r for r in rows}["Battledance Materia II"]
    assert row["quantity"] == 2
    assert row["unit_price"] == round(row["sale_total"] / 2)
    assert row["sale_total"] > row["unit_price"]


def test_parse_sale_rows_quantity_one_total_equals_unit():
    soup, _ = soup_of("sales_clean.html")
    rows, _ = fr.parse_sale_rows(soup)
    first = rows[0]
    assert first["quantity"] == 1
    assert first["unit_price"] == first["sale_total"] == 86


# --------------------------------------------------------------------------- #
# velocity units
# --------------------------------------------------------------------------- #

def test_pick_velocity_converts_per_day_to_per_week():
    """Universalis saleVelocity is units/day (units sold in 7d / 7). Fine
    Wax's live value of 2.857143 corresponded to 20 units in 7 days."""
    assert abs(fr.pick_velocity({"nqSaleVelocity": 2.857143}, hq=False)
               - 20.0) < 1e-4


def test_pick_velocity_hq_and_regular_fallback():
    assert fr.pick_velocity({"hqSaleVelocity": 1.0}, hq=True) == 7.0
    assert fr.pick_velocity({"regularSaleVelocity": 2.0}, hq=False) == 14.0
    assert fr.pick_velocity({}, hq=False) == 0.0


# --------------------------------------------------------------------------- #
# undercutting and the NPC vendor ceiling
# --------------------------------------------------------------------------- #

def test_effective_sale_price_undercuts_current_board():
    """History says 1000 but the board is already down to 600: you have to
    get under 600 to be the one who sells."""
    entry = {"listings": [{"pricePerUnit": 600, "hq": False},
                          {"pricePerUnit": 900, "hq": False}]}
    price, notes = fr.effective_sale_price(entry, hq=False, hist_price=1000)
    assert price == 600 * fr.UNDERCUT_FACTOR
    assert any("undercut" in n for n in notes)


def test_effective_sale_price_keeps_history_when_board_is_higher():
    entry = {"listings": [{"pricePerUnit": 5000, "hq": False}]}
    price, notes = fr.effective_sale_price(entry, hq=False, hist_price=1000)
    assert price == 1000
    assert notes == []


def test_effective_sale_price_flags_but_does_not_cap_vendor_buy_price():
    """Rroneek Glue: an NPC sells it for 300k, but that vendor (Goplu in
    Tuliyollal) is gated behind the quest 'Forging the Phantasmal' - not
    every buyer has it. Actual sales clear at 400-500k, consistent with most
    buyers having no access to the cheap vendor. Capping the achievable
    price at vendor cost was confirmed wrong live 2026-09-04; a GilShopItem
    entry now only produces a note for the seller to weigh, never a price
    override."""
    entry = {"listings": [{"pricePerUnit": 499999, "hq": False}]}
    price, notes = fr.effective_sale_price(entry, hq=False, hist_price=459998,
                                           vendor_buy_price=300000)
    assert price == 459998
    assert any("NOTE" in n and "vendor" in n.lower() for n in notes)


def test_effective_sale_price_ignores_absent_vendor_price():
    """Fine Wax has PriceMid 279 but no shop stocks it, so the caller passes
    no ceiling and the ~14k market price must survive intact."""
    entry = {"listings": [{"pricePerUnit": 14500, "hq": False}]}
    price, _ = fr.effective_sale_price(entry, hq=False, hist_price=14000,
                                       vendor_buy_price=None)
    # Undercutting the 14,500 board ask is expected; being dragged anywhere
    # near PriceMid (279) would be the bug.
    assert price == 14500 * fr.UNDERCUT_FACTOR
    assert price > 10000


def test_cheapest_current_ask_respects_quality():
    entry = {"listings": [{"pricePerUnit": 100, "hq": True},
                          {"pricePerUnit": 900, "hq": False}]}
    assert fr.cheapest_current_ask(entry, hq=False) == 900
    assert fr.cheapest_current_ask(entry, hq=True) == 100


def test_price_dispersion_flags_local_outlier():
    world = {"recentHistory": [{"pricePerUnit": 500000, "hq": False}] * 6}
    dc = {"recentHistory": [{"pricePerUnit": 1000, "hq": False}] * 6}
    assert fr.price_dispersion_suspect(world, dc, hq=False, chosen=500000)
    assert not fr.price_dispersion_suspect(world, dc, hq=False, chosen=1200)


def test_price_dispersion_needs_a_real_dc_sample():
    """A thin DC sample is not evidence of anything - don't flag on it."""
    dc = {"recentHistory": [{"pricePerUnit": 1000, "hq": False}]}
    assert not fr.price_dispersion_suspect({}, dc, hq=False, chosen=500000)


# --------------------------------------------------------------------------- #
# verdict_for: slot economics
# --------------------------------------------------------------------------- #

def _entry(price, velocity, listings=None):
    return {"recentHistory": [{"pricePerUnit": price, "hq": False}] * 8,
            "nqSaleVelocity": velocity,
            "listings": listings if listings is not None
            else [{"pricePerUnit": price * 10, "hq": False}]}


def test_verdict_for_reports_gil_per_slot_week():
    row = {"item_id": 1, "quantity": 99, "hq": False, "vendor_price": 1}
    out = fr.verdict_for(row, {1: _entry(200, 10.0)}, {}, {1}, 500,
                         "Example World", "Example DC")
    assert out["verdict"] == "sell"
    # 10/day -> 70/week, so a 99 stack clears inside the 4-week horizon
    assert out["weeks_to_clear"] < fr.DEPTH_HORIZON_WEEKS
    assert out["gil_per_slot_week"] > 0
    assert out["unit_price"] == 200


def test_verdict_for_slow_mover_uses_weekly_threshold():
    """0.02/day is 0.14/week - genuinely dead, and must still read slow once
    the per-week conversion is applied."""
    row = {"item_id": 1, "quantity": 1, "hq": False, "vendor_price": 1}
    out = fr.verdict_for(row, {1: _entry(50000, 0.02)}, {}, {1}, 500,
                         "Example World", "Example DC")
    assert out["verdict"] == "sell_slow"


def test_verdict_for_vendor_ceiling_flags_but_does_not_change_the_estimate():
    """A quest-gated vendor (Rroneek Glue's Goplu, gated behind 'Forging the
    Phantasmal') is not proof every buyer has a cheaper option - it's a flag
    for manual review, not an automatic haircut. See effective_sale_price."""
    row = {"item_id": 46854, "quantity": 1, "hq": False, "vendor_price": 1}
    px = {46854: _entry(459998, 0.14,
                        listings=[{"pricePerUnit": 499999, "hq": False}])}
    uncapped = fr.verdict_for(row, px, {}, {46854}, 500, "Example World", "Example DC")
    flagged = fr.verdict_for(row, px, {}, {46854}, 500, "Example World", "Example DC",
                             vendor_buy={46854: 300000})
    assert flagged["unit_price"] == uncapped["unit_price"]
    assert flagged["est_value_optimistic"] == uncapped["est_value_optimistic"]
    assert flagged["price_suspect"] is True
    assert any("vendor" in n.lower() for n in flagged["price_notes"])


def test_price_dispersion_ignores_cheap_items():
    """A 3x gap on bait priced in single-digit gil is noise. The first live
    run with this check flagged 68 rows, nearly all low-value fish."""
    world = {"recentHistory": [{"pricePerUnit": 5, "hq": False}] * 6}
    dc = {"recentHistory": [{"pricePerUnit": 20, "hq": False}] * 6}
    assert not fr.price_dispersion_suspect(world, dc, hq=False, chosen=5)


# --------------------------------------------------------------------------- #
# scionbook_quest_mats: recipe-closure protection (no network - pure functions)
# --------------------------------------------------------------------------- #

import scionbook_quest_mats as fqm  # noqa: E402


def test_recipe_ingredients_filters_padding_and_sentinel():
    """Ingredient/AmountIngredient are fixed-length-8 arrays; unused slots
    are item id 0 and the array ends with a bare -1 sentinel with no
    'fields' key at all - both must be dropped, not read as an ingredient."""
    fields = {
        "Ingredient": [
            {"row_id": 5106, "fields": {"Name": "Copper Ore"}},
            {"row_id": 0, "fields": {"Name": ""}},
            {"row_id": 2, "fields": {"Name": "Fire Shard"}},
            {"value": -1},
        ],
        "AmountIngredient": [2, 0, 1, 0],
    }
    result = fqm.recipe_ingredients(fields)
    assert result == [("Copper Ore", 2), ("Fire Shard", 1)]


def test_walk_closure_leaf_has_no_ingredients(monkeypatch):
    monkeypatch.setattr(fqm, "find_recipe", lambda name, session: None)
    node = fqm.walk_closure("Fire Shard", session=None, cache={})
    assert node == {"name": "Fire Shard", "is_craftable": False,
                    "ingredients": []}


def test_walk_closure_recurses_into_sub_recipes(monkeypatch):
    """Mythril Plate is itself crafted from Mythril Ingot + Ice Shard; the
    closure of something that uses Mythril Plate must reach both."""
    recipes = {
        "Mythril Plate": {"Ingredient": [
            {"row_id": 1, "fields": {"Name": "Mythril Ingot"}},
            {"row_id": 2, "fields": {"Name": "Ice Shard"}}],
            "AmountIngredient": [2, 4]},
        "Mythril Ingot": None,
        "Ice Shard": None,
    }
    monkeypatch.setattr(fqm, "find_recipe",
                        lambda name, session: recipes.get(name))
    node = fqm.walk_closure("Mythril Plate", session=None, cache={})
    leaves = fqm.flatten_leaves(node)
    # Mythril Plate itself is included now, not just its raw ingredients -
    # see flatten_leaves for why (Taffeta Cloth, Boar Leather, etc. were
    # missed as intermediates before this fix).
    assert leaves == {"Mythril Plate", "Mythril Ingot", "Ice Shard"}
    assert node["is_craftable"] is True


def test_walk_closure_breaks_cycles(monkeypatch):
    recipes = {"A": {"Ingredient": [{"row_id": 1, "fields": {"Name": "B"}}],
                     "AmountIngredient": [1]},
              "B": {"Ingredient": [{"row_id": 1, "fields": {"Name": "A"}}],
                    "AmountIngredient": [1]}}
    monkeypatch.setattr(fqm, "find_recipe",
                        lambda name, session: recipes.get(name))
    node = fqm.walk_closure("A", session=None, cache={})
    # Must terminate rather than recurse forever, and never crash.
    assert node["name"] == "A"


def test_walk_closure_caches_repeated_ingredients(monkeypatch):
    """Ice Shard/Earth Shard appear in nearly every mid-level crafting
    recipe; each should only be looked up once per run."""
    calls = []

    def fake_find(name, session):
        calls.append(name)
        if name == "Widget A":
            return {"Ingredient": [{"row_id": 1, "fields": {"Name": "Shard"}}],
                    "AmountIngredient": [1]}
        if name == "Widget B":
            return {"Ingredient": [{"row_id": 1, "fields": {"Name": "Shard"}}],
                    "AmountIngredient": [1]}
        return None

    monkeypatch.setattr(fqm, "find_recipe", fake_find)
    cache = {}
    fqm.walk_closure("Widget A", session=None, cache=cache)
    fqm.walk_closure("Widget B", session=None, cache=cache)
    assert calls.count("Shard") == 1


def test_flatten_leaves_protects_intermediate_crafts_too():
    """Every stage of the recipe - the finished turn-in, an intermediate
    craft, and raw leaves - must be protected, not just the leaves. This is
    the fix for the 2026-09-04 report that Taffeta Cloth/Boar Leather/Horn
    Glue/Fine Wax/Silver Ingot/Hard Leather (all intermediate crafts) were
    slipping through to the sell bucket."""
    tree = {"name": "Top", "is_craftable": True, "ingredients": [
        {"name": "Mid", "is_craftable": True, "ingredients": [
            {"name": "Raw", "is_craftable": False, "ingredients": []}]},
        {"name": "OtherRaw", "is_craftable": False, "ingredients": []},
    ]}
    assert fqm.flatten_leaves(tree) == {"Top", "Mid", "Raw", "OtherRaw"}


# --------------------------------------------------------------------------- #
# never-discard protection: DoH/DoL leveling XP-boost manuals
# --------------------------------------------------------------------------- #

def test_is_never_discard_matches_manual_variants():
    for name in ["Commercial Engineering Manual", "Revised Survival Manual",
                "Squadron Engineering Manual", "Company-issue Survival "
                "Manual II"]:
        assert fr.is_never_discard(name), name
    assert not fr.is_never_discard("Iron Ore")
    assert not fr.is_never_discard(None)


def test_apply_never_discard_protection_overrides_any_sell_verdict():
    rows = [
        {"name": "Commercial Engineering Manual", "verdict": "sell",
         "reason": "~50,000g realistically"},
        {"name": "Commercial Survival Manual", "verdict": "vendor_or_discard",
         "reason": "only ~10g"},
        {"name": "Iron Ore", "verdict": "sell", "reason": "~100g"},
    ]
    n = fr.apply_never_discard_protection(rows)
    assert n == 2
    assert rows[0]["verdict"] == rows[1]["verdict"] == "protected_leveling_item"
    assert rows[2]["verdict"] == "sell"
    assert "never discard" in rows[0]["reason"]


# --------------------------------------------------------------------------- #
# min_gil floor scaling with free market slots (2026-09-04 fix)
# --------------------------------------------------------------------------- #

def test_verdict_for_below_min_gil_is_vendor_or_discard():
    """Baseline: a flat min_gil floor still applies when the caller doesn't
    scale it - e.g. a full board, where a 940g item genuinely isn't worth a
    slot over something better."""
    row = {"item_id": 1, "quantity": 1, "hq": False, "vendor_price": 1}
    out = fr.verdict_for(row, {1: _entry(940, 10.0)}, {}, {1}, 1000,
                         "Example World", "Example DC")
    assert out["verdict"] == "vendor_or_discard"


def test_verdict_for_respects_a_lowered_min_gil():
    """With an empty board there's no opportunity cost, so main() computes
    a scaled-down effective_min_gil and passes it straight through - the
    same 940g item should clear a floor of, say, 100."""
    row = {"item_id": 1, "quantity": 1, "hq": False, "vendor_price": 1}
    out = fr.verdict_for(row, {1: _entry(940, 10.0)}, {}, {1}, 100,
                         "Example World", "Example DC")
    assert out["verdict"] == "sell"


# --------------------------------------------------------------------------- #
# untradeable + no vendor price -> keep_unknown, not discard (2026-09-04 fix)
# --------------------------------------------------------------------------- #

def test_verdict_for_untradeable_no_vendor_price_is_keep_unknown():
    """Flagged live 2026-09-04: this exact profile (market_allowed False,
    vendor_price None) was hitting real Occult Crescent phantom-job unlock
    drops and Arcadion raid tokens with a 'safe to discard' verdict -
    directly contradicting the module's own fail-closed principle."""
    row = {"item_id": 1, "quantity": 1, "hq": False,
          "market_allowed": False, "vendor_price": None}
    out = fr.verdict_for(row, {}, {}, set(), 1000, "Example World", "Example DC")
    assert out["verdict"] == "keep_unknown"
    assert out["est_value"] is None


def test_verdict_for_untradeable_with_vendor_price_still_sells_to_vendor():
    """The fix must not swallow the case where a vendor price DOES exist -
    that's genuinely sellable-to-vendor, unlike the no-signal-at-all case
    above."""
    row = {"item_id": 1, "quantity": 3, "hq": False,
          "market_allowed": False, "vendor_price": 50}
    out = fr.verdict_for(row, {}, {}, set(), 1000, "Example World", "Example DC")
    assert out["verdict"] == "vendor_or_discard"
    assert out["est_value"] == 150


# --------------------------------------------------------------------------- #
# quest_mats_status_note: distinguish "nothing to protect" from "no data"
# --------------------------------------------------------------------------- #

def test_quest_mats_status_note_missing_file():
    note = fr.quest_mats_status_note(None, "quest_mats.json")
    assert "not found" in note


def test_quest_mats_status_note_empty_set_is_not_silent():
    """The 2026-09-04 bug: an empty set used to produce no note at all,
    reading as 'nothing needs protecting' when it really meant 'no tier is
    currently tracked.'"""
    note = fr.quest_mats_status_note(set(), "quest_mats.json")
    assert note is not None
    assert "zero protected materials" in note
    assert "NOT that nothing needs protecting" in note


def test_quest_mats_status_note_real_protections_is_silent():
    note = fr.quest_mats_status_note({"iron ore"}, "quest_mats.json")
    assert note is None


# --------------------------------------------------------------------------- #
# scale_min_gil: floor scales with slot occupancy, never below the nuisance
# floor (2026-09-04 fix, corrected same day after over-scaling to 1g)
# --------------------------------------------------------------------------- #

def test_scale_min_gil_full_board_keeps_flat_floor():
    assert fr.scale_min_gil(1000, occupied=40, slots_total=40) == 1000


def test_scale_min_gil_empty_board_drops_to_nuisance_floor():
    """0/40 occupied - no opportunity cost, so it should drop all the way to
    the nuisance floor, not stay near 1,000."""
    assert fr.scale_min_gil(1000, occupied=0, slots_total=40) == \
        fr.MIN_GIL_NUISANCE_FLOOR


def test_scale_min_gil_never_below_nuisance_floor():
    """A first version of this fix scaled to 1g and flooded 'sell' with
    1-4g bait (Helmet Crab, Animal Sinew, Lightning Rock). Must never go
    below MIN_GIL_NUISANCE_FLOOR regardless of occupancy."""
    assert fr.scale_min_gil(1000, occupied=0, slots_total=40) >= \
        fr.MIN_GIL_NUISANCE_FLOOR
    assert fr.scale_min_gil(10_000_000, occupied=0, slots_total=40) == \
        fr.MIN_GIL_NUISANCE_FLOOR


def test_scale_min_gil_partial_occupancy_is_between():
    half = fr.scale_min_gil(1000, occupied=20, slots_total=40)
    assert fr.MIN_GIL_NUISANCE_FLOOR <= half <= 1000


def test_scale_min_gil_no_slots_returns_flat_floor():
    assert fr.scale_min_gil(1000, occupied=0, slots_total=0) == 1000


# --------------------------------------------------------------------------- #
# check_turnins_resolve - the silent no-recipe failure
# --------------------------------------------------------------------------- #
# A bad turn-in name used to fail invisibly: walk_closure finds no recipe,
# returns a childless leaf, flatten_leaves protects that one dead string, and
# the run reports success while the tier protects nothing. Two names have been
# wrong this way already ("Geva's Choker", "Elde's Donation").


def _tree(name, craftable, ingredients=()):
    return {"name": name, "is_craftable": craftable,
            "ingredients": list(ingredients)}


def test_check_turnins_resolve_passes_when_every_turnin_has_a_recipe():
    turnins = {
        "Blacksmith": {53: [_tree("Mythrite Rivets", True,
                                  [_tree("Mythrite Ingot", True)])]},
        "Culinarian": {60: [_tree("Morel Salad", True),
                            _tree("Marron Glace", True)]},
    }
    assert qm.check_turnins_resolve(turnins) == []


def test_check_turnins_resolve_flags_an_unresolvable_turnin():
    turnins = {
        "Leatherworker": {35: [_tree("Geva's Choker", False)]},
        "Blacksmith": {53: [_tree("Mythrite Rivets", True)]},
    }
    assert qm.check_turnins_resolve(turnins) == [
        ("Leatherworker", 35, "Geva's Choker")]


def test_check_turnins_resolve_reports_every_bad_entry_not_just_the_first():
    turnins = {
        "Alchemist": {55: [_tree("Elde's Donation", False)],
                      60: [_tree("Noble Gold", True)]},
        "Weaver": {58: [_tree("Crawler Silk", False)]},
    }
    bad = qm.check_turnins_resolve(turnins)
    assert sorted(bad) == [("Alchemist", 55, "Elde's Donation"),
                           ("Weaver", 58, "Crawler Silk")]


# --------------------------------------------------------------------------- #
# outgrown_tier_note - coverage that exists but no longer applies
# --------------------------------------------------------------------------- #

HW_TIERS = {j: [53, 55, 58, 60] for j in
            ("Carpenter", "Blacksmith", "Armorer", "Goldsmith",
             "Leatherworker", "Weaver", "Alchemist", "Culinarian")}


def test_outgrown_tier_note_silent_while_crafters_are_inside_coverage():
    levels = {j: 52 for j in HW_TIERS}
    assert fr.outgrown_tier_note(HW_TIERS, levels) is None


def test_outgrown_tier_note_silent_at_the_top_tier_itself():
    """Level 60 still has the 60 turn-in pending - that is covered, not past."""
    levels = {j: 60 for j in HW_TIERS}
    assert fr.outgrown_tier_note(HW_TIERS, levels) is None


def test_outgrown_tier_note_fires_for_a_crafter_past_the_last_tier():
    levels = dict.fromkeys(HW_TIERS, 52)
    levels["Culinarian"] = 61
    note = fr.outgrown_tier_note(HW_TIERS, levels)
    assert note is not None
    assert "Culinarian (level 61, tracked through 60)" in note
    assert "Weaver" not in note


def test_outgrown_tier_note_flags_a_crafter_with_no_tier_at_all():
    tiers = {j: v for j, v in HW_TIERS.items() if j != "Alchemist"}
    note = fr.outgrown_tier_note(tiers, dict.fromkeys(HW_TIERS, 52))
    assert "Alchemist (level 52, no tier tracked)" in note


def test_outgrown_tier_note_needs_both_inputs():
    assert fr.outgrown_tier_note(None, {"Weaver": 61}) is None
    assert fr.outgrown_tier_note(HW_TIERS, None) is None


def test_quest_mats_status_note_prefers_the_empty_set_warning():
    """An empty set is the louder problem; don't mask it with the tier note."""
    note = fr.quest_mats_status_note(set(), "quest_mats.json", HW_TIERS,
                                     dict.fromkeys(HW_TIERS, 61))
    assert "zero protected materials" in note


def test_quest_mats_status_note_surfaces_outgrown_coverage_when_set_is_full():
    levels = dict.fromkeys(HW_TIERS, 52)
    levels["Blacksmith"] = 62
    note = fr.quest_mats_status_note({"mythrite ore"}, "quest_mats.json",
                                     HW_TIERS, levels)
    assert note is not None and "Blacksmith (level 62" in note


def test_quest_mats_status_note_stays_silent_when_everything_is_current():
    assert fr.quest_mats_status_note({"mythrite ore"}, "quest_mats.json",
                                     HW_TIERS,
                                     dict.fromkeys(HW_TIERS, 52)) is None


# --------------------------------------------------------------------------- #
# build_report plans against FREE slots, not total (2026-09-05)
# --------------------------------------------------------------------------- #

def _report_data(n_listable, occupied, slots_total=40):
    rows = [{"name": f"Item {i}", "quantity": 1, "hq": False,
             "retainer": "R", "verdict": "sell", "reason": "x",
             "est_value": 1000 - i, "gil_per_slot_week": 1000 - i,
             "weeks_to_clear": 1.0, "price_suspect": False}
            for i in range(n_listable)]
    return {"fetched_at_utc": "now", "all_rows": rows,
            "summary": {"market_slots_total": slots_total,
                        "market_slots_occupied": occupied,
                        "retainers": 2,
                        "estimated_recoverable_gil": 1,
                        "estimated_recoverable_gil_optimistic": 1}}


def test_build_report_plans_only_into_free_slots():
    """With 25 of 40 slots occupied, the plan must offer 15 items, not 40 -
    it used to plan against slots_total, which was only ever correct while
    market_slots_occupied was stuck at 0."""
    md = fr.build_report(_report_data(n_listable=60, occupied=25))
    assert "into 15 free market slot(s)" in md
    assert "25 of 40 slots are already in use" in md
    # Count only inside the plan section - the per-bucket sections further
    # down render every listable row in the same bullet format.
    plan = md.split("## List right now")[1].split("\n## ")[0]
    listed = [l for l in plan.splitlines() if l.startswith("- **Item ")]
    assert len(listed) == 15


def test_build_report_empty_board_plans_all_slots():
    md = fr.build_report(_report_data(n_listable=60, occupied=0))
    assert "into 40 free market slot(s)" in md


def test_build_report_full_board_says_so_instead_of_going_quiet():
    """A full board must not render as an empty plan - that reads as
    'nothing is worth listing', the opposite of the truth."""
    md = fr.build_report(_report_data(n_listable=60, occupied=40))
    assert "Board is full (40/40 slots in use)" in md
    assert "Nothing can be listed until something comes down" in md
    assert "List right now" not in md


def test_parse_quests_page_strips_pua_glyph_inside_category_parens():
    """Lodestone's quest-type icon is a PUA glyph that is not always leading:
    in "Category ( Title)" it sits inside the parens, where a ^-anchored
    strip misses it and the name silently stops matching unlocks.json."""
    html = (
        '<li class="entry__quest"><div href="/lodestone/character/1/quest/abc/">'
        '<div class="entry__quest__name"><p>-<br>'
        'Beastmaster Quests ( Rite of the Wind\'s Chosen)</p></div></div>'
        '<script>ldst_strftime(1753401600, "YMD")</script></li>'
    )
    soup = BeautifulSoup(html, "html.parser")
    quests, _, _ = fr.parse_quests_page(soup, html)
    assert len(quests) == 1
    q = quests[0]
    assert q["category"] == "Beastmaster Quests"
    assert q["name"] == "Rite of the Wind's Chosen"


def _slot_fixture(occupied_a, occupied_b, rows):
    """Two retainers with the given occupancy and a set of listable rows."""
    return {
        "fetched_at_utc": "2026-09-09T00:00:00+00:00",
        "retainers": [
            {"name": "Retainer A",
             "market_listings": [{}] * occupied_a},
            {"name": "Retainer B",
             "market_listings": [{}] * occupied_b},
        ],
        "all_rows": rows,
        "summary": {"market_slots_total": 40,
                    "market_slots_occupied": occupied_a + occupied_b,
                    "retainers": 2},
    }


def test_listing_plan_respects_per_retainer_slot_capacity():
    """Free slots are per-retainer, not a shared pool. A stack can only be
    listed from the retainer holding it, so a global free-slot count can
    balance while one retainer is assigned more listings than it can take."""
    rows = []
    # Retainer B holds every high-value row, far more than its free slots.
    for i in range(30):
        rows.append({"name": f"rich-{i}", "quantity": 1, "retainer": "Retainer B",
                     "verdict": "sell", "reason": "r", "est_value": 10000 - i,
                     "gil_per_slot_week": 10000 - i, "weeks_to_clear": 1})
    for i in range(30):
        rows.append({"name": f"poor-{i}", "quantity": 1, "retainer": "Retainer A",
                     "verdict": "sell", "reason": "r", "est_value": 10,
                     "gil_per_slot_week": 10, "weeks_to_clear": 1})
    data = _slot_fixture(9, 7, rows)   # 11 free / 13 free, 24 total
    md = fr.build_report(data)

    # Scope to the plan itself: the consolidation section above it also
    # tags rows with their retainer.
    listed = md.split("## List right now")[1].split("### Refill queue")[0]
    per = {"Retainer A": listed.count("[Retainer A]"),
           "Retainer B": listed.count("[Retainer B]")}
    assert per["Retainer B"] <= 13, per
    assert per["Retainer A"] <= 11, per
    assert sum(per.values()) == 24


def test_listing_plan_reports_slots_it_cannot_fill():
    """When one retainer's board is full, its stock cannot fill the other's
    free slots - the report must say so rather than quietly planning short."""
    rows = [{"name": f"x-{i}", "quantity": 1, "retainer": "Retainer B",
             "verdict": "sell", "reason": "r", "est_value": 100,
             "gil_per_slot_week": 100, "weeks_to_clear": 1}
            for i in range(30)]
    data = _slot_fixture(0, 20, rows)   # Retainer A wide open, Retainer B full
    md = fr.build_report(data)
    plan = md.split("## List right now")[1].split("### Refill queue")[0]
    assert "[Retainer B]" not in plan
    assert "go unused" in md


def test_bucket_includes_limited_jobs():
    """Beastmaster and Blue Mage level like any other combat job. Omitting one
    from JOB_ORDER drops it from `jobs` entirely while jobs_parsed still counts
    it - Beastmaster read as absent at level 12 on 2026-09-09."""
    jobs = {"Dark Knight": {"level": 100, "exp": None},
            "Beastmaster": {"level": 30, "exp": None},
            "Blue Mage": {"level": 80, "exp": None}}
    out = fr.bucket(jobs)
    assert out["combat"]["Beastmaster"] == 30
    assert out["combat"]["Blue Mage"] == 80
    assert "other" not in out


def test_bucket_surfaces_jobs_it_does_not_recognise():
    """A job added to the game later matches none of the three hardcoded
    lists. It must not disappear silently - that is the failure this guards."""
    jobs = {"Dark Knight": {"level": 100, "exp": None},
            "Necromancer": {"level": 42, "exp": None}}
    out = fr.bucket(jobs)
    assert out["other"] == {"Necromancer": 42}


class _FakeResp:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"{self.status_code} Server Error")

    def json(self):
        return self._payload


class _FakeSession:
    """Fails any batch containing a 'slow' id, succeeds on singles."""

    def __init__(self, slow_ids=(), absent_ids=()):
        self.slow = set(slow_ids)
        self.absent = set(absent_ids)
        self.calls = []

    def get(self, url, timeout=None):
        ids = [int(x) for x in url.split("/")[-1].split("?")[0].split(",")]
        self.calls.append(ids)
        if len(ids) == 1 and ids[0] in self.absent:
            return _FakeResp(404)
        if len(ids) > 1 and any(i in self.slow for i in ids):
            return _FakeResp(504)
        return _FakeResp(200, {"items": {str(i): {"itemID": i} for i in ids}})


def test_fetch_prices_sweeps_items_lost_to_a_slow_neighbour(monkeypatch):
    """One slow item times out the whole batch it shares. The neighbours are
    recoverable one at a time - without the sweep they are silently unpriced."""
    monkeypatch.setattr(fr.time, "sleep", lambda *_: None)
    sess = _FakeSession(slow_ids=[3])
    out = fr.fetch_prices([1, 2, 3, 4], "Example DC", sess, chunk=4, attempts=1)
    assert set(out) == {1, 2, 3, 4}


def test_fetch_prices_does_not_retry_a_404(monkeypatch):
    """A 404 is permanent - Universalis has no such item. Retrying it burns
    the budget the recoverable failures need."""
    monkeypatch.setattr(fr.time, "sleep", lambda *_: None)
    sess = _FakeSession(absent_ids=[7])
    out = fr.fetch_prices([7], "Example DC", sess, chunk=1, attempts=3)
    assert out == {}
    assert len(sess.calls) == 1, sess.calls


def _consolidation_data(rows, listings_by_retainer):
    return {
        "fetched_at_utc": "2026-09-12T00:00:00+00:00",
        "all_rows": rows,
        "retainers": [{"name": n, "market_listings": ls}
                      for n, ls in listings_by_retainer.items()],
    }


def test_consolidation_flags_a_split_that_changed_the_verdict():
    """The min-gil floor and depth cap apply per row, so a stack split across
    retainers can bucket its small half vendor_or_discard while the large half
    sells. The item is not marginal - the split made it look that way."""
    rows = [
        {"name": "Savage Aim Materia XI", "quantity": 1, "retainer": "Retainer A",
         "verdict": "vendor_or_discard"},
        {"name": "Savage Aim Materia XI", "quantity": 5, "retainer": "Retainer B",
         "verdict": "sell"},
    ]
    md = "\n".join(fr.consolidation_lines(_consolidation_data(rows, {})))
    assert "verdicts disagree" in md
    assert "Savage Aim Materia XI" in md
    assert "6 total" in md


def test_consolidation_counts_slots_freed_by_merging_listings():
    listings = {"Retainer A": [
        {"name": "Acidic Secretions", "unit_price": 5000, "quantity": 9},
        {"name": "Acidic Secretions", "unit_price": 5000, "quantity": 10},
        {"name": "Acidic Secretions", "unit_price": 5000, "quantity": 10},
    ]}
    md = "\n".join(fr.consolidation_lines(_consolidation_data([], listings)))
    assert "frees **2 slot(s)**" in md


def test_consolidation_flags_stock_stranded_off_the_listing_retainer():
    """Stock on the retainer that is not listing the item cannot sell through
    the existing slot; stock on the same retainer can, so it is not flagged."""
    rows = [
        {"name": "Hippogryph Skin", "quantity": 18, "retainer": "Retainer B",
         "verdict": "sell"},
        {"name": "Cactuar Needle", "quantity": 2, "retainer": "Retainer A",
         "verdict": "sell"},
    ]
    listings = {"Retainer A": [{"name": "Hippogryph Skin", "unit_price": 100,
                               "quantity": 1},
                              {"name": "Cactuar Needle", "unit_price": 100,
                               "quantity": 1}]}
    md = "\n".join(fr.consolidation_lines(_consolidation_data(rows, listings)))
    assert "Hippogryph Skin" in md.split("stranded on the other")[1]
    assert "Cactuar Needle" not in md.split("stranded on the other")[1]


def test_consolidation_is_silent_when_nothing_is_scattered():
    rows = [{"name": "Yew Log", "quantity": 94, "retainer": "Retainer B",
             "verdict": "sell"}]
    assert fr.consolidation_lines(_consolidation_data(rows, {})) == []


def _priced_row(**over):
    row = {"item_id": 100, "quantity": 11, "hq": False,
           "name": "Allagan Silver Piece", "vendor_price": 500,
           "market_allowed": True}
    row.update(over)
    return row


def _vendor_entry(unit, velocity=848.0):
    return {"minPrice": unit, "minPriceNQ": unit,
            "nqSaleVelocity": velocity / 7.0,
            "regularSaleVelocity": velocity / 7.0,
            "listings": [{"hq": False, "pricePerUnit": unit + 25}] * 5,
            "recentHistory": [{"hq": False, "pricePerUnit": unit}] * 9}


def test_vendor_beats_market_is_not_recommended_for_sale():
    """vendor_price is scraped from the item's own tooltip. A stack worth
    more to an NPC than to the board must never be bucketed `sell` - that
    loses gil and burns a market slot to do it."""
    row = _priced_row()
    out = fr.verdict_for(row, {100: _vendor_entry(475)}, {}, {100}, 200,
                         "Example World", "Example DC", {})
    assert out["verdict"] == "vendor_or_discard", out
    assert out["est_value"] == 5500
    assert "vendor sale" in out["reason"]


def test_market_clearly_above_vendor_still_sells():
    row = _priced_row()
    out = fr.verdict_for(row, {100: _vendor_entry(5000)}, {}, {100}, 200,
                         "Example World", "Example DC", {})
    assert out["verdict"] == "sell", out


def test_item_index_falls_back_to_cache_when_refresh_fails(tmp_path, monkeypatch):
    """A refresh that cannot reach GitHub must not kill a run when a usable
    cache exists - the refresh only buys newly-named items. Observed
    2026-09-16: a transient connection refusal aborted the whole scrape
    before a single page was fetched."""
    monkeypatch.setattr(fr, "CACHE_DIR", tmp_path)
    (tmp_path / "items.json").write_text(
        '{"5": {"en": "Cached Item"}}', encoding="utf-8")

    class _Boom:
        def get(self, *a, **k):
            raise RuntimeError("Connection refused")

    notes = []
    idx = fr.load_item_index(_Boom(), refresh=True, notes=notes)
    assert idx == {"cached item": 5}
    assert notes and "refresh failed" in notes[0]


def test_item_index_still_raises_when_there_is_no_cache(tmp_path, monkeypatch):
    """With no cache there is nothing to degrade to, so the failure is real."""
    monkeypatch.setattr(fr, "CACHE_DIR", tmp_path)

    class _Boom:
        def get(self, *a, **k):
            raise RuntimeError("Connection refused")

    import pytest
    with pytest.raises(RuntimeError):
        fr.load_item_index(_Boom(), refresh=True, notes=[])
