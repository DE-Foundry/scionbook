---
name: inventory-cleanup
description: Review FFXIV retainer inventory, consolidate stacks, protect needed materials, and recommend keep, sell, vendor, or discard actions from saved state. Does not execute in-game actions or refresh character data.
---

# Inventory cleanup

Read scionbook.json `preferences.gameplay` and follow
[gameplay preferences](../../../docs/gameplay-preferences.md). Apply ordered priorities
and relevant standing routines, including exclusions and job/level conditions. Newer
explicit conversation choices take precedence; session-only overrides remain temporary.
Keep durable changes, session choices, and confirmed outcomes separate.

Follow AGENTS.md and shared source/freshness rules. This is analysis in either role, not a role switch.
Read scionbook.json preferences, status.json warnings/gaps, local goals and newer player reports, and the
matching cleanup.md (or report_md), plus quest_mats.json's protected_materials, material_reasons, and coverage_gaps.
Read quest_turnins.json only when the saved research or keeps need review. If inventory is missing/public-only or invalidated by substantial
cleanup, explain the gap and direct a refresh to Maintainer; do not infer empty storage.

Start with a short assessment: storage value estimates, occupied/free market slots by retainer, and
whether a cleanup pass is useful for the player's goal. Do not dump every row by default.

## Protection and disposal

- Apply the player's inventory policy; default conservative. Never assume a blanket liquidation request.
- `keep_unknown`, unresolved/unpriced items, rare/quest/relic items, and explicit keeps are not safe to discard.
  Retainer storage excludes bags, armory, saddlebag, and dresser; do not claim a complete inventory audit.
- Respect protected_quest_material and protected_leveling_item. Review quest-material coverage against
  confirmed reports and quests inferred from job levels plus complete quest history. Use
  [quest-material inference](references/quest-material-inference.md) to select unfinished class quests and
  verify only missing/changed references; do not repeat lookups already saved in the data files or require
  Journal input when saved evidence suffices. Missing/legacy-empty protection or recorded coverage gaps
  means unknown coverage. A validated version 2 empty set can mean all researched needs are completed.
- Maintainer maintains ignored quest_turnins.json and quest_mats.json using the persistent
  [data workflow](../../../docs/crafting-protection.md); full sync reconciles them automatically.
  The Session Planner makes the same inference read-only and records desired changes for recap only.
- A market recommendation must beat the NPC vendor return after applicable fees and time/slot costs.
  Verify item eligibility before vendor/trade-in/discard advice. Keep uncertainties visible.

## Order of operations

1. Identify duplicate item/HQ stacks across storage and listings; consider consolidation before new listings.
   Storage and market_listings are disjoint; recent_sales are gone, never current stock. Distinguish total
   stock from individual market-board listings: each listing holds at most 99 items (or the item's lower
   stack limit). Never recommend one listing above that limit, even when storage holds more.
2. Re-evaluate split-stack verdicts: per-row price floors and depth caps can make a small split look disposable.
   Smaller sale stacks are also a valid strategy: weigh buyer demand, sale speed, and value per slot rather
   than always merging into the largest possible stack. Show the proposed stack sizes and listing count;
   for example, 120 eligible units could be 60 + 60 across two slots, never one listing of 120.
   Consolidation changes quantities and capacity; refresh or clearly mark the subsequent plan provisional.
3. Use [market-update](../market-update/SKILL.md) for repricing/listing decisions. Capacity belongs to each
   retainer, not a shared pool; each split listing consumes one slot. Queue excess stock for later refill.
   Retainers sell only on the character's configured home World. A non_home_world_price row supplies a
   labeled reference for a provisional starting listing price there when local pricing is missing; show
   its source and leave local proceeds/sale speed unestimated. Apply the same material protections and
   stack/slot limits. Other Worlds/DCs are never selling destinations. A MOVE is an inventory/retainer
   transfer, not a change of selling World, and remains proposed until reported.
4. Present practical batches grouped by retainer, honoring configured order (otherwise name order), sorted
   by value within each. Include item, HQ/NQ, quantity, action, reason, and applicable estimated value.

Flag implausible totals, price-like quantities, unresolved names, dropped sale rows, and capacity conflicts
before trusting the plan. Distinguish realistic depth-capped proceeds from optimistic full-stock value.
Never execute or claim sales, moves, deletions, or purchases. Session confirmations use `$tasks` and recap;
Maintainer saves gameplay outcomes only from an explicitly supplied recap.
