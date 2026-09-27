"""Shared unlock annotations must not overstate character progress."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scionbook_quest_history as history
import scionbook_report as report


def test_catalog_has_no_duplicate_names_and_valid_annotations():
    def unique(pairs):
        result = {}
        for key, value in pairs:
            assert key not in result, f'duplicate unlock key: {key}'
            result[key] = value
        return result
    unlocks = json.loads(history.UNLOCKS_PATH.read_text(), object_pairs_hook=unique)
    for name, annotation in unlocks.items():
        assert name.strip() == name and annotation['type'] and annotation['unlock']
        if 'source' in annotation:
            assert annotation['source'].startswith('https://')


def test_all_report_jobs_have_entry_quest_annotations():
    jobs = {v['unlock'].removesuffix(' (limited job)')
            for v in history.load_unlocks().values() if v['type'] == 'Job'}
    assert set(report.JOB_ORDER) <= jobs


def test_each_grand_company_has_join_mount_and_hunt_entries():
    unlocks = history.load_unlocks()
    for company in ('Maelstrom', 'Twin Adder', 'Immortal Flames'):
        for quest in ('The Company You Keep', 'My Little Chocobo', 'Let the Hunt Begin'):
            assert f'{quest} ({company})' in unlocks


def test_normal_raid_history_never_claims_savage_unlocks():
    names = ('The Claw in the Dark', 'Sweet Poison', 'Vile Heat', 'The Neoteric Witch')
    quests = [dict(name=name, category='Raids', epoch=i, date='2026-09-24')
              for i, name in enumerate(names)]
    md = history.render(quests, 4, history.load_unlocks(), '2026-09-24')
    assert '(Savage)' not in md
    assert all(f'M{i} (Normal)' in md for i in range(1, 5))


def test_unresearched_or_prerequisite_quests_remain_unannotated():
    names = ('Sylph-management', 'The Wilds Call', 'Synthetic Unresearched Quest')
    quests = [dict(name=name, category='Other', epoch=i, date='2026-09-24')
              for i, name in enumerate(names)]
    md = history.render(quests, 3, history.load_unlocks(), '2026-09-24')
    assert '**0** are annotated' in md
    assert 'coverage is partial' in md
    assert all(name in md for name in names)
