# Unlock annotation coverage

`unlocks.json` annotates completed quest names in saved history. It is a curated reference, not a
complete content database or a checklist of what a character still needs to unlock. An absent quest
or annotation is unknown. It does not prove content is locked, and a prerequisite alone does not prove
that a later NPC conversation, duty clear, or separate difficulty unlock happened.

## Review: 2026-09-24

The review expanded coverage beyond one character's jobs and Grand Company:

- Job entry quests cover all jobs currently listed in the report, including the healer and caster paths.
- All three Grand Companies have joining, chocobo, and basic hunt entries.
- Added representative normal raids from Heavensward through Endwalker, optional dungeons from
  Shadowbringers through Dawntrail, field operations, deep dungeons, and Island Sanctuary.
- Corrected Arcadion M1–M4 to Normal. Completing these quests does not establish Savage access.
- Corrected the Sylph daily-quest annotation to `Voyce of Concern`; `Sylph-management` is not that unlock.
- Corrected Beastmaster's entry quest to `Strangers in the Wood`, and distinguished the first Crucible board.
- Distinguished Phantom Village access from entry into Occult Crescent: South Horn.

New and corrected mappings carry a `source` URL. Their evidence comes from the
[job quest tables](https://ffxiv.consolegameswiki.com/wiki/Job_Quests),
[feature quest tables](https://ffxiv.consolegameswiki.com/wiki/Feature_Quests),
[Arcadion quest table](https://ffxiv.consolegameswiki.com/wiki/The_Arcadion#The_Arcadion_Quests),
and the individual quest/duty pages linked in each record. Existing unsourced entries remain inherited
reference data; this review does not certify every old annotation.

## Remaining gaps

Coverage remains partial for MSQ duties, later raid tiers and alliance raids, allied societies,
crafting/gathering delivery systems, relic stages, PvP, and patch-specific unlocks. In particular,
Savage, Extreme, and Ultimate access often involves dialogue absent from completed quest history.
Verify the specific content and prerequisites when planning; do not infer access from job level alone.

## Updating the mapping

Use the exact English completed-quest name as the key. Each value has `type` and a concise `unlock`;
include `source` for additions or corrections. Verify the actual unlock step rather than merely the
start of a quest chain. Label prerequisites as prerequisites if retained. Do not add player state,
coordinates, speculative progress, or a blanket unlock for an entire raid series from its first quest.
A single name cannot distinguish identically named quests; research ambiguous cases instead of guessing.
Tests check parsing, job/company coverage, and known overstatements; they cannot verify live game facts.
