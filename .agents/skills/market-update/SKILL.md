---
name: market-update
description: Review FFXIV retainer listings, current market prices, recent sales, and free slots; recommend repricing and new listings. Does not execute trades or refresh private character data.
---

# Market update

Follow AGENTS.md and shared source/freshness rules. Analyze in either role without changing permissions.
Read configured home world/data center, preferences, status.json timestamp/warnings/gaps, market_listings,
recent_sales, all_rows, and newer reports. If holdings/listings are stale or unavailable, request Maintainer
sync before a precise plan. A public price lookup does not refresh the player's inventory or balances.
Retainers list and sell only on the character's home World from scionbook.json. State that World in the
plan and prefer its market for selling prices and expected returns. If local pricing is missing but a
non_home_world_price reference exists, show “Non-home-World price,” its source World/DC, quality, and
available timestamp. It can be used as a provisional starting listing price on the home World; check that
board when possible. Keep these proposals separate from locally priced recommendations, count their
listing slots, and leave local proceeds/sale speed unestimated. Other Worlds/DCs are never selling destinations.

1. Show occupied/free slots per retainer, existing listing value, and relevant recent sales separately.
   Listed items are not in storage; sales history is already sold. Never double-count them.
2. Check consolidation opportunities with [inventory-cleanup](../inventory-cleanup/SKILL.md). Apply its
   quest/leveling/unknown-item protections before recommending any new listing.
3. Verify current prices via Universalis or the player's in-game board, using item ID, home world, HQ/NQ,
   stack size, and update timestamp. Public market lookup is allowed in either role. Cached snapshot
   estimates and historical sales alone do not establish the current lowest listing. Universalis data can lag.
4. Compare current listings, recent sale velocity and depth, NPC vendor alternatives, taxes/fees, and value
   per occupied slot over time. A high past sale does not prove current underpricing; pricing_calibration
   compares different times. Flag sparse/stale data and price_suspect instead of giving false precision.
5. Recommend CHANGE for existing listings, MOVE for consolidation/transfers, and CREATE for new listings.
   Cap every proposed listing at 99 items or the item's lower stack limit. Distinguish total available stock
   from per-listing quantity; show stack sizes and number of listings. Consider smaller stacks based on
   buyer demand, sale speed, and value per slot; do not automatically favor stacks of 99.
   Each split listing consumes one of the owning retainer's slots. Each CREATE must fit that retainer's
   own free slots. Count proposed delists/transfers explicitly; do not treat them as already done. A MOVE
   changes inventory/retainer allocation, never the selling World. Group by configured retainer order
   (otherwise name), then value. Include item, HQ/NQ, per-listing quantity, gil per unit, estimated net
   return per listing, and a brief reason; label any batch totals separately.
6. Separate immediately actionable listings from a refill queue, including stock that exceeds available
   listing slots. Label other World/DC prices as comparisons, provisional home-World asking prices when
   local pricing is missing, or potential buying opportunities, with their
   source World/DC and timestamp. Verify travel/purchase restrictions before recommending a buying trip;
   visiting another World/DC never makes it a retainer selling destination.

Start with a concise update and highest-value changes. Distinguish conservative proceeds from optimistic
full-stock totals. Stop on missing identity, holdings, or pricing evidence rather than recommending guessed
transactions. No in-game actions, automatic refresh, credential requests, repository writes, or implied completions.
