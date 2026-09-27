# Scionbook crafting protection

Both files are local and ignored by Git. Quest research stays in `quest_turnins.json`; the current material
list, its reasons, and reusable recipe trees stay in `quest_mats.json`. No character data ships in the repo.
Inventory cleanup reads the saved list. Chat context and Scionbook memory are not its source of truth.

## First-time protection

1. Complete character setup and a validated full sync. Public mode cannot infer unfinished quests from
   unavailable private history. If no complete snapshot exists yet, obtain it before building the plan.
2. In Maintainer, request crafting-material protection. Follow
   [quest inference](../.agents/skills/inventory-cleanup/references/quest-material-inference.md) to research
   each relevant class chain through the saved level. Save verified references in a version 2
   `quest_turnins.json`, using the configured character ID and real Lodestone quest IDs. Include explicit
   keeps and level-limited goals only when supported by the user's preferences. Do not copy the examples below.
3. Run the generator with `--status status.json` and inspect its coverage gaps, item reasons and source time.
   It creates `quest_mats.json`, fetching missing recipes. It does not refresh Lodestone or rebuild cleanup.md.
4. On the next explicitly requested sync (or the current sync if protection was requested as part of it),
   stage the snapshot, protection and report together. Resolve errors, disclose uncovered special quests,
   and install matching validated files. Inventory cleanup can then use the saved keep list.

Initial character setup does not fabricate a crafting plan. Once configured, later full syncs reconcile it
automatically; only missing tiers/items or intentionally refreshed references need another lookup.

## Plan format

Version 2 uses the following shape. These are synthetic examples, not real quests or recommended items:

```json
{
  "version": 2,
  "character_id": "12345",
  "coverage": {"Carpenter": 10},
  "quests": [
    {
      "qid": "example-lodestone-quest-id",
      "name": "Example Quest",
      "job": "Carpenter",
      "level": 5,
      "kind": "ordinary",
      "prerequisites": ["example-prior-quest-id"],
      "sources": ["https://example.invalid/quest-reference"],
      "verified_at_utc": "2026-01-01T00:00:00Z",
      "turnins": [{"name": "Example Craft", "quantity": 3, "hq": true}]
    }
  ],
  "keeps": [
    {"name": "Example Material", "reason": "Crafting goal"},
    {"name": "Example Leveling Material", "reason": "Leveling", "job": "Carpenter", "until_level": 20}
  ]
}
```

Use the **Lodestone quest ID** (`quests.recent[].qid`), not an XIVAPI numeric row ID. Keep source URLs,
verification dates, quantities/HQ requirements and prerequisite notes in each quest record. `coverage`
means every relevant quest through that level has been researched, including quests with no normal craft.
Only raise it after checking the chain. Cache future tiers too when researched; retain completed references.
Kinds are `ordinary` (recipe closure), `no_turnin` (empty turnins), and `special` (stored but reported as an
unresolved material-coverage gap). A special quest is never silently treated as a normal recipe.

`keeps` protects exact item types independently of quests. `until_level` expires when that job reaches the
specified level; without it a keep remains until explicitly removed. Quantities/HQ are reference facts;
the current keep list protects item types and does not prove that sufficient quantities are owned.
Prerequisites explain the backlog; unfinished quests below the current level stay protected even while
blocked behind an earlier quest or other unlock.

## Generated data and reconciliation

`quest_mats.json` version 2 includes:

- `source_fetched_at_utc`, `character_id`, and `job_levels`: evidence used for this evaluation.
- `quests`: saved references with `completed`, `unfinished`, or `future` state.
- `protected_materials` and `material_reasons`: the active union of recipe closures and explicit keeps.
- `recipe_cache`, `recipe_checked_at_utc`, and `recipe_source`: reusable recipe trees and lookup provenance.
- `coverage_gaps`: missing researched tiers or unsupported special quests.
- `added_materials` and `released_materials`: changes since the previous evaluation.

A generated timestamp dates the evaluation, not a fresh lookup of every recipe. Existing cached recipes
retain their lookup timestamps; imported legacy cache entries may have no known lookup date.
Only newly needed recipes are queried. Explicit `--refresh-recipes` rebuilds the recipe cache when the
references need updating. A completed quest stops contributing materials, while shared ingredients remain
until every active reason is gone. An empty list with no gaps is valid when no researched needs remain.
Releasing protection is not itself advice to discard an item.

Full authenticated `scionbook_report.py` runs reconcile version 2 plans automatically, using that run's complete
quest history and levels, before building cleanup advice. `--quest-mats` selects the existing cache;
`--quest-mats-out` stages the updated file separately. Sync validates and installs it alongside the matching
snapshot/history/report. Public mode and `--no-quest-mats` do not reconcile or overwrite protection.

For a standalone update from saved state:

```bash
python3 scionbook_quest_mats.py --status status.json --out quest_mats.json
```

Create `.scionbook-tmp/` first, then add `--cache quest_mats.json --out .scionbook-tmp/quest_mats.json`
to the standalone command to stage an update. This changes protection only; retain the existing snapshot/report
until an authorized sync builds matching advice. Invalid identities,
incomplete/older histories, regressed levels, vanished completions, and recipe errors do not replace the
previous protection file. A scrape reports reconciliation failure and uses existing protection provisionally;
sync must resolve that failure before installing the staged set. Look up new quest tiers only when coverage
needs extending; save the references once. Recheck changed references deliberately, not every chat.

Legacy job -> level -> item-name plans remain supported by the generator without `--status`. They do not
identify completed quests; migrate to version 2 by looking up the missing IDs and references while retaining
explicit keeps. Never infer quest completion from level alone or prune from public/incomplete quest history.
