---
name: recap-session
description: Summarize confirmed FFXIV session progress, saved preferences, pending outcomes, and the next starting point. Save outstanding explicit reports locally when asked to save or end the session; no handoff required.
---

# Recap session

Follow AGENTS.md. Review this conversation and relevant local sources only; never retrieve another chat.
Preferences and confirmed reports normally save when supplied through [save-state](../save-state/SKILL.md).
For an explicit save/end-session request, save any outstanding unambiguous reports before reporting success.
For a recap-only request, summarize and identify anything unsaved; a generated recap is not a save.

Produce a concise `Session YYYY-MM-DD recap` in the configured timezone, distinguishing:

- Confirmed progress and dated completions, with known reset-cycle context and source attribution.
- Changed durable preferences and their verified save state; omit unchanged baseline preferences.
- Temporary choices, tentative discussions, pending actions, and material uncertainty, without turning
  them into durable preferences or completed outcomes.
- The actual snapshot timestamp, next starting point, and a separately requested sync if useful.

Do not duplicate saved reports or bump versions when nothing changed. Label saved, already saved,
and unsaved accurately. If writes are unavailable, provide the self-contained recap for manual local
application with [apply-recap](../apply-recap/SKILL.md). Do not claim it was saved.
No automatic sync, commit, push, new chat, or transfer. A user may request a new conversation using the
optional [continuation guidance](../../../docs/chat-handoffs.md), but can keep using this one.
