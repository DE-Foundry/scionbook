"""Exercise market eligibility through the real report/pricing pipeline, offline."""
import json
import pathlib
import sys
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import scionbook_report as report


class PricingSession:
    def __init__(self, catalog, available=(1,), dc_available=None, dc_price=500):
        self.headers = {}
        self.catalog = catalog
        self.dc_price = dc_price
        self.available = set(available)
        self.dc_available = self.available if dc_available is None else set(dc_available)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(url)
        if url.endswith('/marketable'):
            if isinstance(self.catalog, Exception):
                raise self.catalog
            payload = self.catalog
        else:
            parsed = urlsplit(url)
            scope, ids = parsed.path.rsplit('/', 2)[-2:]
            available = self.dc_available if scope == 'Example DC' else self.available
            price = self.dc_price if scope == 'Example DC' else 500
            payload = {'items': {str(i): {
                'itemID': i, 'nqSaleVelocity': 20,
                'recentHistory': [{'hq': False, 'pricePerUnit': price}] * 5,
                'listings': [{'hq': False, 'pricePerUnit': price * 1.2, 'quantity': 50}],
            } for i in map(int, ids.split(',')) if i in available}}
        return SimpleNamespace(status_code=200, json=lambda: payload,
                               raise_for_status=lambda: None)


@pytest.fixture
def run_report(monkeypatch, tmp_path):
    profile = '<p class="frame__chara__name">Example Adventurer</p><p class="frame__chara__world">Example World [Example DC]</p>'
    soup = BeautifulSoup(profile, 'html.parser')
    monkeypatch.setattr(report, 'HEADERS', {})
    monkeypatch.setenv('LODESTONE_COOKIE', 'synthetic-cookie')
    monkeypatch.setattr(report, 'fetch', lambda *a, **k: (soup, profile))
    monkeypatch.setattr(report, 'parse_class_job', lambda *a: {'Carpenter': {'level': 1}})
    monkeypatch.setattr(report, 'fetch_quests', lambda *a, **k: ([], 0, 1, None))
    monkeypatch.setattr(report, 'fetch_currency', lambda *a, **k: ({'Gil': 100}, None, None, None))
    monkeypatch.setattr(report, 'find_retainer_index', lambda *a, **k: ('example', soup, profile))
    monkeypatch.setattr(report, 'parse_retainer_list', lambda *a: [{'name': 'Retainer A', 'retainer_id': 'example'}])
    monkeypatch.setattr(report, 'fetch_vendor_buy_prices', lambda *a, **k: {})
    monkeypatch.setattr(report.time, 'sleep', lambda _: None)

    def run(catalog, ids=(1, 2, 3, 4), available=(1,), dc_available=None, protection_args=None, dc_price=500, vendor_price=None):
        session = PricingSession(catalog, available, dc_available, dc_price)
        monkeypatch.setattr(report.requests, 'Session', lambda: session)
        monkeypatch.setattr(report, 'load_item_index', lambda *a: {f'item {i}': i for i in ids})
        monkeypatch.setattr(report, 'scrape_retainer', lambda *a, **k: {
            'retainer_id': 'example', 'inventory': [
                {'name': f'Item {i}', 'quantity': 1, 'hq': False, 'vendor_price': vendor_price}
                for i in ids], 'market_listings': [], 'recent_sales': []})
        output = tmp_path / 'status.json'
        monkeypatch.setattr(sys, 'argv', ['scionbook_report.py', '--id', '12345',
            '--world', 'Example World', '--dc', 'Example DC', '--cookie-env',
            '--fast', '--out', str(output)] + (protection_args if protection_args is not None else ['--no-quest-mats']))
        report.main()
        return session, json.loads(output.read_text())
    return run


def pricing_calls(session):
    return [url for url in session.calls if not url.endswith('/marketable')]


def test_mixed_inventory_filters_both_scopes_before_batches_and_retries(run_report):
    session, data = run_report([1])
    assert session.calls[0].endswith('/marketable')
    calls = pricing_calls(session)
    assert len(calls) == 2
    assert {urlsplit(u).path.rsplit('/', 2)[-2] for u in calls} == {'Example World', 'Example DC'}
    for url in calls:
        assert urlsplit(url).path.endswith('/1')
        assert parse_qs(urlsplit(url).query) == {'listings': ['50'], 'entries': ['50']}
    assert len(data['all_rows']) == 4
    assert data['all_rows'][0]['price_source'] == 'history_median'
    for row in data['all_rows'][1:]:
        assert row['verdict'] == 'keep_unknown'
        assert 'untradeable' in row['reason']
    assert not any('DC pricing' in n for n in data['notes'])


def test_all_nonmarketable_inventory_makes_no_price_requests(run_report):
    session, data = run_report([999])
    assert not pricing_calls(session)
    assert all('untradeable' in r['reason'] for r in data['all_rows'])
    assert not any('returned no data' in n or 'DC pricing' in n for n in data['notes'])


@pytest.mark.parametrize('catalog', [requests.Timeout(), [], {}, {'error': 'down'}, None, [True], ['1'], [0], [1, -2]])
def test_unavailable_or_malformed_catalog_keeps_unpriced_rows_unknown(run_report, catalog):
    session, data = run_report(catalog)
    assert pricing_calls(session)  # legacy lookups still recover usable prices
    assert data['all_rows'][0]['price_source'] == 'history_median'
    assert any('marketable list unavailable' in n for n in data['notes'])
    for row in data['all_rows'][1:]:
        assert row['verdict'] == 'keep_unknown'
        assert 'untradeable' not in row['reason']


def test_total_pricing_outage_preserves_known_nonmarketable_classification(run_report):
    session, data = run_report([1], available=())
    assert all(urlsplit(u).path.endswith('/1') for u in pricing_calls(session))
    assert data['all_rows'][0]['verdict'] == 'keep_unknown'
    assert 'pricing unavailable' in data['all_rows'][0]['reason']
    assert all('untradeable' in r['reason'] for r in data['all_rows'][1:])


def test_dc_coverage_denominator_only_counts_eligible_unique_ids(run_report):
    _, data = run_report([1, 2], ids=(1, 1, 2, 3, 4), dc_available=())
    assert any('0/2 items' in n for n in data['notes'])


def test_report_reconciles_and_stages_protection_before_building_cleanup(run_report, tmp_path, monkeypatch):
    import crafting_protection as cp
    import scionbook_quest_mats as mats
    source, cache, staged = (tmp_path / name for name in ('turnins.json', 'cache.json', 'staged-mats.json'))
    cp.write_json(source, {
        'version': 2, 'character_id': '12345', 'coverage': {'Carpenter': 10},
        'quests': [{'qid': 'a', 'name': 'Quest A', 'job': 'Carpenter', 'level': 1,
                    'kind': 'ordinary', 'sources': ['https://example.invalid/quest'],
                    'verified_at_utc': '2026-01-01T00:00:00Z',
                    'turnins': [{'name': 'Item 1', 'quantity': 1, 'hq': False}]}]})
    monkeypatch.setattr(mats, 'find_recipe', lambda name, session:
        {'Ingredient': [], 'AmountResult': 1, 'AmountIngredient': []} if name == 'Item 1' else None)
    args = ['--quest-turnins', str(source), '--quest-mats', str(cache), '--quest-mats-out', str(staged)]
    _, first = run_report([1], protection_args=args)
    saved = cp.read_json(staged)
    assert not cache.exists()  # canonical cache untouched by staged refresh
    assert saved['source_fetched_at_utc'] == first['fetched_at_utc']
    assert first['crafting_protection']['protected_materials'] == saved['protected_materials']
    assert first['all_rows'][0]['verdict'] == 'protected_quest_material'
    assert first['summary']['estimated_recoverable_gil'] == 0
    cp.write_json(cache, saved)
    before = cache.read_bytes()
    monkeypatch.setattr(mats, 'find_recipe', lambda *a: pytest.fail('cached recipe was fetched again'))
    _, second = run_report([1], protection_args=args)
    assert second['all_rows'][0]['verdict'] == 'protected_quest_material'
    monkeypatch.setattr(report, 'fetch_quests', lambda *a, **k: ([{'qid': 'a', 'name': 'Quest A'}], 1, 1, None))
    _, completed = run_report([1], protection_args=args)
    assert completed['crafting_protection']['reconciled'] is True
    assert completed['crafting_protection']['protected_materials'] == []
    assert 'Item 1' in completed['crafting_protection']['released_materials']
    assert completed['all_rows'][0]['verdict'] == 'sell'
    assert completed['summary']['estimated_recoverable_gil'] == 500
    assert cache.read_bytes() == before
    assert not any('zero protected' in n or 'outgrown' in n for n in completed['notes'])


@pytest.mark.parametrize('dc_price', [50, 5000])
def test_dc_prices_do_not_change_home_world_sale_plan_or_totals(run_report, dc_price):
    _, data = run_report([1], ids=(1,), dc_price=dc_price)
    row = data['all_rows'][0]
    assert row['verdict'] == 'sell'
    assert row['unit_price'] == 500
    assert row['est_value'] == 500
    assert 'on Example World' in row['reason']
    assert data['summary']['estimated_recoverable_gil'] == 500
    assert data['summary']['estimated_recoverable_gil_optimistic'] == 500
    assert data['summary']['market_slots_planned'] == 1
    assert '**Selling World: Example World**' in data['report_md']
    assert 'Worth travelling' not in data['report_md']
    assert 'on Example DC' not in data['report_md']


def test_dc_only_prices_offer_labeled_reference_without_estimated_proceeds(run_report):
    _, data = run_report([1], ids=(1,), available=(), dc_available=(1,))
    row = data['all_rows'][0]
    assert row['verdict'] == 'non_home_world_price'
    assert row['unit_price'] == 500
    assert row['price_reference_scope'] == 'Example DC'
    assert row['est_value'] is None
    assert 'starting listing price on Example World' in row['reason']
    assert data['summary']['estimated_recoverable_gil'] == 0
    assert data['summary']['estimated_recoverable_gil_optimistic'] == 0
    assert data['summary']['market_slots_planned'] == 0
    assert '## Sell on your world' not in data['report_md']
    assert '## Non-home-World price' in data['report_md']
    assert '~500g/unit from Example DC' in data['report_md']
    assert '## Unresolved' not in data['report_md']
    assert 'Worth travelling' not in data['report_md']


@pytest.mark.parametrize("catalog", [[1], None])
def test_total_pricing_outage_preserves_vendor_proceeds(run_report, catalog):
    _, data = run_report(catalog, ids=(1,), available=(), vendor_price=50)
    row = data['all_rows'][0]
    assert row['verdict'] == 'vendor_or_discard'
    assert row['est_value'] == 50
    assert row['est_value_realistic'] == row['est_value_optimistic'] == 50
    assert 'known vendor sale ~50g' in data['report_md']
    # The report aggregate covers market sales, not vendor proceeds.
    assert data['summary']['estimated_recoverable_gil'] == 0
    assert data['summary']['market_slots_planned'] == 0


def test_dc_only_reference_is_checked_for_npc_shop_warning(run_report, monkeypatch):
    candidates = []
    def vendor_prices(ids, session, **kwargs):
        candidates.extend(kwargs['candidates'])
        return {1: 1000}
    monkeypatch.setattr(report, 'fetch_vendor_buy_prices', vendor_prices)
    _, data = run_report([1], ids=(1,), available=(), dc_available=(1,), dc_price=5000)
    assert candidates == [1]
    row = data['all_rows'][0]
    assert row['unit_price'] == 5000
    assert row['est_value'] is None
    assert 'NPC sells this for 1,000' in data['report_md']
