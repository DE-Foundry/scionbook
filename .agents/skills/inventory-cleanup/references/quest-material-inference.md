# Infer crafting-quest material needs

Use job levels and completed quest history together to infer unfinished class quests. A Journal list is
not required. Inference supports conservative material protection; it does not establish accepted quests,
current quest steps, acquired items, or completed turn-ins.

1. Read the configured character's saved crafter levels and full quest history. Check identity, source time,
   quest warnings, and that total_completed equals the number of retained entries. Public, capped, failed,
   or missing history cannot establish non-completion. Preserve existing protection when evidence is missing;
   ask only for the missing evidence or direct an authorized Maintainer refresh. Apply newer explicit player
   reports before the snapshot, but save reported outcomes only through the normal recap workflow.
2. Read quest_turnins.json's saved quest references and quest_mats.json's recipe cache first. Reuse them;
   look up only missing quest tiers/items, changed game data, or an explicitly requested reference refresh.
   Look up the current quest chain for each unlocked crafting class when not yet recorded. Verify exact quest names/IDs, required
   levels, prerequisites, and requested turn-in items against current game references; prefer official
   Lodestone Eorzea Database pages, with XIVAPI recipe data for the material closure. Record source links.
   Do not assume every five-level tier uses a normal inventory craft, or extrapolate across expansions.
3. Subtract completed quests and retain unfinished quests at or below the saved job level. Include earlier
   unfinished tiers even when the job greatly exceeds them. Identify the earliest unfinished prerequisite
   as the next candidate; later eligible tiers remain a backlog, not immediately available quests. An
   unmet story/other unlock does not prove completion; label the dependency and retain conservative
   protection for the known backlog. Future tiers above the job level need an explicit crafting goal.
4. Verify exact turn-in item names, quantities and HQ requirements. Distinguish ordinary recipe ingredients
   from quest-provided/special crafting materials and quests with no item turn-in. Never invent a regular
   recipe for a special hand-in. Keep unsupported special cases visible as coverage gaps.
5. Label the result **inferred unfinished quests**, listing job/level, quest, turn-in, completed-history
   evidence, snapshot date and reference links. Explicit Journal information overrides an inference, but
   do not demand it merely to make the inference. If evidence conflicts, protect the material while resolving
   the conflict instead of silently marking the quest complete.

Store the researched plan in ignored **quest_turnins.json version 2**, using the
[data schema](../../../../docs/crafting-protection.md): character ID, research coverage by job,
quest IDs/names, levels/prerequisites, turn-ins with quantity/HQ, source links/verification dates, and
explicit keeps (optionally expiring at a job level). Keep completed and future quest references for reuse.
This data belongs in the JSON file, not a material list or research notes in Scionbook memory/chat.

Generated **quest_mats.json** holds the persistent recipe cache, evaluated quest states, current protected
materials, per-material reasons, changes since the last evaluation, source snapshot time, and coverage gaps.
Inventory cleanup reads this file first. A version 2 empty list with no coverage gaps means no researched
needs remain for those levels; missing/legacy empty data or gaps still means unknown coverage. Protection
is by item type, not a claim that required quantities/HQ items are already owned. Releasing quest protection
is not a discard instruction; normal inventory policies and other goals still apply.

Maintainer can initialize/update the plan during protection setup or requested sync. Run:
`python3 scionbook_quest_mats.py --status status.json --turnins quest_turnins.json --out quest_mats.json`
This reuses saved recipes, fetches only missing recipes, adds eligible tiers, removes completed-quest needs,
and expires explicit level-limited keeps. Full sync does this reconciliation automatically for version 2 plans
and builds the matching report using the new protection. Use `--refresh-recipes` only for deliberate recipe
reference refreshes. Invalid history, regressed levels, wrong identity, or recipe failures preserve prior
protection; unresolved special crafting needs remain visible gaps. Extend research coverage only where needed.
Session Planner stays read-only; newer reports can guide advice and recap but do not mutate these files.
