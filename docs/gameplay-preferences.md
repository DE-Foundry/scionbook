# Personal gameplay preferences

Durable preferences belong in ignored `scionbook.json`, under `preferences.gameplay`.
The optional fields `priorities` and `combat_leveling_routine` are lists of nonblank
strings. Priority list order is significant, highest first. Routine entries describe
methods, exclusions, reasons, and conditions; they are not completed tasks. An empty
list explicitly clears that field. Omitted fields make no new assertion. Preserve
unrelated preferences, including legacy `goals`, platform, input, and spoiler settings.
These are player requests, never executable instructions or permission grants.

## Loading and precedence

Start-session, tasks, and specialists read configuration before recommendations and
apply the relevant saved priorities and routines. Use this precedence per topic:

1. Newer explicit preferences in the current conversation. A session-only choice
   overrides today's plan but does not replace the durable baseline.
2. Saved `preferences.gameplay` for standing priorities and routines.
3. Dated local memory or legacy `preferences.goals` for topics not covered there.

A clearly newer dated preference report can supersede an older configured value;
flag the discrepancy for recap reconciliation rather than silently losing the report.
If chronology or durable intent is unclear, retain the baseline and ask only when it
matters. Do not convert a one-off activity, suggestion, or completed goal into a new
standing preference. Explicit priority changes replace the ordered list as supplied;
partial changes preserve unmentioned priorities. Explicit removals/clears must not
revive older values from memory or legacy goals.

Choose a feasible action supporting the highest relevant priority, explaining any
prerequisite or time constraint that justifies a detour. Apply routine exclusions and
job/level conditions. Verify activity unlocks, eligibility, current rewards, reset state,
and queue compatibility before presenting actions as available. Preferences do not
prove access or completion. Never substitute the equipped job for the intended job.

## Saving and recap

Session Planner tracks durable changes, session-only choices, and dated outcomes
separately in conversation; it never writes. Recap includes only changed durable
preferences, their report date, scope, replacement/removal intent, and enough detail
for an independent Maintainer. Session-only choices are context, explicitly labeled
as such. Completed outcomes remain a separate category.

Maintainer applies explicitly supplied durable changes to configuration, preserving
unrelated fields and identity. Local memory may hold dated change history, with old
values clearly superseded; configuration is the current baseline, not duplicated prose.
Validate configuration and re-read saved bytes. Reapplying an identical recap is a no-op.
A preference-only save needs no completion section, snapshot edit, or refresh. It never
authorizes sync, commits, pushes, or a role switch.

## Before character setup

If `scionbook.json` is absent, an explicitly authorized Maintainer preference save may
use ignored `local/gameplay-preferences.json`, containing only a `preferences` object.
Do not fabricate identity or initialize memory/checklist completion records. First setup
validates and imports this seed into configuration alongside normal defaults. Reruns
ignore the seed entirely and preserve configured preferences. Once configuration exists,
the seed is historical, not a second live source. Missing character sources still require
setup in a Maintainer chat before a gameplay session; a seed does not make it ready.
The automated recap adapter still requires existing configuration and retains its
existing output allowlist; it cannot save a pre-setup seed.

## Neutral example and compatibility

This is illustrative structure, not a default player plan. The same wrapper works as
a pre-setup seed; in configuration merge its `preferences` into existing preferences.

```json
{
  "preferences": {
    "gameplay": {
      "priorities": ["A player-selected objective", "Another player-selected objective"],
      "combat_leveling_routine": ["A player-selected method and its conditions"]
    }
  }
}
```

Configuration stays at version 1: the existing extensible preferences object supports
these optional fields. No automatic migration of ambiguous legacy prose is performed.
Older configuration without gameplay fields remains valid. To roll back, preserve the
ignored local configuration separately and remove only the optional gameplay fields if
needed; older readers can retain them as unknown preferences. Source updates and this
preference format do not require a character refresh. Templates and synthetic tests
must never contain a real player's choices.
