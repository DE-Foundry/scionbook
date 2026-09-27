#!/usr/bin/env python3
"""Regenerate quest_history.md: the full completed-quest list, annotated with
unlocks.json where a quest is known to unlock a dungeon/trial/raid/job/etc.

Two ways to run:
  --from-status   render from status.json's quests.recent (fast, but that
                   field is capped at --recent-quests items in scionbook_report.py
                   and is NOT the full history unless that run used a large
                   --quest-pages/--recent-quests).
  --cookie-env     do a fresh full-history pull (all pages) and render from
                   that. Slower (one request per history page), needs a live
                   ldst_sess cookie in $LODESTONE_COOKIE.

unlocks.json is a curated, player-independent mapping (quest name -> {type,
unlock}) maintained by hand/research over time. It is intentionally sparse -
most quests unlock nothing notable and simply won't appear in it. Missing
from unlocks.json means "not yet researched," not "confirmed no unlock."
"""
import argparse
import collections
import json
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scionbook_report as fr
import requests
from scionbook_config import CONFIG_PATH, load_config
from scionbook_http import HTTP_HEADERS

REPO = pathlib.Path(__file__).parent
UNLOCKS_PATH = REPO / "unlocks.json"
OUT_PATH = REPO / "quest_history.md"


def load_unlocks():
    if not UNLOCKS_PATH.exists():
        return {}
    return json.loads(UNLOCKS_PATH.read_text())


def render(quests, total, unlocks, fetched_date, name="Character", world="Unknown world"):
    by_cat = collections.defaultdict(list)
    for q in quests:
        by_cat[q["category"]].append(q)
    cat_order = sorted(by_cat, key=lambda c: min(q["epoch"] for q in by_cat[c]))

    unlock_count = sum(1 for q in quests if q["name"] in unlocks)

    lines = [
        f"# Completed Quests — {name} ({world})",
        "",
        f"Total: **{total}** quests, generated from Lodestone quest history on "
        f"{fetched_date}. **{unlock_count}** are annotated with a known unlock "
        f"(see `unlocks.json` — coverage is partial by design, not every quest "
        f"has been researched).",
        "",
        "Grouped by category, oldest to newest within each. Categories ordered "
        "by when they were first started.",
        "",
    ]
    for cat in cat_order:
        items = sorted(by_cat[cat], key=lambda q: q["epoch"])
        lines.append(f"## {cat} ({len(items)})")
        lines.append("")
        for q in items:
            unlock = unlocks.get(q["name"])
            tag = f" — **{unlock['unlock']}** ({unlock['type']})" if unlock else ""
            lines.append(f"- {q['date']} — {q['name']}{tag}")
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--from-status", action="store_true",
                      help="render from status.json's quests.recent")
    src.add_argument("--cookie-env", action="store_true",
                      help="do a fresh full-history pull ($LODESTONE_COOKIE)")
    ap.add_argument("--config", default=str(CONFIG_PATH))
    ap.add_argument("--status", type=pathlib.Path, default=REPO / "status.json")
    ap.add_argument("--out", type=pathlib.Path, default=OUT_PATH)
    ap.add_argument("--pages", type=int, default=100, help="max history pages; increase if incomplete")
    args = ap.parse_args()

    unlocks = load_unlocks()

    if args.from_status:
        status = json.loads(args.status.read_text())
        name = status.get("character", {}).get("name")
        world = status.get("world")
        if not name or not world:
            sys.exit("Snapshot has no verified character identity.")
        config = load_config(args.config, required=False)
        if config and str(status.get("character_id")) != config["character_id"]:
            sys.exit("Snapshot belongs to a different character.")
        q = status["quests"]
        quests, total, fetched_date = q["recent"], q["total_completed"], status["fetched_at_utc"][:10]
        if len(quests) < (total or 0):
            print(f"WARNING: status.json only carries {len(quests)}/{total} "
                  f"quests (quests.recent is capped) — this is NOT the full "
                  f"history. Use --cookie-env for a complete regeneration.",
                  file=sys.stderr)
    else:
        try:
            config = load_config(args.config)
        except ValueError as exc:
            sys.exit(str(exc))
        if config["mode"] != "full":
            sys.exit("Private quest refresh requires configured full mode. "
                     "Public mode can only render previously saved history with --from-status.")
        name, world = config["name"], config["world"]
        cookie = os.environ.get("LODESTONE_COOKIE", "").strip()
        if not cookie:
            sys.exit("LODESTONE_COOKIE is empty.")
        fr.HEADERS["Cookie"] = cookie if "=" in cookie else f"ldst_sess={cookie}"
        session = requests.Session()
        session.headers.update(HTTP_HEADERS)
        quests, total, pages, note = fr.fetch_quests(config["character_id"], session, pages=args.pages)
        if note:
            sys.exit(f"quest fetch failed: {note}")
        if len(quests) < (total or 0):
            print(f"WARNING: only fetched {len(quests)}/{total} quests across "
                  f"{pages} pages — increase --pages.", file=sys.stderr)
        import datetime
        fetched_date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

    if total is None or len(quests) != total:
        sys.exit("Incomplete or unavailable quest history; previous output preserved.")
    md = render(quests, total, unlocks, fetched_date, name, world)
    args.out.write_text(md, encoding="utf-8")
    print(f"wrote {args.out} ({len(quests)} quests, "
          f"{sum(1 for q in quests if q['name'] in unlocks)} annotated)")


if __name__ == "__main__":
    main()
