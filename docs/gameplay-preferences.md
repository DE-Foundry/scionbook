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
reconcile the explicit durable change locally rather than deferring it to a recap.
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

## Discussion and immediate saves

Use [save-state](../.agents/skills/save-state/SKILL.md) in the current conversation as soon as the user
clearly establishes a standing preference. The instruction itself authorizes the local save; no recap,
new chat, or repeated confirmation is needed. Preserve identity and unrelated settings, validate, verify
saved bytes, and use the preference immediately. Explicit sync timing/completeness choices live under
preferences.sync, separate from gameplay priorities. Full pricing is assumed when no choice is saved.

Discussing alternatives is welcome and does not establish a preference. “I might focus on crafting” is
exploration; “make crafting my main priority” is a durable change. “Crafting just tonight” is temporary.
Ask only if ambiguity affects what would be persisted, and do not delay unrelated discussion.

Configuration is the current baseline. Local memory may retain useful dated change history, with old
values clearly superseded; do not keep competing current preference lists there. Confirmed outcomes
are dated records separate from preferences and reusable routine boxes. A completed objective does not
silently create another standing goal. Repeated identical changes are no-ops.

A recap can summarize saved changes or import an explicitly supplied report. It is not required for
saving. A preference-only save needs no completion section, snapshot edit, refresh, commit, or push.

## Before character setup

If `scionbook.json` is absent, an explicit gameplay preference may
use ignored `local/gameplay-preferences.json`, containing only a `preferences` object
with an optional `gameplay` object.
Other preference keys in this seed are rejected; configure those after setup. Duplicate
JSON keys and non-finite values are rejected in seeds, configuration, and local save proposals.
Do not fabricate identity or initialize memory/checklist completion records. First setup
validates and imports this seed into configuration alongside normal defaults. Reruns
ignore the seed entirely and preserve configured preferences. Once configuration exists,
the seed is historical, not a second live source. Missing character sources still require
setup in the current conversation before snapshot-based gameplay planning; a seed does not make it ready.
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
Older configuration without gameplay fields remains valid. Existing malformed gameplay
fields are rejected: correct them to the documented object/list types before using
configuration-dependent commands. A setup rerun restores defaults when the entire
preferences key is absent; existing preference objects are preserved unchanged.
To roll back, preserve the ignored local configuration separately and remove only the optional gameplay fields if
needed; older readers can retain them as unknown preferences. Source updates and this
preference format do not require a character refresh. Templates and synthetic tests
must never contain a real player's choices.
