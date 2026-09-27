---
name: recap-session
description: Output one combined FFXIV worth-saving recap from the Session Planner conversation and offer a confirmed handoff to apply-recap followed by a fresh Maintainer context. Use for recap session, end session, save session, or what's worth saving. Does not directly edit gameplay files.
---

# Recap session

Follow root AGENTS.md's Session Planner role. Generate the recap without directly writing files, running sync, committing, or pushing. A confirmed handoff is the narrow transport exception described in [chat handoffs](../../../docs/chat-handoffs.md); it does not switch the current chat's role or permissions.

Review this conversation and the five Scionbook sources already loaded. Re-read relevant sources if needed, but do not search other chats or global memories. If invoked in the Maintainer chat without the gameplay conversation, request a recap from the Session Planner rather than inventing or retrieving its context.

Produce `What's worth saving from Session YYYY-MM-DD`, using the session's date in the configured timezone. Include only meaningful information needed for a self-contained handoff:

- The source snapshot's actual fetched_at_utc and the report's session date; distinguish player reports, snapshot facts, and externally verified corrections (retain useful source links).
- Confirmed gameplay progress, exact known levels/equipment/purchases, completed quests/unlocks, and dated checked tasks (`- [x]`) with reset-cycle context where known.
- Durable preferences and standing behavior changes, corrections to source files, and changes to active goals.
- Pending or unconfirmed outcomes and relevant uncertainties. Accepted quests, suggestions, queued duties, and proposed purchases remain pending. Use justified dates or user-supplied conditions for expiring notes, not invented deadlines.
- The best starting point for the next session and any needed sync, especially after substantial inventory or quest progress. Mark sync as a separate future request after Lodestone has had time to update following logout, not an action authorized by applying the recap.

Keep it concise but sufficient for a Maintainer with no access to this conversation. Omit empty categories and routine unchanged baseline facts. Do not treat a canceled/withdrawn request as a new update. If asked again, provide a consolidated current recap without duplicate items; a prior recap does not prove it was applied.

## Handoff

Use the manual prompts in [chat handoffs](../../../docs/chat-handoffs.md) by default. After the complete
recap, explain that the user can paste it with the apply-recap prompt into a fresh Maintainer with file
write access. Do not ask permission to perform a transition you cannot execute. If nothing is worth
saving, do not offer an empty apply operation.

Optional automation applies only when the current client supports the documented adapter and the user
chooses it. Check transport before asking for Yes and disclose required user actions. For Codex, use
[its integration](../../../docs/integrations/codex.md): a draft requires pasting the recap and pressing Send;
a full launch requires an isolated verified apply followed by a fresh visible Maintainer. Never run a
hidden interactive CLI or switch the current chat's role. Reuse approval for the exact recap; changed
content needs renewed approval. No or silence causes no action. Failed/partial saves stop the sequence.

The destination owns save verification. The source Session never reads another chat to check its outcome.
Keep recap ready, prompt/draft prepared, save verified, and new chat started distinct. Do not automatically
sync. The final fresh Maintainer receives only the startup prompt, without the recap or transcript.
