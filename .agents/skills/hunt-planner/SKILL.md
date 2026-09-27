---
name: hunt-planner
description: Look up FFXIV hunt mark targets supplied by the user and organize them into a practical hunting route that reduces travel. Include target names, levels, regions, areas, coordinates, and suitability for the hunting job. Use for hunt bills, daily marks, elite marks, or requests to locate a list of hunt targets. Read-only reference lookup; does not track kills or save progress.
---

# Hunt planner

Read root AGENTS.md and standards.md. This is a read-only game-reference lookup usable in either scionbook role without switching roles or starting a gameplay session. Never write files, scrape character data, run sync, or infer hunt completion. Use public enemy/location references, not character databases.

## Input and lookup

- Accept target names as a pasted list, comma-separated text, or a readable hunt-bill image. Preserve supplied rank, zone, and quantity context. If no targets were supplied, ask for the list.
- Resolve each target's exact in-game name. Correct an obvious typo only when the match is clear. If a name has multiple plausible matches, ask a short clarification for that target while returning the verified remainder; do not silently substitute a different enemy.
- Browse to verify both enemy levels and locations for this request. Prefer the FFXIV Console Games Wiki and Gamer Escape enemy/location pages, using linked maps or another reliable hunt reference when necessary. Search queries/snippets alone are not sufficient evidence for a coordinate. If sources conflict, resolve the matching enemy, population, zone, and map or mark the affected level/location field unverified. Use the actual enemy level or population's level range, not the hunt-bill tier, quest level, or zone's general level. Tie each level/range to the specific location in that row.
- Use hunt-bill zone/rank information to choose the matching population when a target occurs in several places. Without that context, include the verified alternatives needed to disambiguate. For ordinary mobs, one verified representative hunting spot per matching area is enough; label approximate positions or ranges as such.
- For roaming elite marks, label coordinates as possible spawn locations or a search area. Include a concise linked spawn map when there are many locations. Static sources do not establish a currently alive mark, an exact present position, or a respawn time.
- If the location cannot be verified, retain the target with the missing field marked **Unverified** and briefly state what is missing. Never invent coordinates or use (0, 0) as a placeholder.

## Suitability for the hunting job

Read status.json's timestamp, notes, still_not_available, and job levels, plus relevant Scionbook instructions/memory and newer reports in this conversation. Prefer the job the user says they will hunt on; otherwise use the established current hunting/leveling job and state that assumption. Do not silently use a higher-level main job or the snapshot's equipped job when the user is leveling another job. If the intended job or usable current level remains unclear, ask that focused question while returning verified target details.

State the comparison basis briefly before the table, for example: **Planning for the selected job at its last known level — saved snapshot [date]; newer session reports take precedence.** Use actual evidence, not this example as a fixed default. If the snapshot is stale, label the level as last known and seek confirmation only when needed for the comparison; do not run a refresh.

- Compare each target to that job's level. For a range, use the **upper end**: a range straddling the player's level is not wholly within level.
- Flag above-level targets explicitly by name and level difference, and recommend skipping them on that job. Keep them visible in a separate skip/conditional list so no supplied mark is silently lost or included as a recommended stop. If a separately verified lower-level population exists, show its own location and range rather than implying every spawn is manageable.
- A target at or below the player's level is only **within level**, not guaranteed safe. Consider verified elite rank, solo/group expectations, known gear limitations, and dangerous surrounding enemies when relevant. Do not infer safety from a quest's level or an unlock.
- Label elite/group targets separately even when their level is below the player; verify difficulty expectations before suggesting a solo attempt. Missing level/rank evidence means **suitability unverified**, not safe.
- Do not automatically replace the leveling job with a stronger job. A job switch can be offered as an option when supported by the player's saved state and the activity's restrictions.

## Hunting order

Plan travel order by default; do not preserve the pasted target order unless the user requests it.

- Group suitable targets by zone and nearby hunting spots. Order zone visits to reduce repeated teleports,
  transitions, and backtracking; finish a local cluster before leaving when practical. Account for actual
  connections and travel effort rather than alphabetical ordering or coordinate distance alone.
- Start from the player's current location when supplied. Otherwise choose a practical verified entry point
  and state it as the proposed start. Do not delay a useful route just to ask where the player is standing.
- Verify relevant aetherytes, zone entrances, map layers and travel restrictions. Use known attunements,
  flying/access unlocks and user travel preferences. When unknown, label the dependency and give a viable
  ground/entrance alternative where verified; do not assume an unlocked teleport or flight route.
- Within a zone, follow a sensible sweep from the entry point, accounting for terrain and exits. Coordinates
  on different maps are not comparable distances. Describe the result as a practical low-travel route, not
  a proven shortest route; omit precise travel-time claims without evidence.
- When several populations satisfy the same supplied target, select the verified suitable spot that best
  fits the route. Label other locations as alternatives, not extra required kills or stops. Keep supplied
  quantities/rank constraints; never shorten travel by substituting a different target.
- Keep above-level, inaccessible, unverified and group-dependent targets out of the main solo route unless
  suitability/access is established for the requested plan. List them separately with reasons or conditions.
  Roaming elites are conditional search detours, not guaranteed encounters at a fixed coordinate.

## Output

State the proposed start and relevant travel assumptions, then return a concise table in recommended hunting
order. Number the stops; group consecutive stops by zone and briefly name the entry/teleport or transition
when it changes. Include enough travel guidance to follow the order without repeating a full itinerary.

| Stop | Name | Level / range | Region | Area | Coordinates |
|---|---|---|---|---|---|
| 1 | [Verified target name](source URL) | Verified level or range | Broad region | Map zone | X: value, Y: value |

**Region** means the broad geographic region. **Area** means the named map zone within it. Do not substitute a subarea for the map zone.

Coordinates use the named in-game map, not world-space coordinates. Include Z or a map layer only when sourced and needed to distinguish floors or elevation. Link the source on each target name. Give alternative locations separately with their own map/source; do not number them as additional required stops.

After the route, account for every remaining supplied target in a skip/conditional list with its verified level/location details where available. Give brief, target-specific suitability notes: which marks are above the hunting job's level and should be skipped, which need separate elite/group assessment, and which remain unverified. If none exceed it, say the ordinary targets are within the stated level without promising safe kills. Keep other notes limited to ambiguity, approximate positions, multiple spawn sites, or sourced access restrictions. A listed mark does not prove access, an accepted bill, or a kill.

The default deliverable is the ordered hunt route, concise travel guidance, and suitability notes. Do not add a combat guide or completion checklist unless asked. The repository's no-table rule applies to the saved daily/weekly checklist, not this chat lookup.
