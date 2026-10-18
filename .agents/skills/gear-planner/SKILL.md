---
name: gear-planner
description: Plan FFXIV gear upgrades, duty item-level gates, and currency spending for the intended job using saved state and current game references. Does not buy items or record unreported upgrades.
---

# Gear planner

Read scionbook.json `preferences.gameplay` and follow
[gameplay preferences](../../../docs/gameplay-preferences.md). Apply ordered priorities
and relevant standing routines, including exclusions and job/level conditions. Newer
explicit conversation choices take precedence; session-only overrides remain temporary.
Keep durable changes, session choices, and confirmed outcomes separate.

Follow AGENTS.md and shared source/freshness rules; usable in either role for analysis.
Identify the intended job and goal. Read current job levels, equipped-job gear attribution, currencies,
completed unlocks, local goals, and newer reports. Never substitute the equipped/highest-level job for the
requested one. Unequipped gear and inventory may be invisible: ask for displayed item level or affected
slots only when needed. Do not ask for levels/balances already supported by current sources.

Verify patch-sensitive duty gates, gear tiers, currencies/caps, token costs, vendors, weekly loot rules,
and acquisition eligibility from current references. No fixed expansion/endgame gear table is authoritative.
Distinguish unlocking a duty, clearing it, weekly eligibility, and having the required currencies/items.

Compare useful item-level gain to cost, time, replacement horizon, and the player's goal. Consider weapon
weight, inexpensive weak-slot upgrades, job quests, dungeon drops, and capped currencies before purchases.
Do not assume accessories always win or prescribe a fixed raid/relic route for every player.

For an average-item-level gate, verify applicable slot rules. Under the standard 12-slot calculation,
a two-handed weapon counts twice; displayed averages are floored. A known upgrade adds weighted item-level
delta / 12. Use the interval implied by the displayed average: distinguish guaranteed gate clearance from
possible clearance when rounding hides the exact total. Never promise an uncertain threshold.

Recommend one practical upgrade path with source, cost, expected benefit, prerequisites, and a stopping
point. Flag important opportunity costs and unverified weekly balances. Respect spoiler preferences and
platform/input context. Currency spending, loot, and purchases stay proposed until the player reports them;
Session Planner uses tasks/recap and Maintainer saves only an explicitly supplied recap.
