# Scionbook skill guide

Use any workflow by sending `Read .agents/skills/<name>/SKILL.md and follow it: <your request>`.
Provide AGENTS.md and referenced files if your assistant cannot read the repository directly; see
[assistant setup](assistant-setup.md). `$skill-name` in the examples is optional shorthand for clients
with native skill discovery, not a terminal command. Replace bracketed placeholders with your details.
Codex discovers `.agents/skills/`; Claude Code uses `.claude/skills` and `/skill-name`.

For first use, complete the [installation steps](../README.md#get-started), then run `$setup` in a fresh
Repository Maintainer chat. Setup includes the initial refresh. Later sessions use the saved files;
starting a chat does not automatically refresh them.

## Choose a skill and chat

Use **Maintainer** with repository read/write access for setup, saves, refreshes, and repository work. Use **Session**
with read-only for gameplay planning and progress tracking. The four specialist skills work in either
role without changing its permissions. In an established chat, keep its role; use a fresh chat for the
other role. A fresh chat can open in the same app window.

| Skill | Chat | Use it for | Local file effect |
|---|---|---|---|
| [setup](#setup) | Maintainer | Find your character and initialize Scionbook | Saves configuration, creates missing memory/checklist files, performs initial sync |
| [start-maintenance](#start-maintenance) | Fresh Maintainer | Begin repository or data work | None from startup alone |
| [start-session](#start-session) | Fresh or existing Session | Load saved state and plan play | None |
| [tasks](#tasks) | Session | Report progress or ask what remains | Conversation only |
| [recap-session](#recap-session) | Session | Summarize what is worth saving | Outputs recap; offers a separate apply handoff |
| [apply-recap](#apply-recap) | Maintainer | Save a supplied recap | Updates local memory, checklist outcomes, and relevant preferences |
| [sync](#sync) | Maintainer | Refresh Lodestone and reconcile saved state | Updates validated snapshot, applicable history, reports, and configured protection |
| [inventory-cleanup](#inventory-cleanup) | Either | Consolidate and decide what to keep or dispose of | Recommendations; Maintainer can maintain crafting protection when requested |
| [market-update](#market-update) | Either | Review listings, prices, and available selling slots | None |
| [gear-planner](#gear-planner) | Either | Plan upgrades for a particular job and goal | None |
| [hunt-planner](#hunt-planner) | Either | Put supplied hunt targets into practical hunting order | None |

No skill executes in-game actions or automatically commits/pushes. Player files stay local and ignored by
Git. Advice, proposed purchases, and generated recaps do not establish completed or saved progress.

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

Open a fresh chat with repository read/write access, then send:

```text
$start-maintenance
```

You can include a task, such as reviewing documentation or explaining a saved-data warning. This selects
the Maintainer role and reads sources relevant to the request. Startup alone does not refresh data, save
new gameplay reports, begin a gameplay plan, or authorize a commit/push.

## Start session

[Skill instructions](../.agents/skills/start-session/SKILL.md)

After setup succeeds, open a fresh read-only chat:

```text
$start-session I have 45 minutes and want to work on crafting.
```

The skill loads configuration and saved sources, checks snapshot age and reset availability, and suggests
one primary objective with useful next steps. It honors saved preferences and newer reports you supply.
It directs missing setup or needed refreshes to Maintainer; it does not scrape or save files.

You can also use it to resume an existing Session chat. After a Maintainer sync, ask that Session to reload
the saved files while preserving newer conversation reports. This reload does not clear its context.

## Tasks

[Skill instructions](../.agents/skills/tasks/SKILL.md)

Use during a Session to report only what you actually completed or ask for next actions:

```text
$tasks I completed [quest name] and reached level [level] on [job]. What next?
```

```text
$tasks What is still available for this session?
```

The skill tracks dated reports in the conversation, distinguishes confirmed and pending outcomes, and
recommends the next useful action. Nothing is saved to the repository. Use recap-session and apply-recap
to preserve the reports for another chat.

## Recap session

[Skill instructions](../.agents/skills/recap-session/SKILL.md)

Run this in the Session containing your gameplay reports:

```text
$recap-session
```

It outputs one self-contained recap of meaningful confirmed progress, preferences, corrections, pending
outcomes, and the next starting point. It then checks the available transport before offering a handoff.
Generating the recap alone saves nothing.

In the optional Codex desktop draft route, say Yes to open an Apply Recap draft, select workspace-write, paste the
shown recap after “Recap to apply:”, and press Send. After verifying the save, that chat provides a fresh
Maintainer draft. With a supported full-launch route, confirmation forwards the approved recap to an
isolated apply run and then starts a fresh Maintainer. Neither route automatically syncs.

The default route is to copy the approved recap into a separate Maintainer using the portable apply-recap
prompt. See [chat handoffs](chat-handoffs.md) for exact prompts and optional transport limits.

## Apply recap

[Skill instructions](../.agents/skills/apply-recap/SKILL.md)

In Maintainer, supply the actual recap; the skill cannot retrieve another chat:

```text
$apply-recap

[Paste the complete recap here]
```

It reconciles reports into local memory, dated checklist outcomes, and relevant personal preferences.
Reapplying the same recap does not duplicate outcomes. It verifies the save and reports changes or gaps.
Generated snapshot/history files and their scrape timestamps are not advanced by this prose save.

Applying a recap does not refresh Lodestone. Request `$sync` separately when ready, or explicitly ask to
apply the supplied recap **and sync**. A recap that merely mentions needing a sync is not that request.
The requested post-save handoff provides a fresh Maintainer prompt after a verified save; supported client adapters can offer a draft.

## Sync

[Skill instructions](../.agents/skills/sync/SKILL.md)

With the character configured and full-mode credentials available when required, send in Maintainer:

```text
$sync
```

Sync stages and validates a refresh, then reconciles the snapshot, applicable quest history, cleanup
report, memory/checklist, and configured crafting protection. Newer player reports are preserved as dated
reports. Public mode remains limited even after a successful refresh. Failed validation does not replace
the prior validated snapshot. Lodestone can lag after logout; the result reports its actual source time.

After success, sync provides the prompt for a fresh read-only Session. In the optional Codex desktop app route, accepting
prepares a link: open it, select read-only, and press Send. A prepared draft has not started the skill.
The new Session reads the saved files without inheriting the Maintainer transcript.

## Inventory cleanup

[Skill instructions](../.agents/skills/inventory-cleanup/SKILL.md)

Use with a full snapshot containing retainer inventory and its matching cleanup report:

```text
$inventory-cleanup Help me free retainer space. Start with consolidation and keep needed crafting materials.
```

Expect a short assessment followed by practical batches grouped by retainer: item, HQ/NQ, quantity,
recommended action, reason, and applicable value. It protects known needs and flags uncertain items.
Retainer storage is not a complete audit of bags, armory, saddlebag, or dresser. Public-mode or stale
holdings cannot support precise disposal advice; request Maintainer sync when needed. Market-board sale
recommendations cap each listing at 99 items (or a lower item limit), show how larger totals are split,
and consider smaller stacks as a selling strategy. Each split uses a separate retainer listing slot.
Selling recommendations apply only to your configured home World.

For persistent crafting protection, ask Maintainer:

```text
Set up crafting-material protection from my saved job levels and complete quest history.
```

Maintainer researches unfinished crafting quests and saves the plan and recipe-material closure in
`quest_turnins.json` and `quest_mats.json`. Full sync reconciles configured protection as quests are
completed and level-limited keeps expire; job level alone does not prove a quest complete. Coverage gaps
remain explicit. See [crafting protection](crafting-protection.md). In Session, desired protection changes
remain recap requests rather than file edits.

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
refresh private holdings. Stale or missing inventory needs Maintainer sync before precise transactions.
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

## Typical session from start to save

1. Complete `$setup` once in Maintainer, then open a read-only Session with `$start-session`.
2. Use specialist skills as needed and `$tasks` for actual progress reports.
3. Run `$recap-session`, review the recap, and accept the offered handoff if you want it saved.
4. Complete `$apply-recap` in Maintainer; desktop drafts need the recap pasted before Send.
5. Request `$sync` when Lodestone is ready to refresh, then accept the offered fresh Session if desired.

For file ownership and portability, see [local state and privacy](../README.md#local-state-and-privacy).
For CLI entry points and desktop/manual transitions, see [chat handoffs](chat-handoffs.md).
