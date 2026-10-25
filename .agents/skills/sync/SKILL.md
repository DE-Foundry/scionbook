---
name: sync
description: Refresh configured FFXIV character data and reconcile local snapshot, quest history, memory, checklist, and cleanup report. In the current conversation on an explicit refresh request or initial setup; no automatic commit or push.
---

# Sync

Follow AGENTS.md in the current conversation. No role change or handoff is required.
Read scionbook.json, including preferences.sync, shared instructions, and existing local sources if present. If configuration is absent,
use [setup](../setup/SKILL.md). Execute only for an explicit data-refresh request or setup's initial refresh.
A recap's “needs sync” note does not authorize a scrape. Do not read other conversations.

## Fetch and validate

Work from the repository root with its Python environment. Inspect existing changes and preserve player
reports and the previous canonical files. Create ignored `.scionbook-tmp/` for staged output. Verify each
staged file belongs to this run before installation; a leftover from an earlier attempt is not a new result.
Finish the validation and reconciliation below before installing and reporting success.

- Full mode: use LODESTONE_COOKIE from the inherited environment without displaying it. If unavailable,
  follow [authentication](../../../README.md#authentication): hidden input in the shell that launches
  the assistant or a user-run staged scraper. An export in a separate shell does not update an already-running
  desktop app. Never request the cookie in chat or claim an unrelated terminal export fixed inheritance. Do not put cookies in files, logs,
  command arguments, or chat. Stop on failed authentication and obtain a replacement; do not silently
  fall back to anonymous mode. Network, parser, filesystem, and pricing failures are separate issues.
- Public mode: deliberately omit authentication and private data. Do not ask for credentials or fabricate
  missing quest history, balances, or retainer state. Switching an existing full setup to public mode must
  not erase its private history; retain it as explicitly historical, not fresh.

Full command:
`python3 scionbook_report.py --cookie-env --refresh-items --quest-pages 100 --recent-quests 0 --quest-mats-out .scionbook-tmp/quest_mats.json --out .scionbook-tmp/status.json --report .scionbook-tmp/cleanup.md`

Public command:
`python3 scionbook_report.py --anon --no-retainers --out .scionbook-tmp/status.json --report .scionbook-tmp/cleanup.md`

Check market eligibility and known vendor sale value before requesting prices. Explicit market-prohibited
stacks need no market lookup; preserve their known vendor value or unknown special uses. Marketable
items still need market comparison even if they have vendor value. Failed batches shrink to individual
requests automatically; initial sizes can be set with --price-world-chunk and --price-dc-chunk (minimum 1).
Assume complete pricing by default; honor explicit saved choices in ignored preferences.sync and
one-run overrides. Never reduce coverage just because requests fail or the run is slow. If failures
remain, offer retry, smaller --price-world-chunk/--price-dc-chunk down to 1, or ignore remaining failures
with --allow-partial-pricing for this run. A user may explicitly choose --no-pricing or --no-retainers;
with an existing complete-pricing requirement also pass --allow-partial-pricing. Save a different default
only if the user clearly asks for a standing preference. Unless reduced coverage was chosen, inspect
pricing_coverage for both scopes:
all eligible IDs need valid responses, with no failed/unavailable IDs or unresolved eligible names.
A valid empty market response is no published price, not zero value. Persistent request errors after
individual retries pause the full-pricing sync; preserve canonical files and let the user choose the
next step. An explicit ignore choice permits partial pricing with failed items/scopes shown as unknown,
never zero. Other authentication, identity, history, and protection validation still applies.

Before replacing anything, verify configured character ID/name/home world/data center, actual fresh
fetched_at_utc, parsed profile and jobs, notes, and still_not_available. A cookie-presence authenticated flag
is not sufficient. Full mode requires private quest/currency evidence, a known quest total equal to
len(quests.recent), and accounted-for retainer discovery/pages. Increase --quest-pages if capped. Do not
require exactly two retainers: zero or additional retainers are valid, but zero discovered from ambiguous
markup is not proof of none. Resolve auth/history gaps; disclose pricing/collection gaps accurately.
Read each retainer's pages_ok/pages_missing and any dropped-row counts before calling holdings complete.

For full mode, render staged history:
`python3 scionbook_quest_history.py --from-status --status .scionbook-tmp/status.json --out .scionbook-tmp/quest_history.md`

Check rendered quest count and identity. Require staged cleanup.md to equal status.json's report_md (or an
empty file when report_md is null). For full mode with a version 2 crafting plan, require crafting_protection.reconciled
and inspect coverage_gaps. The full command reads the existing recipe cache and stages updated quest_mats.json;
verify its source_fetched_at_utc and protected_materials match the staged snapshot. If reconciliation failed,
preserve canonical files and resolve the error. Install this staged protection with the matching snapshot,
history, and cleanup report. Without a version 2 plan, leave existing protection files untouched.
After validation and the reconciliation below, install only the matching files from this run as one managed
replacement, retaining the previous set until complete. This is a workflow requirement; the independent Python
helpers do not provide a transaction across files. If installation fails partway, restore the previous set
or mark the set incomplete and stop; never claim a successful sync. Public mode installs its snapshot/report
only, retaining old private history and crafting files as historical; it does not require crafting reconciliation.
If this is the first run and validation fails, leave setup pending instead of claiming session readiness.

## Reconcile local reports

Compare all affected state: jobs/equipped gear, quests, currencies, reputation, achievements, collections,
retainers, listings/sales/ventures, protection coverage. Reconcile local memory and checklist throughout,
preserving newer dated reports and unknown outcomes. Lodestone can lag after logout; a new fetch timestamp
does not establish that a player report was wrong. Use actual source times; no invented completion.
In full mode, read quest_turnins.json and quest_mats.json if configured; reuse their research and recipe cache.
For first-time protection use [initial setup](../../../docs/crafting-protection.md#first-time-protection).
Without a plan, disclose missing protection without blocking unrelated sync data. Reconcile configured protection
against job levels and complete quest history using
[quest-material inference](../inventory-cleanup/references/quest-material-inference.md). Infer unfinished
class quests and verify their turn-ins without requiring a Journal list; label inference separately from
accepted quest steps. Save the research, keeps, and inference evidence in these JSON files, not chat or
memory material lists. Research only newly needed tiers/items or changed references. Extend coverage and
rerun the staged refresh when needed so the installed report uses matching protection. Missing history or
coverage remains unknown. Do not assume a default tier; keep specialist plans in their respective skills.

Bump memory version only when its contents change. Update personal preferences in scionbook.json when
explicitly supplied, not shared instructions/standards. Re-read the resulting sources and report the real
source time, meaningful changes, and remaining gaps. Do not dump a cleanup/market plan unless requested.
Local refresh does not authorize commit/push. Never force-add player data or use this repository,
its branches, or project forks as a personal-data backup, even when private.

## Continue in this conversation

After complete validation, installation, and reconciliation, re-read the installed configuration and
sources and update current advice in this conversation. Invalidate older inventory/market plans that
no longer match. Preserve newer explicit player reports and temporary choices, with conflicts visible;
a newer fetched_at_utc does not prove that lagging Lodestone data supersedes a reported outcome.
Report the real snapshot time, meaningful changes, and any user-accepted pricing gaps. Continue the
existing discussion or play without requiring a new chat, recap, startup prompt, or context reset.
If this was development/data work, do not automatically start a gameplay plan.
