---
name: setup
description: Set up Scionbook for a character name and home world, or a Lodestone profile URL. Resolves the character ID, initializes local preferences and sources, and performs the first refresh. Repository Maintainer only.
---

# Setup

Follow AGENTS.md. Establish Repository Maintainer in a fresh chat; in an established Session Planner
chat, direct setup to a separate Maintainer chat. This request authorizes local initialization and the
initial refresh, not Git publishing. Read README.md for installation and commands.

1. Inspect scionbook.json and existing local state before doing anything. One character per checkout.
   Read [gameplay preferences](../../../docs/gameplay-preferences.md). First initialization imports
   a validated local/gameplay-preferences.json seed if present; reruns ignore it.
   Preserve configured preferences and existing progress on reruns; use a separate checkout for another character.
2. Take the full character name and **home world** from the request. Ask only if missing. Accept an official
   Lodestone profile URL or numeric ID as a fallback. Never use a default/example character.
3. Use the repository Python environment (install requirements.txt if needed). Run
   `python3 scionbook_setup.py --name "Character Name" --world "Home World" --lookup-only` or
   `python3 scionbook_setup.py --profile "LODESTONE_PROFILE_URL" --lookup-only`.
   This searches public Lodestone entries, requires an exact name/world match, and verifies the profile.
   Show the resolved profile link/name/world. If lookup fails or is ambiguous, obtain the correct URL;
   do not select the first fuzzy match. HTTP/block/markup failures are not proof the character does not exist.
4. Ask for timezone and whether to use full authenticated or limited public mode if not already known.
   Explain that full mode needs a Lodestone session cookie for the player's own private pages.
   UTC is an available default, not an inferred local timezone. Platform, input method, goals, and
   spoiler tolerance are optional preferences; collect them together without delaying basic setup.
5. Run the same helper without `--lookup-only`, passing the chosen `--timezone IANA_ZONE` and
   `--mode full` or `--mode public`. On reruns omit unchanged options so existing settings are preserved.
   It saves ignored scionbook.json and creates missing memory/checklist files from neutral templates.
   Save optional preferences in scionbook.json; preserve the identity and schema. Never store credentials there.
6. Follow [sync](../sync/SKILL.md) for the initial refresh, including staging and validation. Setup explicitly
   authorizes this first sync. If credentials are unavailable, configuration remains initialized but full
   setup is pending; do not silently switch modes or call it session-ready. Public mode deliberately has no
   private quest history, inventory, or balances. A failed refresh never destroys prior validated state.
7. Explain the [everyday workflow](../../../README.md#everyday-workflow): Session play/tasks → recap →
   Maintainer apply → separately requested sync → fresh Session. Use [handoffs](../../../docs/chat-handoffs.md)
   for the default manual prompts and optional client adapters. Supported app drafts require permissions and Send; the apply draft additionally needs
   the recap pasted into it. Do not offer a second startup prompt if initial sync already handled it.
   Point out inventory, market, gear, and hunt skills. Crafting protection is optional: it needs researched
   quest_turnins.json, not a fabricated default tier; see [initial setup](../../../docs/crafting-protection.md#first-time-protection).
   Report the initialized/refreshed sources, their timestamps, public-mode limits, and any remaining gaps.

A configuration save is not a successful refresh. Do not invent progress, completed chores, goals, or
quest-material protection to populate empty templates. No automatic commit/push. Initial sync may offer
a fresh Session using a manual prompt or a supported confirmed draft/full-launch route; a draft is not a running skill.
