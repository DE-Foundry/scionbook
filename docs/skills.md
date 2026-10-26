# Scionbook skill guide

Use any workflow by sending `Read .agents/skills/<name>/SKILL.md and follow it: <your request>`.
Provide AGENTS.md and referenced files if your assistant cannot read the repository directly; see
[assistant setup](assistant-setup.md). `$skill-name` in the examples is optional shorthand for clients
with native skill discovery, not a terminal command. Replace bracketed placeholders with your details.
Codex discovers `.agents/skills/`; Claude Code uses `.claude/skills` and `/skill-name`.

Complete setup once, then keep using the same conversation for discussion, planning, local saves,
and explicitly requested syncs. Give the player agent local write access. A separate maintenance chat
is optional for application work, never a prerequisite for saving preferences or progress.

## Choose a skill

| Skill | Use it for | Local file effect |
|---|---|---|
| [setup](#setup) | Find your character and initialize Scionbook | Configuration, missing templates, first validated sync |
| [start-session](#start-session) | Begin/resume planning | Loads state; clear new reports/preferences save through save-state |
| [tasks](#tasks) | Report confirmed progress or ask what remains | Saves dated outcomes and clear preferences |
| [save-state](#save-state) | Apply a clear personal change immediately | Validated local preferences, memory, checklist; no scrape |
| [recap-session](#recap-session) | Summarize or finish play | Summary; explicit save/end request also saves outstanding reports |
| [apply-recap](#apply-recap) | Import a supplied report | Local reports/preferences; no transcript retrieval |
| [sync](#sync) | Explicitly refresh character data | Validated snapshot/history/report, reconciliation, same-chat reload |
| [start-maintenance](#start-maintenance) | Explicit application changes | Only requested source changes |
| [inventory-cleanup](#inventory-cleanup) | Storage/protection/disposal advice | Requested protection research may save locally |
| [market-update](#market-update) | Listings, prices, selling slots | Recommendations |
| [gear-planner](#gear-planner) | Upgrades for an intended job | Recommendations |
| [hunt-planner](#hunt-planner) | Route supplied hunt targets | Recommendations |

No skill executes in-game actions or automatically commits/pushes. Personal data stays ignored, never
shared source. Discussion, suggestions, and pending activities do not establish decisions/completions.
Read-only/upload-only clients prepare unsaved proposals and disclose that limit.

## Setup

[Skill instructions](../.agents/skills/setup/SKILL.md)

Supply your full character name and **home world**, or an official Lodestone profile URL:

```text
$setup [Character Name] on [Home World]
```

```text
$setup [Lodestone profile URL], timezone [IANA timezone], public mode
```

Setup resolves and verifies the character ID, asks for missing timezone/mode choices, initializes local
configuration and missing memory/checklist files, and follows sync for the first validated snapshot.
Optional preferences include goals, spoiler tolerance, platform, and input method.

Full mode needs your own authenticated Lodestone session; follow [authentication](../README.md#authentication)
outside chat. Public mode provides limited public data and cannot establish private quests, currencies,
or retainer inventory. Missing data remains unknown. If the refresh fails, configuration may be saved but
setup is not yet session-ready. Rerunning setup preserves existing reports; use another checkout for a
different character.

## Start maintenance

[Skill instructions](../.agents/skills/start-maintenance/SKILL.md)

Use for explicit code, skill, test, or shared documentation work:

```text
$start-maintenance
```

A separate development conversation is optional. Startup alone does not authorize source changes,
gameplay planning, sync, commits, or pushes. Personal preferences never change shared skills.

## Start session

[Skill instructions](../.agents/skills/start-session/SKILL.md)

After setup, continue here or resume later with:

```text
$start-session I have 45 minutes and want to work on crafting.
```

It loads saved state, checks actual snapshot age/reset availability, and suggests useful next actions.
Temporary choices affect the current plan without rewriting standing preferences. Missing setup or an
explicit sync request is handled in this conversation when supported. No fresh chat is required.

## Tasks

[Skill instructions](../.agents/skills/tasks/SKILL.md)

```text
$tasks I completed [quest name] and reached level [level] on [job]. What next?
```

Confirmed reports save locally through save-state, with dates and known reset-cycle context. Questions
about remaining tasks do not establish completion. Pending activities stay pending. Saves never fabricate
a snapshot refresh. The assistant verifies persistence before saying saved and continues the discussion.

## Save state

[Skill instructions](../.agents/skills/save-state/SKILL.md)

```text
Make [objective] my main priority from now on.
```

Clear standing preferences save immediately without a recap or repeated approval. “I might try [activity]”
remains exploration; “just tonight” remains temporary. Configuration is the current baseline; memory
retains dated outcomes or useful superseded history. The deterministic helper prepares originals,
validates permitted changes, rejects concurrent edits, and re-reads saved bytes. It requires Python but
no model or network. See the skill for its stdin proposal format and the pre-setup preference seed.

## Recap session

[Skill instructions](../.agents/skills/recap-session/SKILL.md)

```text
$recap-session
```

Summarizes confirmed progress, changed preferences, pending outcomes, actual snapshot time, and the next
starting point. Saved and unsaved are labeled separately. “Save/end this session” also saves outstanding
clear reports. A recap-only request is a summary, not automatic permission to persist tentative ideas.
No handoff or new conversation follows unless you explicitly request one.

## Apply recap

[Skill instructions](../.agents/skills/apply-recap/SKILL.md)

```text
$apply-recap
[Paste the actual recap here.]
```

Imports a supplied recap in this conversation and verifies its local save. It never retrieves another
chat, duplicates already represented reports, or runs sync unless explicitly asked to do both.
A preference-only recap needs no fabricated completion records. Continue playing here afterward.

## Sync

[Skill instructions](../.agents/skills/sync/SKILL.md)

```text
$sync
```

Stages/validates character data and derived reports, reconciles local records, then reloads sources
and updates current advice in this conversation. Preserves newer explicit reports when Lodestone lags.
Failure preserves prior validated sources. Public-mode private data stays unknown.
Full pricing is assumed; persistent failures offer retry, batches down to one, or explicit acceptance
of remaining gaps for this run. That choice never silently changes the standing preference.

## Inventory cleanup

[Skill instructions](../.agents/skills/inventory-cleanup/SKILL.md)

Use with a full snapshot containing retainer inventory and its matching cleanup report:

```text
$inventory-cleanup Help me free retainer space. Start with consolidation and keep needed crafting materials.
```

Expect a short assessment followed by practical batches grouped by retainer: item, HQ/NQ, quantity,
recommended action, reason, and applicable value. It protects known needs and flags uncertain items.
Retainer storage is not a complete audit of bags, armory, saddlebag, or dresser. Public-mode or stale
holdings cannot support precise disposal advice; explicitly request sync here when needed. Market-board sale
recommendations cap each listing at 99 items (or a lower item limit), show how larger totals are split,
and consider smaller stacks as a selling strategy. Each split uses a separate retainer listing slot.
Selling recommendations apply only to your configured home World.

For persistent crafting protection, ask:

```text
Set up crafting-material protection from my saved job levels and complete quest history.
```

The agent researches unfinished crafting quests and saves the plan and recipe-material closure in
`quest_turnins.json` and `quest_mats.json`. Full sync reconciles configured protection as quests are
completed and level-limited keeps expire; job level alone does not prove a quest complete. Coverage gaps
remain explicit. See [crafting protection](crafting-protection.md). Requested protection changes save locally using that workflow, without a handoff.

## Market update

[Skill instructions](../.agents/skills/market-update/SKILL.md)

Use with saved retainer holdings/listings from full mode:

```text
$market-update Review my listings, suggest repricing, and fill each retainer's available slots.
```

The skill checks current public prices and recent sales, then recommends CHANGE, MOVE, and CREATE actions
with per-listing quantities, unit prices, estimated returns, and reasons. Each listing holds at most 99
items (or a lower item limit); smaller stacks may suit buyer demand. Capacity is checked separately for
each retainer, counting every split listing and queuing excess stock for refill. Retainers sell only on
your configured home World. When local pricing is missing, **Non-home-World price** identifies a reference
you can use as a provisional starting listing price on your home World, with its source shown and local
proceeds/sale speed left unestimated. Other Worlds/DCs are never selling destinations. Consolidation and
protected materials affect recommendations. A public price lookup does not
refresh private holdings. Stale or missing inventory needs an explicitly requested sync before precise transactions.
Nothing is listed, moved, sold, or saved by the skill.

## Gear planner

[Skill instructions](../.agents/skills/gear-planner/SKILL.md)

Name the job and goal, especially if they differ from your equipped job:

```text
$gear-planner Plan affordable upgrades for my [job] so I can enter [duty].
```

The skill uses saved levels, gear, currencies, unlocks, and newer reports, then verifies current costs and
requirements. It asks for missing displayed item level or gear slots only when needed. Expect one upgrade
path with sources, costs, prerequisites, expected benefit, and a stopping point. Unknown balances or
unequipped gear stay unknown; purchases and loot remain proposals until you report them.

## Hunt planner

[Skill instructions](../.agents/skills/hunt-planner/SKILL.md)

Supply target names as text or a readable hunt-bill image. Include job, current level, bill quantities,
and starting location when known:

```text
$hunt-planner Plan these marks in hunting order for [job] at level [level], starting in [zone]:
[target name] — [quantity]
[target name] — [quantity]
```

It verifies targets and locations and returns numbered stops grouped by nearby targets and zones to reduce
travel, with levels, regions, map areas, coordinates, and entry/transition guidance. If no starting point
is supplied, it proposes one. Unknown flight or attunement is not assumed. Above-level, inaccessible,
unverified, and group-dependent targets are listed separately with reasons or conditions; elite spawn
areas do not prove a mark is currently alive. The skill neither tracks kills nor saves progress.

## Typical ongoing session

1. Complete setup and its initial validated sync, then continue in that conversation.
2. Discuss goals and options; clear standing choices save immediately and tentative ideas stay open.
3. Use specialists and report actual progress with tasks; confirmed outcomes save locally.
4. Request sync when needed; choose retry/smaller batches/ignore if pricing failures persist.
5. Optionally request a recap or start a new conversation that reads the durable local files.

See [privacy](../README.md#local-state-and-privacy) and [optional continuation tools](chat-handoffs.md).
