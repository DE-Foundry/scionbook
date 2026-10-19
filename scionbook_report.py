#!/usr/bin/env python3
"""
FFXIV Lodestone -> status.json

One scraper for everything the Lodestone will give up:
profile, all job levels, quest history, currencies, reputation, achievements,
collections, retainer inventories, Universalis pricing, and cleanup verdicts.

Deps:  pip install requests beautifulsoup4

    python3 scionbook_report.py  # configured mode; hidden cookie prompt in full mode

    python3 scionbook_report.py --cookie-env --fast          # skip achievements/collections
    python3 scionbook_report.py --cookie-env --no-retainers  # character data only
    python3 scionbook_report.py --cookie-env --probe --dump ./raw

Auth: quest history, currencies and retainers only exist for a logged-in
session viewing its own character. Anonymously they 404, and anonymous public
pages are served from a hard CDN cache that can lag days.
    DevTools > Application > Cookies > na.finalfantasyxiv.com > ldst_sess

TWO HARD LIMITS, do not try to code around them:
  1. Gear and item level exist only for the CURRENTLY EQUIPPED job. All job
     LEVELS are available; gear for unequipped jobs is not, at all.
  2. Retainer storage is the only inventory exposed. Character bags, armory
     chest, chocobo saddlebag, armoire and glamour dresser are not available.
"""

import argparse
import getpass
import json
import os
import pathlib
import re
import sys
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
from scionbook_config import CONFIG_PATH, resolve_identity, resolve_mode
from scionbook_http import LODESTONE, LODESTONE_HEADERS, HTTP_HEADERS

BASE = f"{LODESTONE}/character"

ITEMS_URL = ("https://raw.githubusercontent.com/ffxiv-teamcraft/ffxiv-teamcraft"
             "/staging/libs/data/src/lib/json/items.json")
UNIVERSALIS = "https://universalis.app/api/v2"
# Game-data sheets (item vendor prices, shop membership). The v1 xivapi.com
# host no longer serves current item rows - it 404s on anything Dawntrail-era
# (confirmed 2026-09-03 for item 46854) - so use the beta host, which does.
XIVAPI = "https://beta.xivapi.com/api/1"
CACHE_DIR = pathlib.Path.home() / ".cache" / "scionbook"

HEADERS = dict(LODESTONE_HEADERS)

JOB_ORDER = [
    "Paladin", "Warrior", "Dark Knight", "Gunbreaker",
    "Monk", "Dragoon", "Ninja", "Samurai", "Reaper", "Viper",
    "Bard", "Machinist", "Dancer",
    "Black Mage", "Summoner", "Red Mage", "Pictomancer",
    "White Mage", "Scholar", "Astrologian", "Sage",
    # Limited jobs. They level and appear on the Lodestone like any other
    # combat job, so they belong here - omitting one drops it silently.
    "Blue Mage", "Beastmaster",
]
DOH = ["Carpenter", "Blacksmith", "Armorer", "Goldsmith",
       "Leatherworker", "Weaver", "Alchemist", "Culinarian"]
DOL = ["Miner", "Botanist", "Fisher"]
ACHIEVEMENT_KINDS = range(1, 14)

RETAINER_INDEX_CANDIDATES = [
    "{base}/character/{cid}/retainer/",
    "{base}/my/retainer/",
    "{base}/retainer/",
]
# Confirmed against a live authenticated session (2026-08-28): the retainer
# only has three real subpages. "" is the "Market" tab (recent completed
# sales history, with buyer name - NOT current inventory). "baggage/" is
# actual storage. "venture/" is the current/last venture report. Everything
# else in the old candidate list (inventory/, item/, marketitem/, sale/,
# markethistory/, history/) 404s.
RETAINER_SUBPAGES = ["", "baggage/", "venture/"]

# Confirmed live (2026-08-28): 20 market-board listing slots per retainer,
# fixed, not upgradeable. Two retainers = 40 total regardless of how many
# stacks the character owns.
MARKET_SLOTS_PER_RETAINER = 20

# How many weeks of "realistic" absorption to assume when a stack is far
# bigger than what the market actually clears per week. See est_value_realistic.
DEPTH_HORIZON_WEEKS = 4

# Below this many units sold per week an item is "listable but barely moves".
# pick_velocity returns per-week units, so this is roughly one sale a month.
SLOW_VELOCITY_PER_WEEK = 0.25

# When undercutting is modelled, assume you list this far below the cheapest
# current ask to actually be the one that sells. See effective_sale_price.
UNDERCUT_FACTOR = 0.95

# Flag prices above an NPC's purchase price for review. Shop access can be
# quest-gated, so this threshold produces a warning, never an automatic cap.
VENDOR_CEILING_MULTIPLIER = 1.0

# Don't bother cross-checking a local price against the DC below this unit
# price: a 3x gap on a 5g bait item is noise, not evidence.
DISPERSION_MIN_UNIT_PRICE = 500

# The min_gil floor scales down as market slots free up (see main()), but
# never below this - a 2g stack of bait isn't worth the real-world time to
# list regardless of how empty the board is. min_gil itself (the
# --min-gil default, 1000) is the ceiling of that scale, approached as
# slots fill up.
MIN_GIL_NUISANCE_FLOOR = 200

# Bump these when the tomestone rotation changes (roughly once an expansion,
# sometimes mid-expansion - see e.g. patch 7.4's Mathematics -> Mnemonics
# swap). The Lodestone currency page appears to omit zero-balance rows
# entirely, so a currently-relevant tomestone the character has never
# earned won't appear in the scrape at all - it has to be backfilled
# explicitly as a confirmed zero, or it reads as "we didn't look."
CURRENT_TOMESTONES_CAPPED = ["Allagan Tomestone of Mnemonics"]
CURRENT_TOMESTONES_UNCAPPED = ["Allagan Tomestone of Poetics"]

GC_SEAL_NAME = {
    "Maelstrom": "Storm Seals",
    "Order of the Twin Adder": "Serpent Seals",
    "Immortal Flames": "Flame Seals",
}

# Baseline facts that are true regardless of what this particular run
# managed to fetch - the Lodestone structurally never exposes these.
# Run-specific gaps (a section that came back null/empty this time) are
# appended dynamically in derive_still_not_available().
STRUCTURAL_LIMITS = [
    "gear / item level for any job other than the equipped one",
    "character bags, armory chest, chocobo saddlebag, armoire, dresser",
    "retainer gear and item level",
    "aether currents / flying unlocks per zone",
    "hotbar and HUD setup",
    "weekly lockouts (Wondrous Tails, raid reentry)",
]


# --------------------------------------------------------------------------- #
# transport
# --------------------------------------------------------------------------- #

def fetch(url, session, dump_dir=None, label="", soft=False):
    """soft=True returns (None, None, status) instead of raising on 404."""
    bust = f"{'&' if '?' in url else '?'}_={int(time.time() * 1000)}"
    try:
        resp = session.get(url + bust, headers=HEADERS, timeout=30)
    except requests.RequestException:
        if soft:
            return None, None, None
        raise
    if dump_dir and resp.status_code == 200:
        p = pathlib.Path(dump_dir)
        p.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", label or "page")
        (p / f"{safe}.html").write_text(resp.text, encoding="utf-8")
    if resp.status_code == 404:
        if soft:
            return None, None, 404
        raise FileNotFoundError(url)
    if soft and resp.status_code != 200:
        return None, None, resp.status_code
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    return (soup, resp.text, 200) if soft else (soup, resp.text)


def looks_logged_out(html):
    if not html:
        return False
    if "My Quests" in html or "Currencies" in html:
        return False
    return "lodestone/account/login" in html and "Log In" in html


# --------------------------------------------------------------------------- #
# profile + jobs
# --------------------------------------------------------------------------- #

def text_or_none(node):
    return node.get_text(strip=True) if node else None


def block_by_title(soup, title):
    for t in soup.select(".character-block__title"):
        if t.get_text(strip=True).lower() == title.lower():
            block = t.find_parent(class_="character-block")
            if block:
                name = block.select_one(".character-block__name")
                if name:
                    return name.get_text(" ", strip=True)
    return None


def parse_profile(soup, html):
    out = {
        "name": text_or_none(soup.select_one(".frame__chara__name")),
        "world": text_or_none(soup.select_one(".frame__chara__world")),
        "title": text_or_none(soup.select_one(".frame__chara__title")),
        "race_clan_gender": block_by_title(soup, "Race/Clan/Gender"),
        "nameday": block_by_title(soup, "Nameday"),
        "guardian": block_by_title(soup, "Guardian"),
        "city_state": block_by_title(soup, "City-state"),
        "grand_company": block_by_title(soup, "Grand Company"),
    }

    fc = soup.select_one(".character__freecompany__name h4 a")
    if fc:
        out["free_company"] = fc.get_text(strip=True)
        m = re.search(r"/freecompany/(\d+)", fc.get("href", ""))
        out["free_company_id"] = m.group(1) if m else None
    else:
        out["free_company"] = None

    ilvl = soup.select_one(".character__item_level")
    m = re.search(r"(\d+)", ilvl.get_text()) if ilvl else \
        re.search(r"Average Item Level[:\s]*(\d+)", html)
    # NOT a character-wide gear score. The Lodestone only renders the currently
    # equipped job's gear, so this describes whatever job you logged out on.
    out["equipped_job_avg_item_level"] = int(m.group(1)) if m else None

    m = re.search(r"LEVEL\s*(\d+)", html)
    out["equipped_job_level"] = int(m.group(1)) if m else None

    icon = soup.select_one(".character__class_icon img[alt], "
                           ".character__class__data img[alt]")
    out["equipped_job"] = icon.get("alt").strip() if icon and icon.get("alt") \
        else None

    attrs = {}
    for row in soup.select(".character__param__list tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) >= 2:
            k, v = cells[0].get_text(strip=True), cells[-1].get_text(strip=True)
            if k and v.isdigit():
                attrs[k] = int(v)
    out["attributes"] = attrs or None

    if not out.get("equipped_job_avg_item_level") and \
            attrs.get("Average Item Level"):
        out["equipped_job_avg_item_level"] = attrs["Average Item Level"]

    # Staleness canary: portrait URLs carry a cache token.
    m = re.search(r"img2\.finalfantasyxiv\.com/f/[^\"'\s]+\?(\d{10})", html)
    if m:
        ts = int(m.group(1))
        out["portrait_cache_token"] = ts
        out["portrait_cache_time_utc"] = datetime.fromtimestamp(
            ts, tz=timezone.utc).isoformat()
        age_h = (time.time() - ts) / 3600
        out["portrait_cache_age_hours"] = round(age_h, 1)
        if age_h > 24:
            out["staleness_warning"] = (
                f"Public page appears ~{age_h/24:.1f} days stale (CDN cache). "
                "Numbers may lag actual gameplay.")
    return out


def parse_class_job(soup, html):
    jobs = {}
    for name_el in soup.select(".character__job__name"):
        li = name_el.find_parent("li") or name_el.parent
        lvl_el = li.select_one(".character__job__level") if li else None
        exp_el = li.select_one(".character__job__exp") if li else None
        name = name_el.get_text(strip=True).split("/")[-1].strip()
        raw = lvl_el.get_text(strip=True) if lvl_el else "-"
        jobs[name] = {"level": int(raw) if raw.isdigit() else None,
                      "exp": exp_el.get_text(strip=True) if exp_el else None}

    if not jobs:
        for n, l in re.findall(
            r'character__job__name[^>]*>([^<]+)<.*?'
            r'character__job__level[^>]*>([^<]+)<', html, re.S,
        ):
            n, l = n.split("/")[-1].strip(), l.strip()
            jobs[n] = {"level": int(l) if l.isdigit() else None, "exp": None}
    return jobs


def bucket(jobs):
    def grab(names):
        return {n: jobs[n]["level"] for n in names
                if n in jobs and jobs[n]["level"]}
    out = {"combat": grab(JOB_ORDER), "crafters": grab(DOH),
           "gatherers": grab(DOL)}
    # The three lists are hardcoded, so a job Square adds later lands in no
    # bucket and vanishes from `jobs` entirely while jobs_parsed still counts
    # it. Surface leftovers instead of
    # dropping them; an unexpected key is a far cheaper failure than a
    # missing job nobody notices.
    placed = set(out["combat"]) | set(out["crafters"]) | set(out["gatherers"])
    other = {n: j["level"] for n, j in jobs.items()
             if n not in placed and j.get("level")}
    if other:
        out["other"] = other
    return out


def attribute_item_level(character, jobs, buckets):
    """Attribute item level to the equipped job, never to other jobs."""
    lvl = character.get("equipped_job_level")
    if not character.get("equipped_job") and lvl:
        cands = [n for n, j in jobs.items() if j.get("level") == lvl]
        if len(cands) == 1:
            character["equipped_job"] = cands[0]
        elif cands:
            character["equipped_job_candidates"] = sorted(cands)

    combat = buckets.get("combat") or {}
    if combat and lvl:
        top = max(combat.values())
        if lvl < top:
            main = "/".join(n for n, v in combat.items() if v == top)
            character["item_level_scope_warning"] = (
                f"equipped_job_avg_item_level "
                f"({character.get('equipped_job_avg_item_level')}) describes "
                f"{character.get('equipped_job') or f'a level {lvl} job'}, NOT "
                f"{main} at {top}. The Lodestone cannot show gear for "
                f"unequipped jobs - log out on the job you want measured.")


# --------------------------------------------------------------------------- #
# quests
# --------------------------------------------------------------------------- #

def split_category(text):
    """'Category (Title)' -> (category, title). Split on the FIRST paren:
    titles can themselves contain parens."""
    if text and text.endswith(")") and "(" in text:
        i = text.index("(")
        return text[:i].strip(), text[i + 1:-1].strip()
    return None, text


def parse_quests_page(soup, html):
    # The visible <span> is a "-" placeholder; the real completion time lives
    # in an inline ldst_strftime(<epoch>) call, so read the epoch.
    quests = []
    for li in soup.select("li.entry__quest"):
        inner = li.find("div", href=True)
        qid = inner["href"].rstrip("/").split("/")[-1] if inner else None
        epoch = None
        scr = li.find("script")
        if scr and scr.string:
            m = re.search(r"ldst_strftime\((\d+)", scr.string)
            if m:
                epoch = int(m.group(1))
        full = None
        p = li.select_one(".entry__quest__name p")
        if p:
            br = p.find("br")
            if br and br.next_sibling:
                full = br.next_sibling.strip()
            if not full:
                bits = [t.strip() for t in p.stripped_strings
                        if t.strip() and t.strip() != "-"]
                full = bits[-1] if bits else None
        if full:
            # Lodestone renders a quest-type icon as a Private Use Area glyph
            # directly in the name text (e.g. " Forging the Phantasmal");
            # .strip() doesn't touch it since it isn't whitespace.
            # It is not always leading: in "Category ( Title)" form the
            # glyph sits inside the parens, so strip every occurrence.
            full = re.sub(r"[-]+\s*", "", full).strip()
        cat, name = split_category(full) if full else (None, full)
        quests.append({
            "date": (datetime.fromtimestamp(epoch, tz=timezone.utc)
                     .strftime("%Y-%m-%d") if epoch else None),
            "epoch": epoch, "category": cat, "name": name, "qid": qid})

    tm = re.search(r"([\d,]+)\s*Total", html)
    pm = re.search(r"Page\s+\d+\s+of\s+(\d+)", html)
    return (quests,
            int(tm.group(1).replace(",", "")) if tm else None,
            int(pm.group(1)) if pm else None)


def fetch_quests(char_id, session, dump_dir=None, pages=1, polite=0.4):
    all_q, total, page_count, note = [], None, None, None
    for page in range(1, pages + 1):
        url = f"{BASE}/{char_id}/quest/?sort=1&page={page}"
        try:
            soup, html = fetch(url, session, dump_dir,
                               f"quest_p{page}" if dump_dir else "")
        except FileNotFoundError:
            note = "quest/ returned 404 - needs a logged-in session cookie."
            break
        except requests.RequestException as e:
            note = f"quest fetch failed: {e}"
            break
        if looks_logged_out(html):
            note = "Not authenticated - cookie missing or expired."
            break
        q, t, pc = parse_quests_page(soup, html)
        total = total or t
        page_count = page_count or pc
        all_q.extend(q)
        time.sleep(polite)
        if pc and page >= pc:
            break
    return all_q, total, page_count, note


# --------------------------------------------------------------------------- #
# currencies / reputation
# --------------------------------------------------------------------------- #

def parse_currency(soup, html):
    currencies, reputation = {}, {}
    for row in soup.find_all(["tr", "li", "div"]):
        cells = row.find_all(["th", "td"], recursive=False)
        if len(cells) == 2:
            k = cells[0].get_text(" ", strip=True)
            v = cells[1].get_text(" ", strip=True)
            if k and re.fullmatch(r"[\d,]+(\s*/\s*[\d,]+)?", v):
                currencies[k] = v

    if not currencies:
        # A trailing `\s*\n` here would greedily eat every blank line up to
        # the START of the next label too, consuming the leading \n the next
        # match needs to anchor on - re.finditer never backtracks across an
        # already-consumed region, so every other label/value pair silently
        # vanishes. Confirmed live, 2026-08-28: a currency page with both an
        # inactive former-GC seal box and the active current-GC one lost the
        # second ("Flame Seals") to exactly this. A lookahead instead of a
        # consuming match leaves the boundary for the next label alone.
        flat = re.sub(r"<[^>]+>", "\n", html)
        for m in re.finditer(
            r"\n\s*([A-Z][A-Za-z'\- ]{2,40})\s*\n\s*"
            r"([\d,]+(?:\s*/\s*[\d,]+)?)(?=\s*\n)", flat,
        ):
            currencies[m.group(1).strip()] = m.group(2).strip()

    block = soup.select_one(".character__reputation")
    if block:
        comm = block.select_one(
            ".character__reputation__list .character-block__value")
        if comm:
            reputation["Commendations Received"] = comm.get_text(strip=True)
        societies = []
        for li in block.select(".character__beastman_relations__list li"):
            nm = li.select_one(".character-block__box--beast_tribe__name")
            rk = li.select_one(".character-block__friendship")
            pt = li.select_one(".character-block__point")
            if nm:
                societies.append({
                    "name": nm.get_text(strip=True),
                    "rank": rk.get_text(strip=True) if rk else None,
                    "progress": pt.get_text(strip=True) if pt else None})
        if societies:
            reputation["societies"] = societies

    # Company Seals render as TWO boxes for anyone who has ever changed
    # Grand Company: the current GC's active, earnable balance, and a frozen
    # leftover balance from whichever GC they left (marked
    # `character-block--off`, no earn cap shown). Both are real currency
    # amounts and both belong in `currencies` - the generic scans above
    # already put them there - but only the active one should ever be
    # compared against the profile's stated affiliation. Recovered
    # separately here since neither generic scan can see CSS state.
    active_seal = None
    for box in soup.select(".currency__box"):
        name_el = box.select_one(".currency__box__text__name")
        if not name_el or name_el.get_text(strip=True) not in {"Storm Seals", "Serpent Seals", "Flame Seals"}:
            continue
        if "character-block--off" not in (box.get("class") or []):
            active_seal = name_el.get_text(strip=True)
    return currencies or None, reputation or None, active_seal


def fetch_currency(char_id, session, dump_dir=None):
    try:
        soup, html = fetch(f"{BASE}/{char_id}/currency/", session,
                           dump_dir, "currency" if dump_dir else "")
    except FileNotFoundError:
        return None, None, None, "currency/ returned 404 - needs a logged-in cookie."
    except requests.RequestException as e:
        return None, None, None, f"currency fetch failed: {e}"
    if looks_logged_out(html):
        return None, None, None, "Not authenticated - cookie missing or expired."
    cur, rep, active_seal = parse_currency(soup, html)
    return cur, rep, active_seal, None


def reconcile_currencies(character, currencies, active_seal):
    """The Lodestone currency page appears to omit zero-balance rows
    entirely rather than showing "0" - confirmed indirectly: a character
    with no Allagan Tomestone of Mnemonics (the current weekly-capped tome
    as of patch 7.4) simply has no row for it, while an old capped tome the
    character no longer earns (e.g. Mathematics) keeps showing because its
    leftover balance is nonzero. Left alone, that reads as "we didn't look"
    instead of "you have zero" - so backfill known-current tomestones
    explicitly, and tag which ones were backfilled vs actually scraped.

    Also cross-checks the ACTIVE Grand Company seal currency (see
    parse_currency - a character who has ever switched GC shows both a
    frozen legacy seal balance and the current active one, which is normal
    and not itself a problem) against the profile's stated affiliation, and
    raises a loud, structured warning if they disagree - genuinely
    contradictory data between two freshly-fetched pages, not explainable
    by the legacy-seal mechanic."""
    currencies = dict(currencies or {})
    inferred_zero = []
    for name in CURRENT_TOMESTONES_CAPPED + CURRENT_TOMESTONES_UNCAPPED:
        if name not in currencies:
            currencies[name] = "0"
            inferred_zero.append(name)

    gc_warning = None
    gc_raw = (character or {}).get("grand_company") or ""
    gc_name = gc_raw.split("/")[0].strip()
    expected_seal = GC_SEAL_NAME.get(gc_name)
    if expected_seal and active_seal and active_seal != expected_seal:
        gc_warning = (
            f"GRAND COMPANY / SEAL MISMATCH: profile says '{gc_name}' "
            f"(expects active seal '{expected_seal}') but the currency "
            f"page's active seal box is '{active_seal}'. One of "
            "parse_profile's Grand Company block or parse_currency's "
            "active-seal detection is reading stale/wrong data - do not "
            "trust either the affiliation or the seal balance until this "
            "is resolved by hand.")
    return currencies, inferred_zero, gc_warning


# --------------------------------------------------------------------------- #
# achievements + collections
# --------------------------------------------------------------------------- #

def parse_achievements_page(soup, html):
    entries = []
    for li in soup.select("li.entry"):
        name_el = li.select_one(".entry__activity__txt")
        if not name_el:
            continue
        name = name_el.get_text(" ", strip=True)
        name = re.sub(r'^.*?achievement\s*["\u201c]?', "", name, flags=re.I)
        name = name.strip().strip('".\u201d\u201c')
        m = re.search(r"ldst_strftime\((\d+)", str(li))
        epoch = int(m.group(1)) if m else None
        link = li.select_one("a.entry__achievement")
        aid = None
        if link:
            m2 = re.search(r"/achievement/detail/(\d+)", link.get("href", ""))
            aid = m2.group(1) if m2 else None
        entries.append({
            "name": name, "id": aid, "completed_epoch": epoch,
            "completed_utc": (datetime.fromtimestamp(epoch, tz=timezone.utc)
                              .isoformat() if epoch else None)})
    has_next = bool(soup.select_one(".btn__pager__next:not(.btn__pager__no)"))
    return entries, has_next


def fetch_achievements(char_id, session, dump_dir=None, max_pages=4, polite=0.4):
    all_entries, note, points = [], None, None
    for kind in ACHIEVEMENT_KINDS:
        for page in range(1, max_pages + 1):
            url = f"{BASE}/{char_id}/achievement/kind/{kind}/?page={page}"
            try:
                soup, html = fetch(url, session, dump_dir,
                                   f"ach_k{kind}_p{page}" if dump_dir else "")
            except (FileNotFoundError, requests.RequestException):
                break
            if "private" in html.lower() and not soup.select("li.entry"):
                return [], None, ("Achievements are private. Lodestone > "
                                  "Character Settings > Public/Private.")
            if points is None:
                pt = soup.select_one(".achievement__point")
                if pt:
                    m = re.search(r"([\d,]+)", pt.get_text())
                    if m:
                        points = int(m.group(1).replace(",", ""))
            entries, has_next = parse_achievements_page(soup, html)
            all_entries.extend(entries)
            time.sleep(polite)
            if not has_next or not entries:
                break

    seen, deduped = set(), []
    for e in sorted(all_entries, key=lambda x: x["completed_epoch"] or 0,
                    reverse=True):
        key = e["id"] or e["name"]
        if key not in seen:
            seen.add(key)
            deduped.append(e)
    return deduped, points, note


def fetch_collection(char_id, session, kind, dump_dir=None):
    """Confirmed live (2026-08-28): the mount/minion page no longer embeds
    names anywhere in the static HTML - each icon `<li>` now carries a
    `data-tooltip_href="/lodestone/character/<id>/<kind>/tooltip/<hash>"`
    that the client fetches on hover. Recovering names would mean one extra
    request per mount/minion; not done here. The icon count is still real,
    static data though (confirmed: 18 `.character__item_icon` elements
    matched a page with 0 recoverable names) - report that instead of
    letting an absent name list erase an available count."""
    try:
        soup, _ = fetch(f"{BASE}/{char_id}/{kind}/", session,
                        dump_dir, kind if dump_dir else "")
    except (FileNotFoundError, requests.RequestException):
        return None, None
    icons = soup.select(".character__item_icon")
    names = [el.get("data-tooltip") or el.get("title") for el in icons]
    names = [n.strip() for n in names if n]
    if not names:
        names = [e.get_text(strip=True)
                 for e in soup.select(".mount__name, .minion__name")
                 if e.get_text(strip=True)]
    uniq = sorted(set(names))
    count = len(uniq) if uniq else (len(icons) or None)
    return (uniq or None), count


# --------------------------------------------------------------------------- #
# retainers
# --------------------------------------------------------------------------- #

def find_retainer_index(char_id, session, dump_dir=None, verbose=False):
    for tmpl in RETAINER_INDEX_CANDIDATES:
        url = tmpl.format(base=LODESTONE, cid=char_id)
        soup, html, status = fetch(url, session, dump_dir, "retainer_index",
                                   soft=True)
        if verbose:
            print(f"  probe {url} -> {status}", file=sys.stderr)
        if status == 200 and not looks_logged_out(html):
            return url, soup, html
    return None, None, None


def parse_retainer_list(soup, html):
    # Real markup: /lodestone/character/<char id>/retainer/<hex id>/. Keep the
    # older /lodestone/retainer/ and /lodestone/my/retainer/ shapes as a
    # fallback in case a locale or a future markup change drops the
    # character segment - cheap insurance, costs nothing when unused.
    pattern = r"/lodestone/(?:character/\d+/|my/)?retainer/([0-9a-f]{6,})/?"
    found = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http"):
            # Absolute links are the locale switcher (na./eu./jp./...) - same
            # retainer, but the link text is a language name, not its name.
            continue
        m = re.search(pattern, href)
        if not m:
            continue
        rid, name = m.group(1), a.get_text(" ", strip=True)
        if rid not in found or (name and len(name) > len(found[rid])):
            found[rid] = name
    if not found:
        for rid in set(re.findall(pattern, html or "")):
            found[rid] = ""
    return [{"retainer_id": r, "name": n or None} for r, n in found.items()]


def parse_qty(text):
    m = re.search(r"([\d,]+)", text or "")
    return int(m.group(1).replace(",", "")) if m else 1


def parse_baggage_rows(soup):
    """Retainer storage ("baggage/"): name + quantity, plus whatever the
    item's own tooltip footer tells us for free (it's already in the page we
    fetched) - NPC vendor sell price and market-board eligibility. That
    footer is real, scraped data, not a fabricated fallback."""
    rows = []
    for li in soup.select("li.item-list__list[data-stack]"):
        # The icon's tooltip also carries a db/item/ link with no text; the
        # visible name link lives in .item-list__name specifically.
        a = li.select_one('.item-list__name a[href*="/playguide/db/item/"]')
        if a is None:
            continue
        name = a.get_text(" ", strip=True)
        if not name:
            continue
        hq = "\ue03c" in name
        stack = li.get("data-stack", "")
        if stack.isdigit():
            qty = int(stack)
        else:
            num_el = li.select_one(".item-list__number")
            qty = parse_qty(num_el.get_text()) if num_el else 1

        vendor_price, market_allowed = None, None
        footer = li.select_one(".db-tooltip__item_footer")
        if footer is not None:
            ftext = footer.get_text(" ", strip=True)
            m = re.search(r"Sells for\s*([\d,]+)\s*gil", ftext)
            sellable = "Unsellable" not in ftext
            vendor_price = (int(m.group(1).replace(",", ""))
                            if m and sellable else None)
            market_allowed = "Market Prohibited" not in ftext

        rows.append({"name": name.replace("\ue03c", "").strip(),
                     "quantity": qty or 1, "hq": bool(hq),
                     "listed_price": None, "vendor_price": vendor_price,
                     "market_allowed": market_allowed})
    return rows


def looks_like_listing_row(li):
    """True for a row in the retainer's "Sale Inventory" (active market
    listings) rather than its "Sale History" (completed sales).

    Both sections render as `ul.item-list--footer` full of
    `li.item-list__list`, so the container class can't tell them apart. The
    row shapes can:

      sale     -> sm(price) + md(buyer) + sm([data-epoch] sale time)
      listing  -> sm(unit price) + sm(quantity) + sm(total), no buyer, no
                  data-epoch (nothing has sold, so there's no timestamp),
                  and the item name only in the db-tooltip block.
    """
    if li.select_one("[data-epoch]"):
        return False
    sm_cells = li.select(".item-list__item.item-list__cell--sm")
    return (len(sm_cells) == 3
            and li.select_one(".item-list__item.item-list__cell--md") is None
            and li.select_one("h2.db-tooltip__item__name") is not None)


def parse_listing_rows(soup):
    """Retainer "Sale Inventory": the items currently listed on the market
    board, i.e. the occupied market slots.

    These were previously discarded. parse_sale_rows read every non-sale row
    on the page as "tooltip/UI contamination" - a hidden per-item detail
    popup - and counted it as dropped. That diagnosis was wrong, and wrong
    since the parser was first written on 2026-08-28: these are real
    listings whose name cell embeds the db-tooltip markup, which is why they
    look like a popup dump. The tell is arithmetic - the three `--sm` cells
    are unit price, quantity, and total, and the first times the second
    equals the third (125 x 12 = 1,500, 2,980 x 2 = 5,960, confirmed live
    2026-09-05, and the same shape is present in the 2026-08-28 fixture:
    1,000 x 4 = 4,000).

    The cost of the misdiagnosis was not just lost data: `market_listings`
    was never populated by anything, so `market_slots_occupied` was
    structurally 0 on every run. That fed `scale_min_gil`, which then
    treated a genuinely busy board as idle and scaled the sell/vendor floor
    all the way down to the nuisance floor.
    """
    rows = []
    for li in soup.select("li.item-list__list"):
        if li.has_attr("data-stack") or not looks_like_listing_row(li):
            continue
        name_el = li.select_one("h2.db-tooltip__item__name")
        raw_name = name_el.get_text(" ", strip=True)
        sm = li.select(".item-list__item.item-list__cell--sm")
        unit_price = parse_qty(sm[0].get_text())
        quantity = parse_qty(sm[1].get_text())
        total = parse_qty(sm[2].get_text())
        rows.append({
            "name": raw_name.replace("", "").strip(),
            "hq": "" in raw_name,
            "unit_price": unit_price,
            "quantity": quantity,
            "total": total,
            # A row whose price x quantity doesn't reconcile means the cell
            # order changed under us; surfaced rather than silently trusted.
            "total_reconciles": bool(unit_price and quantity and total
                                     and unit_price * quantity == total),
        })
    return rows


def parse_sale_rows(soup):
    """Retainer "Sale History" (the "" subpage): recent COMPLETED sales -
    name, price, buyer, sale time. These items are already gone; never feed
    this into cleanup verdicts, it's informational only.

    A real sale row carries a numeric `data-epoch` and a buyer cell
    (`item-list__cell--md`). Rows from the "Sale Inventory" section on the
    same page - the active listings - fail both checks and are skipped here
    without being counted as dropped; they belong to parse_listing_rows, not
    to this parser. Anything else that fails is genuinely unexpected and is
    dropped and counted, so silent data loss stays visible to the caller."""
    rows, dropped = [], 0
    for li in soup.select("li.item-list__list"):
        if li.has_attr("data-stack"):
            continue
        if looks_like_listing_row(li):
            continue
        name_el = li.select_one(".item-list__name")
        buyer_el = li.select_one(".item-list__item.item-list__cell--md")
        sm_cells = li.select(".item-list__item.item-list__cell--sm")
        epoch_el = li.select_one("[data-epoch]")
        if name_el is None:
            continue
        if (buyer_el is None or not sm_cells or epoch_el is None or
                not epoch_el.get("data-epoch", "").isdigit()):
            dropped += 1
            continue
        raw_name = name_el.get_text(" ", strip=True)
        m = re.match(r"^(.*?)\((\d+)\)$", raw_name)
        name, qty = (m.group(1), int(m.group(2))) if m else (raw_name, 1)
        hq = "\ue03c" in name
        # The price cell is the TOTAL gil for the sale, not the per-unit
        # price, despite reading like one. Confirmed live 2026-09-03: Alumen
        # quantity 92 recorded at 12,236 (= 133/unit, consistent with a
        # Universalis median of 189 and a routine undercut), Ash Log quantity
        # 99 at 8,935 (= 90/unit). Reading 12,236 as Alumen's unit price is
        # nonsense, and it was making calibrate_against_sales report ~-96%
        # residuals on every stack sale while only quantity-1 rows looked
        # sane. Both are kept: the total is what the retainer banked, the
        # unit price is what the market actually cleared at.
        total = parse_qty(sm_cells[0].get_text())
        unit = round(total / qty) if total and qty else total
        buyer = buyer_el.get_text(strip=True)
        epoch = int(epoch_el["data-epoch"])
        rows.append({"name": name.replace("\ue03c", "").strip(),
                     "quantity": qty, "hq": bool(hq), "sale_total": total,
                     "unit_price": unit, "buyer": buyer, "sold_epoch": epoch})
    return rows, dropped


def parse_venture(soup):
    """Venture name + completion status off the "venture/" subpage. Each
    field sits in a <p class="parts__text"> right after its <h4> label -
    when idle (no venture dispatched) that label pair isn't there at all."""
    def field_after(label):
        h4 = soup.find("h4", string=lambda s: s and s.strip() == label)
        p = h4.find_next_sibling("p") if h4 else None
        return p.get_text(" ", strip=True) if p else None

    name = field_after("Ventures")
    if not name:
        return None
    name = re.sub(r"^Lv\.\s*\d+\s*", "", name).strip()
    completion = field_after("Completion Date")
    epoch = None
    if completion:
        scr = soup.find("h4", string=lambda s: s and s.strip() ==
                         "Completion Date")
        scr = scr.find_next("script") if scr else None
        if scr and scr.string:
            m = re.search(r"ldst_strftime\((\d+)", scr.string)
            epoch = int(m.group(1)) if m else None
    return {"name": name, "status": completion, "completion_epoch": epoch}


def scrape_retainer(char_id, rid, session, dump_dir=None, verbose=False):
    out = {"retainer_id": rid, "name": None, "job": None, "level": None,
           # Null by design: retainer gear/ilvl does not exist outside the game
           # client. The gap should read "not available", not "missing".
           "item_level": None, "active_venture": None,
           "inventory": [], "market_listings": [], "recent_sales": [],
           "sale_rows_dropped": 0,
           "pages_ok": [], "pages_missing": []}
    seen_inv, seen_sale = set(), set()
    for sub in RETAINER_SUBPAGES:
        url = f"{BASE}/{char_id}/retainer/{rid}/{sub}"
        soup, html, status = fetch(url, session, dump_dir,
                                   f"retainer_{rid}_{sub or 'root'}", soft=True)
        if verbose:
            print(f"    {url} -> {status}", file=sys.stderr)
        if status != 200:
            out["pages_missing"].append(sub or "root")
            continue
        out["pages_ok"].append(sub or "root")

        if sub == "":
            name_el = soup.select_one(".retainer__data--name")
            if name_el:
                out["name"] = out["name"] or name_el.get_text(strip=True)
            m = re.search(r"(?:Lv\.?|LEVEL)\s*(\d{1,2})\b", html)
            if m:
                out["level"] = int(m.group(1))
            # The job icon carries no alt/title text on the Lodestone - it's
            # image-only, so the job name genuinely isn't recoverable here.
            sale_rows, dropped = parse_sale_rows(soup)
            out["sale_rows_dropped"] += dropped
            for r in sale_rows:
                key = (r["name"], r["hq"], r["quantity"], r.get("sold_epoch"))
                if key not in seen_sale:
                    seen_sale.add(key)
                    out["recent_sales"].append(r)
            # Active market listings live on this same page, in a second
            # section ("Sale Inventory"). Not deduped: two separate listings
            # of the same item at the same price and quantity are two
            # genuinely distinct occupied slots, and slot count is the whole
            # point of collecting these.
            out["market_listings"].extend(parse_listing_rows(soup))
        elif sub == "baggage/":
            for r in parse_baggage_rows(soup):
                key = (r["name"], r["hq"], r["quantity"])
                if key not in seen_inv:
                    seen_inv.add(key)
                    out["inventory"].append(r)
        elif sub == "venture/":
            out["active_venture"] = parse_venture(soup)
        time.sleep(0.4)
    return out


# --------------------------------------------------------------------------- #
# item index + pricing
# --------------------------------------------------------------------------- #

def load_item_index(session, refresh=False, notes=None):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / "items.json"
    if refresh or not cache.exists():
        print("fetching item database (~10MB, cached after this run)...",
              file=sys.stderr)
        try:
            r = session.get(ITEMS_URL, timeout=180)
            r.raise_for_status()
            cache.write_text(r.text, encoding="utf-8")
        except Exception as e:
            # A refresh that cannot reach GitHub must not kill the run when a
            # usable cache is already on disk. Observed 2026-09-16: a
            # transient "Connection refused" to raw.githubusercontent.com
            # aborted the entire scrape before a single page was fetched,
            # with a perfectly good 9.7MB cache sitting right there. The
            # refresh is an optimisation - the only thing it buys is newly
            # named items - so degrade to the cache and say so loudly.
            if not cache.exists():
                raise
            msg = (f"item database refresh failed ({e.__class__.__name__}); "
                   f"continuing with the cached copy from "
                   f"{datetime.fromtimestamp(cache.stat().st_mtime, tz=timezone.utc).strftime('%Y-%m-%d')} "
                   f"- a name added since then may not resolve")
            print(f"  ! {msg}", file=sys.stderr)
            if notes is not None:
                notes.append(msg)
    raw = json.loads(cache.read_text(encoding="utf-8"))
    by_name = {}
    for iid, names in raw.items():
        en = names.get("en") if isinstance(names, dict) else None
        if en:
            by_name.setdefault(en.strip().lower(), int(iid))
    return by_name


def fetch_vendor_buy_prices(ids, session, candidates=None, polite=0.15):
    """NPC *purchase* price (Item sheet PriceMid) for items an NPC actually
    sells, keyed by item id.

    PriceMid alone is not evidence of anything: every item carries the field
    whether or not a shop stocks it. Confirmed live 2026-09-03 - Fine Wax
    has PriceMid 279 and no GilShop entry at all, while its board price is
    ~14,000g, so treating PriceMid as a ceiling unconditionally would have
    written 98% off its value. Rroneek Glue, by contrast, is stocked
    (GilShopItem row 263203) at PriceMid 300,000 while the board asks
    400-500k, which is exactly the case worth catching.

    So membership in GilShopItem is the gate, and it is checked only for
    `candidates` - the handful of items whose market price actually exceeds
    PriceMid - because that check costs one request each. Everything else
    returns no ceiling, which leaves its valuation untouched.
    """
    out = {}
    ids = sorted(set(i for i in ids if i))
    if not ids:
        return out
    mids = {}
    for i in range(0, len(ids), 100):
        batch = ids[i:i + 100]
        url = (f"{XIVAPI}/sheet/Item?rows={','.join(str(b) for b in batch)}"
               f"&fields=PriceMid")
        try:
            r = session.get(url, timeout=60)
            r.raise_for_status()
            for row in r.json().get("rows", []):
                pm = (row.get("fields") or {}).get("PriceMid")
                if isinstance(pm, (int, float)) and pm > 0:
                    mids[int(row["row_id"])] = float(pm)
        except Exception as e:
            print(f"  ! vendor price batch failed ({e}); continuing",
                  file=sys.stderr)
        time.sleep(polite)
    check = [i for i in (candidates if candidates is not None else ids)
             if i in mids]
    for iid in check:
        url = (f"{XIVAPI}/search?sheets=GilShopItem&query=Item={iid}"
               f"&fields=Item&limit=1")
        try:
            r = session.get(url, timeout=60)
            r.raise_for_status()
            if r.json().get("results"):
                out[iid] = mids[iid]
        except Exception as e:
            print(f"  ! vendor shop lookup failed for {iid} ({e}); "
                  f"treating as not vendor-sold", file=sys.stderr)
        time.sleep(polite)
    return out


def fetch_marketable(session):
    try:
        r = session.get(f"{UNIVERSALIS}/marketable", timeout=60)
        r.raise_for_status()
        items = r.json()
        # An empty or malformed global catalog is an outage, not proof
        # that every inventory item is prohibited from the market.
        if (not isinstance(items, list) or not items
                or any(type(i) is not int or i <= 0 for i in items)):
            raise ValueError("expected a non-empty list of positive item IDs")
        return set(items)
    except Exception as e:
        print(f"  ! marketable list unavailable ({e})", file=sys.stderr)
        return None


def fetch_prices(ids, scope, session, chunk=50, listings=50, entries=50,
                 attempts=3, retry_single_items=None, notes=None):
    # Batches of 100 reliably 504 under current Universalis load; 50 comes
    # back in a few seconds *for a single-world scope*. A DC/cross-world
    # scope aggregates every world in it and is measurably heavier. The
    # failure is a *server-side ~10s gateway timeout*, not client-side and
    # not really load: measured 2026-09-09 against "a data center", batches that
    # exceed it 504 with a 16-byte "error code: 504" body after ~10.2s,
    # while batches that finish come back in 2-5s. Chunk size is therefore
    # the lever, and it is a sharp one - over 10 trials each on cold ids:
    #
    #     chunk=10   2/5 succeeded
    #     chunk=5    3/5
    #     chunk=4   10/10   ~4.5s/request
    #     chunk=3    9/10   ~3.5s/request
    #
    # Two DC passes at chunk=10 (09-09 05:24Z and 10:20Z) resolved 30/245
    # and 7/245 items, leaving little DC comparison data. Hence chunk=4
    # for DC callers. The `fields` parameter does NOT help - it trims the
    # response but not the work behind it, and fields-limited batches 504
    # at the same rate. The lighter /api/v2/aggregated/ endpoint answers in
    # ~1s but carries no recentHistory or listings array, so it would strip
    # history_median (the preferred price source) and cheapest_current_ask
    # (the undercut logic) off every DC row and fall back to minPrice,
    # which this pipeline deliberately distrusts - a reliability win paid
    # for in price quality, which is the wrong trade here.
    #
    # Expect the odd gap regardless; num()/pick_unit_price() already treat
    # missing data as "no data" rather than "zero", so a partial DC fetch
    # degrades to "no DC comparison for this item" rather than a wrong price.
    #
    # listings/entries=5 (the pre-fix default) is not enough to compute
    # anything robust: on a thin market the single cheapest *current*
    # listing can be 10-20x what the item has actually sold for recently
    # (confirmed live, 2026-08-28 - see verdict_for). 50 was measured at
    # ~9.5s/batch for a single-world scope, well inside the timeout below.
    out = {}
    ids = sorted(set(i for i in ids if i))
    absent = set()          # Single-item 404s: no record in this scope.

    def note(message):
        print(f"  ! {message}", file=sys.stderr)
        if notes is not None:
            notes.append(message)

    def fetch_batch(batch, tries):
        """Fetch one batch into `out`. Returns True if it landed."""
        url = (f"{UNIVERSALIS}/{scope}/{','.join(str(b) for b in batch)}"
               f"?listings={listings}&entries={entries}")
        for attempt in range(1, tries + 1):
            try:
                r = session.get(url, timeout=90)
                # A batch 404 cannot establish absence for every member.
                # Neither kind of 404 proves the item is untradeable.
                if r.status_code == 404:
                    if len(batch) == 1:
                        absent.update(batch)
                    return False
                r.raise_for_status()
                data = r.json()
                if not isinstance(data, dict):
                    raise ValueError("expected a pricing object")
                items = data.get("items")
                if not isinstance(items, dict):
                    items = {str(data["itemID"]): data} if data.get("itemID") else {}
                # Missing/malformed entries remain eligible for an approved
                # retry; only requested IDs with usable object shapes count.
                parsed = {iid: items[str(iid)] for iid in batch
                          if isinstance(items.get(str(iid)), dict)
                          and items[str(iid)]}
            except Exception as e:
                if attempt == tries:
                    print(f"  ! pricing batch failed ({e}); continuing",
                          file=sys.stderr)
                    return False
                time.sleep(1.5 * attempt)
                continue
            out.update(parsed)
            return True
        return False

    for i in range(0, len(ids), chunk):
        if not fetch_batch(ids[i:i + chunk], attempts):
            time.sleep(1.0)
        time.sleep(0.3)

    # A slow item can time out its neighbours. Single-item requests can
    # recover them, but potentially add many requests: ask before that work.
    missing = [i for i in ids if i not in out and i not in absent]
    if missing and chunk > 1:
        approved = retry_single_items
        if approved is None and sys.stdin.isatty():
            print(f"{scope}: {len(missing)}/{len(ids)} item(s) have no pricing. "
                  "Retry missing prices in batches of 1? [y/N] ",
                  end="", file=sys.stderr, flush=True)
            try:
                approved = input().strip().lower() in ("y", "yes")
            except EOFError:
                approved = False
        if approved:
            print(f"  retrying {len(missing)} unpriced item(s) in {scope}, "
                  "batch size 1...",
                  file=sys.stderr)
            for iid in missing:
                fetch_batch([iid], attempts)
                time.sleep(0.2)
        elif approved is None:
            note(f"{scope}: smaller-batch pricing retry not performed. "
                 "Ask the user whether to retry with batch size 1; after approval, "
                 "use --retry-pricing-single-items or --pricing-batch-size 1.")
        else:
            note(f"{scope}: smaller-batch pricing retry not approved; "
                 "available results retained.")

    still = [i for i in ids if i not in out and i not in absent]
    if still:
        note(f"{scope}: {len(still)}/{len(ids)} item(s) remain unpriced: "
             f"{still[:10]}{'...' if len(still) > 10 else ''}. "
             "Missing prices do not establish market prohibition or zero value.")
    return out


def num(d, *keys):
    for k in keys:
        v = (d or {}).get(k)
        if isinstance(v, (int, float)) and v > 0:
            return float(v)
    return None


def median(values):
    vals = sorted(v for v in values if isinstance(v, (int, float)) and v > 0)
    if not vals:
        return None
    n = len(vals)
    mid = n // 2
    return float(vals[mid]) if n % 2 else (vals[mid - 1] + vals[mid]) / 2.0


def history_median(entry, hq):
    """Median pricePerUnit of completed sales matching this row's HQ flag.
    This is the strongest signal Universalis returns: it's what the item
    actually sold for, not what someone is currently asking for it."""
    hist = (entry or {}).get("recentHistory") or []
    matched = [h.get("pricePerUnit") for h in hist if h.get("hq") == hq]
    return median(matched), len(matched)


def pick_unit_price(entry, hq):
    """Valuation waterfall, most-trustworthy first:
      1. median of realised sales (recentHistory) matching HQ/NQ
      2. averagePrice{HQ,NQ} - itself history-derived on Universalis' side
      3. currentAveragePrice{HQ,NQ} - derived from current listings, so it
         inherits whatever garbage is sitting on the board (confirmed live:
         Copper Ore's currentAveragePrice was ~1.2M because of one troll
         listing far outside the 50-listing window this script even fetches)
      4. minPrice{HQ,NQ} - the single cheapest current ask; on a thin market
         this is whatever one seller happens to be charging today, and can
         run 5-20x the item's actual clearing price (confirmed live for
         Raptor Skin, Hard Leather, Helmet Crab - see diagnosis notes)
    Returns (price, source, hist_n, listings_n) or (None, None, 0, 0).
    """
    hist_price, hist_n = history_median(entry, hq)
    listings_n = len([l for l in (entry or {}).get("listings") or []
                      if l.get("hq") == hq]) or (entry or {}).get(
                          "listingsCount") or 0
    if hist_price:
        return hist_price, "history_median", hist_n, listings_n
    suffix = "HQ" if hq else "NQ"
    avg = num(entry, f"averagePrice{suffix}")
    if avg:
        return avg, "average_price", hist_n, listings_n
    cur_avg = num(entry, f"currentAveragePrice{suffix}")
    if cur_avg:
        return cur_avg, "current_average_price", hist_n, listings_n
    min_p = num(entry, f"minPrice{suffix}")
    if min_p:
        return min_p, "min_price", hist_n, listings_n
    # Nothing HQ/NQ-specific at all (e.g. an item that only ever trades one
    # quality) - fall back to the undifferentiated fields rather than give up.
    generic = num(entry, "averagePrice", "currentAveragePrice", "minPrice")
    if generic:
        return generic, "generic_fallback", hist_n, listings_n
    return None, None, hist_n, listings_n


def cheapest_current_ask(entry, hq):
    """Lowest current asking price per unit for this quality, from the
    listings window. This is what you have to get under to be the seller who
    actually moves, so it caps what a realistic sale nets - the history
    median can sit well above the current board on a market that has since
    been undercut."""
    listings = [l.get("pricePerUnit") for l in (entry or {}).get("listings") or []
                if l.get("hq") == hq and isinstance(l.get("pricePerUnit"), (int, float))
                and l.get("pricePerUnit") > 0]
    if listings:
        return float(min(listings))
    return num(entry, "minPriceHQ" if hq else "minPriceNQ")


def effective_sale_price(entry, hq, hist_price, vendor_buy_price=None):
    """What a unit realistically nets, as opposed to what the item is
    nominally 'worth'.

    Two corrections on top of the realised-sales median:

    1. Undercutting. To be the listing that sells you go under the cheapest
       current ask, so the achievable price is bounded by that ask (times
       UNDERCUT_FACTOR), not by what the item historically cleared at.
    2. The vendor ceiling - flagged, not applied. A GilShopItem entry proves
       *an* NPC sells the item at that price, not that every buyer can reach
       that NPC. Confirmed wrong live 2026-09-04: Rroneek Glue is sold by
       Goplu in Tuliyollal at 300,000g, gated behind the quest "Forging the
       Phantasmal" (level 100, prior quest "Arcane Artistry", part of the
       Dawntrail Phantom Weapon chain) - not something every buyer on the
       board has cleared. Actual sales cleared at 400-500k across every DC,
       consistent with most buyers having no access to the cheap vendor.
       Silently capping the price at vendor cost was true "if everyone can
       buy from the vendor," which is not a safe assumption for a
       quest-gated shop and isn't checkable cheaply per item, so this is
       now a flag for the seller to weigh, not an automatic price override.

    Returns (price, [notes]) so callers can explain a haircut rather than
    silently reporting a different number than the market shows.
    """
    notes = []
    price = hist_price
    ask = cheapest_current_ask(entry, hq)
    if ask and price and ask * UNDERCUT_FACTOR < price:
        price = ask * UNDERCUT_FACTOR
        notes.append(f"undercut to {price:,.0f} (board at {ask:,.0f})")
    elif ask and not price:
        price = ask * UNDERCUT_FACTOR
        notes.append(f"undercut to {price:,.0f} (no sale history)")
    if vendor_buy_price and price and price > vendor_buy_price * VENDOR_CEILING_MULTIPLIER:
        notes.append(f"NOTE: an NPC sells this for {vendor_buy_price:,.0f} - "
                     f"verify that vendor isn't quest/level-gated before "
                     f"assuming buyers have a cheaper option")
    return price, notes


def price_dispersion_suspect(world_entry, dc_entry, hq, chosen):
    """Flag a local price that a wider sample disagrees with sharply.

    A single world's history is a small sample and can be dominated by a
    handful of atypical sales; the DC aggregate is the cheapest available
    second opinion. Disagreement of more than 3x in either direction means
    the local number is carrying the estimate on its own and deserves a look
    before it drives a decision.

    Only worth asking above DISPERSION_MIN_UNIT_PRICE. Below it a 3x gap is
    both routine and meaningless - the first run with this check flagged 68
    rows, nearly all of them bait and low-level fish priced at 2-40g, where
    "local 5g vs DC 20g" is rounding, not a signal, and the whole stack is
    worth less than the time spent verifying it."""
    if not chosen or chosen < DISPERSION_MIN_UNIT_PRICE:
        return False
    dc_med, dc_n = history_median(dc_entry, hq)
    if not dc_med or dc_n < 5:
        return False
    return chosen > dc_med * 3 or chosen < dc_med / 3


def price_confidence(source, hist_n, listings_n):
    if source == "history_median" and hist_n >= 5:
        return "high"
    if source == "history_median" and hist_n >= 1:
        return "medium"
    if source in ("average_price", "current_average_price") and listings_n >= 3:
        return "medium"
    return "low"


def is_price_suspect(chosen_price, source, hist_median_price, hist_n, listings_n):
    """Flag a price worth eyeballing on the board before trusting it: it
    disagrees sharply with realised sales, or it rests on a single current
    listing with no sale history to check it against at all."""
    if hist_median_price and chosen_price:
        if chosen_price > hist_median_price * 2 or chosen_price < hist_median_price * 0.4:
            return True
    if source in ("min_price", "current_average_price", "generic_fallback") \
            and hist_n == 0 and listings_n <= 1:
        return True
    return False


def pick_velocity(entry, hq):
    """Units sold per WEEK.

    Universalis reports saleVelocity as units sold per *day* - specifically
    (units sold in the trailing 7 days) / 7. Verified live 2026-09-03 against
    Example: Fine Wax velocity 2.857143 with 20 units sold in 7 days,
    Rroneek Glue 0.14285715 with 1 unit, Alumen 1806.57 with 12,646 units -
    every value is exactly units7/7. This function converts to per-week,
    which is the unit every caller downstream actually wants (weeks_to_clear,
    DEPTH_HORIZON_WEEKS absorption). Reading the raw field as weekly - the
    prior behaviour - understated throughput by 7x and pushed genuinely
    liquid items into sell_slow and vendor_or_discard."""
    suffix = "hqSaleVelocity" if hq else "nqSaleVelocity"
    per_day = num(entry, suffix) or num(entry, "regularSaleVelocity") or 0.0
    return per_day * 7.0


def verdict_for(row, world_px, dc_px, marketable, min_gil, world, dc,
                vendor_buy=None):
    """Conservative by design: a wrong 'keep' costs a slot, a wrong 'discard'
    costs an item you cannot get back.

    vendor_price/market_allowed come straight from the item's own Lodestone
    tooltip (real, scraped data - not a guess), so they're used even when
    Universalis has nothing: a stack that can't be listed, or has no
    listings/history, still often has real vendor gil sitting in it.

    Returns a dict merged onto the row (verdict, reason, est_value plus the
    optimistic/realistic/confidence detail described in the pricing
    diagnosis), not a bare tuple - there's too much to carry as one now."""
    iid, qty, hq = row.get("item_id"), row.get("quantity") or 1, bool(row.get("hq"))
    vendor_price = row.get("vendor_price")
    vendor_total = vendor_price * qty if vendor_price else None
    base = {"est_value_optimistic": None, "est_value_realistic": None,
            "price_source": None, "price_confidence": None,
            "price_suspect": False, "weeks_to_clear": None,
            "unit_price": None, "gil_per_slot_week": 0.0,
            "price_notes": None}

    def result(verdict, reason, est_value, **extra):
        out = dict(base)
        out.update(extra)
        return {"verdict": verdict, "reason": reason, "est_value": est_value,
                **out}

    if not iid:
        if vendor_total:
            return result("vendor_or_discard",
                          f"item name not resolved to an ID; vendor sale only "
                          f"~{vendor_total:,.0f}g", vendor_total,
                          est_value_optimistic=vendor_total,
                          est_value_realistic=vendor_total)
        return result("keep_unknown", "item name not resolved to an ID", None)

    market_blocked = (row.get("market_allowed") is False or
                      (marketable is not None and iid not in marketable))
    if market_blocked:
        if vendor_total:
            return result("vendor_or_discard",
                          f"market-prohibited; vendor sale only ~{vendor_total:,.0f}g",
                          vendor_total, est_value_optimistic=vendor_total,
                          est_value_realistic=vendor_total)
        # Untradeable AND no vendor price is NOT evidence an item is
        # worthless - it's the exact profile of a currency-like exchange
        # token or a rare unlock material, which typically can't be sold or
        # vendored precisely because it's valuable through some other
        # channel. Flagged live 2026-09-04: this path was labeling Ranger's/
        # Oracle's Soul Shard (Occult Crescent phantom-job unlock drops),
        # 11 stacks of Arcadion raid tokens (Light-heavy/Cruiser Holo-gear),
        # and Bozja-tier exchange materials (Demiatma, Prismaticluster,
        # Novacluster) all "safe to discard" - directly contradicting this
        # module's own fail-closed principle (see the module docstring: an
        # unresolved or untradable item is kept, never silently discarded).
        # The absence of both signals means the pricing pipeline has nothing
        # to say about the item, which is keep_unknown by definition, not a
        # verdict of zero value.
        return result("keep_unknown",
                      "untradeable with no vendor price - the pricing "
                      "pipeline has no signal here, not evidence it's "
                      "worthless (may be a rare drop or an exchange token)",
                      None)

    w, d = world_px.get(iid), dc_px.get(iid)
    if marketable is None and w is None and d is None and not vendor_total:
        return result("keep_unknown",
                      "pricing unavailable; market eligibility unknown", None)
    w_price, w_source, w_hist_n, w_list_n = pick_unit_price(w, hq)
    # A DC sample can supply a provisional asking price on the home World,
    # but cannot establish that World's sale proceeds or liquidity.
    if not w_price:
        d_price, d_source, _, _ = pick_unit_price(d, hq)
        if d_price:
            d_price, price_notes = effective_sale_price(
                d, hq, d_price, (vendor_buy or {}).get(iid))
            reference = dict(unit_price=round(d_price), price_source=d_source,
                             price_reference_scope=dc, price_confidence="low",
                             price_suspect=True, price_notes=price_notes or None)
            note_suffix = f" [{'; '.join(price_notes)}]" if price_notes else ""
            if vendor_total and vendor_price >= d_price:
                return result(
                    "vendor_or_discard",
                    f"vendor sale ~{vendor_total:,.0f}g ({vendor_price:,.0f}/unit) "
                    f"meets or beats the non-home-World reference of "
                    f"~{d_price:,.0f}g/unit from {dc}; home-World pricing "
                    f"unavailable for {world}. Check its board before selling; "
                    "this estimate is vendor proceeds only" + note_suffix,
                    vendor_total, est_value_optimistic=vendor_total,
                    est_value_realistic=vendor_total, **reference)
            return result(
                "non_home_world_price",
                f"non-home-World price: ~{d_price:,.0f}g/unit from {dc} (data center); "
                f"home-World pricing unavailable for {world}. May be used as "
                f"a provisional starting listing price on {world}; check its "
                "board when possible. Home-World proceeds and sale speed "
                "are unestimated" + note_suffix,
                None, **reference)
        if vendor_total:
            return result(
                "vendor_or_discard",
                f"market pricing unavailable; known vendor sale "
                f"~{vendor_total:,.0f}g. Check {world}'s market board before "
                "selling; missing prices do not mean the item is worthless",
                vendor_total, est_value_optimistic=vendor_total,
                est_value_realistic=vendor_total)
        return result("keep_unknown",
                      f"home-World pricing unavailable for {world}; no usable "
                      "non-home-World reference price. Check its market board "
                      "before selling or discarding", None)

    velocity = pick_velocity(w, hq)
    best, where, source, hist_n, list_n = w_price, world, w_source, w_hist_n, w_list_n
    chosen_entry = w
    hist_median_price, _ = history_median(chosen_entry, hq)
    confidence = price_confidence(source, hist_n, list_n)
    suspect = is_price_suspect(best, source, hist_median_price, hist_n, list_n)

    # What the item nominally goes for is not what a sale nets: you have to
    # get under the current board, and no buyer beats an NPC's own price.
    ceiling = (vendor_buy or {}).get(iid)
    best, price_notes = effective_sale_price(chosen_entry, hq, best, ceiling)
    if any(n.startswith("NOTE:") for n in price_notes):
        suspect = True
    if not best:
        if vendor_total:
            return result("vendor_or_discard",
                          f"no achievable sale price; vendor sale only "
                          f"~{vendor_total:,.0f}g", vendor_total,
                          est_value_optimistic=vendor_total,
                          est_value_realistic=vendor_total)
        return result("vendor_or_discard", "no achievable sale price", None)
    if price_dispersion_suspect(w, d, hq, best):
        suspect = True
        price_notes.append("local price disagrees with DC sample >3x")

    optimistic = best * qty
    epsilon = 0.01
    weeks_to_clear = qty / max(velocity, epsilon)
    absorbed_qty = min(qty, velocity * DEPTH_HORIZON_WEEKS)
    realistic = best * absorbed_qty
    # Gil per market slot per week is the number that matters under a hard
    # 40-slot cap: a fat stack of something liquid beats a pricier item that
    # sits for a month. See build_report's listing plan.
    gil_per_slot_week = (realistic / DEPTH_HORIZON_WEEKS) if realistic else 0.0

    extra = dict(price_source=source, price_confidence=confidence,
                price_suspect=suspect, weeks_to_clear=round(weeks_to_clear, 1),
                est_value_optimistic=round(optimistic),
                unit_price=round(best),
                gil_per_slot_week=round(gil_per_slot_week),
                price_notes=price_notes or None)
    note_suffix = f" [{'; '.join(price_notes)}]" if price_notes else ""

    if realistic < min_gil:
        msg = (f"only ~{realistic:,.0f}g realistically over "
              f"{DEPTH_HORIZON_WEEKS} weeks (optimistic full-stack "
              f"~{optimistic:,.0f}g on {where})" + note_suffix)
        if vendor_total and vendor_total > realistic:
            msg += f" - vendor sale ~{vendor_total:,.0f}g is better"
            realistic = vendor_total
        return result("vendor_or_discard", msg, round(realistic),
                      est_value_realistic=round(realistic), **extra)
    # Vendoring beats listing whenever the NPC pays more than the market
    # realistically returns - and it is also instant, certain, and costs no
    # market slot, so it wins ties too. This check used to live only in the
    # `realistic < min_gil` branch above, which meant a stack that cleared
    # the floor was never compared against its own vendor value at all:
    # Allagan Silver Piece x11 was recommended for sale at 475/unit (5,225g)
    # against a 500/unit vendor price (5,500g), losing gil *and* burning a
    # slot to do it. vendor_price is scraped from the item's own tooltip, so
    # this is a comparison of two real numbers, not a heuristic.
    if vendor_total and vendor_total >= realistic:
        return result("vendor_or_discard",
                      f"vendor sale ~{vendor_total:,.0f}g "
                      f"({vendor_price:,.0f}/unit) beats the market's "
                      f"~{realistic:,.0f}g ({best:,.0f}/unit on {where})"
                      + note_suffix, vendor_total,
                      **{**extra, "est_value_realistic": vendor_total})
    # Only home-World velocity establishes local selling liquidity.
    if velocity < SLOW_VELOCITY_PER_WEEK:
        return result("sell_slow",
                      f"~{realistic:,.0f}g realistically (optimistic "
                      f"~{optimistic:,.0f}g) on {where} but barely moves "
                      f"({velocity:.2f}/week)" + note_suffix, round(realistic),
                      est_value_realistic=round(realistic), **extra)
    return result("sell",
                  f"~{realistic:,.0f}g realistically (optimistic "
                  f"~{optimistic:,.0f}g) on {where} "
                  f"({velocity:.2f}/week, ~{gil_per_slot_week:,.0f}g per slot "
                  f"per week)" + note_suffix,
                  round(realistic), est_value_realistic=round(realistic), **extra)


# Cosmic Exploration / general DoH-DoL leveling XP-boost consumables
# ("Commercial Engineering Manual" grants +150% synthesis XP for 18 hours,
# halved at level 70+; "Commercial Survival Manual" is the gathering
# equivalent - verify the current item description).
# Flagged live 2026-09-04: these must never be sold or vendored while any
# crafter/gatherer is still leveling, regardless of what the market model
# says they're worth, because they're cheap to buy now and expensive in
# lost leveling time to need later. Matched by substring so every variant
# (Revised/Squadron/Commercial/Company-issue) is covered, not just the one
# the player happens to own.
NEVER_DISCARD_SUBSTRINGS = ("engineering manual", "survival manual")


def is_never_discard(name):
    name = (name or "").lower()
    return any(s in name for s in NEVER_DISCARD_SUBSTRINGS)


def apply_never_discard_protection(rows):
    """Conservatively protect leveling manuals regardless of market price.

    Recognize legacy sell_on_dc verdicts only to remove them from sale advice.
    """
    n = 0
    for r in rows:
        if is_never_discard(r.get("name")) and r.get("verdict") in (
                "sell", "sell_on_dc", "sell_slow", "non_home_world_price",
                "vendor_or_discard"):
            r["reason"] = (f"protected: DoH/DoL leveling XP boost, never "
                          f"discard while leveling - {r['reason']}")
            r["verdict"] = "protected_leveling_item"
            n += 1
    return n


def load_protected_materials(path):
    """Raw-material closure of pending class-quest turn-ins, from
    scionbook_quest_mats.py's --check output file. Returns a lowercase name set,
    or None if the file doesn't exist - protection is opt-in, not a hard
    dependency of a normal run."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return None
    return {n.strip().lower() for n in data.get("protected_materials", [])}


def load_quest_mats_meta(path):
    """`tiers_covered` from scionbook_quest_mats.py's output, as {job: [levels]}.

    Separate from load_protected_materials so that function keeps returning a
    plain name set. Older quest_mats.json files predate this key; a missing
    or malformed one just means "coverage unknown," never an error."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, ValueError):
        return None
    covered = data.get("tiers_covered")
    return covered if isinstance(covered, dict) else None


def scale_min_gil(min_gil, occupied, slots_total):
    """The min_gil floor scaled down as market slots free up.

    A flat floor is right when slots are contested (a 940g item genuinely
    isn't worth bumping something better off a full board) and wrong when
    they're empty (there's no opportunity cost at all to listing it).
    Confirmed live 2026-09-04: with 0/40 occupied, 139 rows worth ~23,800g
    on the board were being discarded under the flat 1,000g floor for no
    reason. Scales linearly with occupancy, but never below
    MIN_GIL_NUISANCE_FLOOR - a first version that scaled all the way to 1g
    turned "sell" into 125 rows including 1-4g bait, which is technically
    positive value but not worth the real-world time to list."""
    if not slots_total:
        return min_gil
    free_fraction = 1 - occupied / slots_total
    return max(MIN_GIL_NUISANCE_FLOOR, round(min_gil * (1 - free_fraction)))


def quest_mats_status_note(protected, path, tiers_covered=None,
                          crafter_levels=None, protection=None):
    """A note explaining what the loaded protected-materials set does and
    doesn't mean, or None when it's unambiguous (real protections loaded).

    An empty set is not the same claim as "nothing needs protecting" - it's
    equally consistent with the next class-quest tier never having been
    added to quest_turnins.json. That ambiguity was
    silent until this note was added (flagged live 2026-09-04, right after
    the 35-50 tier's protections legitimately emptied out with the next
    tier not yet mapped) - callers were trusting an empty list as "all
    clear" with no way to tell it apart from "coverage lapsed."""
    if protection is not None and protection.get("version") == 2:
        gaps = protection.get("coverage_gaps", [])
        return "Quest-material coverage incomplete: " + "; ".join(gaps) if gaps else None
    if protected is None:
        return (f"{path} not found - quest-material protection skipped. "
               "Run scionbook_quest_mats.py to generate it (see "
               "README.md).")
    if not protected:
        return (f"{path} loaded but contains zero protected materials - "
               "this means no class-quest tier is currently tracked, NOT "
               "that nothing needs protecting. Verify whether "
               "quest_turnins.json needs the next tier "
               "added before trusting the sell list.")
    return outgrown_tier_note(tiers_covered, crafter_levels)


def outgrown_tier_note(tiers_covered, crafter_levels):
    """Warn when a crafter has levelled past every tier protection covers.

    A non-empty protected set proves coverage exists, not that it still
    applies. Once a crafter passes the highest tier in configured quest-turn-in tiers its
    remaining turn-ins are unprotected, and the set stays reassuringly
    non-empty because the other seven classes still populate it - so the
    empty-set warning above never fires. Checked per class, since the
    crafters do drift apart in level."""
    if not tiers_covered or not crafter_levels:
        return None
    outgrown = []
    for job, level in sorted(crafter_levels.items()):
        levels = tiers_covered.get(job)
        if not levels:
            outgrown.append(f"{job} (level {level}, no tier tracked)")
        elif level > max(levels):
            outgrown.append(f"{job} (level {level}, tracked through "
                           f"{max(levels)})")
    if not outgrown:
        return None
    return ("Quest-material protection has been outgrown by "
           f"{len(outgrown)} crafter(s): {', '.join(outgrown)}. Their "
           "remaining class-quest turn-ins are NOT protected - add the next "
           "tier to quest_turnins.json. The protected set "
           "is still non-empty because the other classes populate it, so the "
           "empty-set check above will not catch this.")


def apply_quest_material_protection(rows, protected):
    """Keep configured quest materials out of sell/vendor plans and totals.

    Recognize legacy sell_on_dc verdicts only to remove them from sale advice.
    """
    if not protected:
        return 0
    n = 0
    for r in rows:
        name = (r.get("name") or "").strip().lower()
        if name in protected and r.get("verdict") in (
                "sell", "sell_on_dc", "sell_slow", "non_home_world_price",
                "vendor_or_discard"):
            r["reason"] = (f"protected: saved crafting need - {r['reason']}")
            r["verdict"] = "protected_quest_material"
            n += 1
    return n


def calibrate_against_sales(retainers, world_px, by_name):
    """Ground-truth check: compare the estimator's current unit price for an
    item against what this character's own retainers actually sold it for
    recently. This is free, real evidence the estimator was previously
    ignoring entirely - a large residual means either the market moved
    since that sale, or the estimate is still off."""
    residuals = []
    for ret in retainers:
        for s in ret.get("recent_sales", []):
            iid = by_name.get((s.get("name") or "").strip().lower())
            realized = s.get("unit_price")
            if not iid or not realized:
                continue
            entry = world_px.get(iid)
            est_price, source, hist_n, list_n = pick_unit_price(
                entry, bool(s.get("hq")))
            if not est_price:
                continue
            residuals.append({
                "name": s["name"], "hq": bool(s.get("hq")),
                "quantity": s.get("quantity"),
                "sale_total": s.get("sale_total"),
                "realized_unit_price": realized,
                "estimated_unit_price": round(est_price),
                "price_source": source,
                "residual_pct": round((est_price - realized) / realized * 100, 1),
                "sold_epoch": s.get("sold_epoch"),
            })
    residuals.sort(key=lambda r: -abs(r["residual_pct"]))
    return residuals or None


def derive_still_not_available(data):
    """Generated from what THIS run actually returned, not a fixed list -
    a section that came back null/empty gets flagged so the consumer can
    tell 'you have none' from 'we didn't look', on top of the permanent
    structural gaps the Lodestone never exposes regardless of run."""
    gaps = list(STRUCTURAL_LIMITS)
    coll = data.get("collections")
    if coll is not None:
        for kind in ("mount", "minion"):
            names, count = coll.get(f"{kind}s"), coll.get(f"{kind}_count")
            if names is None and count is None:
                gaps.append(f"collections.{kind}s (returned null this run - "
                            "fetch failed, profile is private, or selectors "
                            "changed)")
            elif names is None:
                gaps.append(f"collections.{kind}s names (Lodestone now "
                            f"serves {kind} names via a per-item tooltip "
                            f"request, not the list page - only the count, "
                            f"{count}, is available without fetching each "
                            "one individually)")
    if data.get("achievements") is None:
        gaps.append("achievements (skipped with --fast, or fetch failed "
                    "this run)")
    if not data.get("currencies"):
        gaps.append("currencies (returned null/empty this run)")
    quests = data.get("quests") or {}
    if not quests.get("recent") and not quests.get("note"):
        gaps.append("quest history (parsed empty this run, no error reported "
                    "- rerun with --dump and check)")
    if not data.get("retainers"):
        gaps.append("retainer data (none scraped this run)")
    return gaps


def consolidation_lines(data):
    """Same item scattered across retainers, listings and inventory.

    Three distinct wastes, in descending order of how much they cost:

    1. A stack split across retainers can change its own verdict. The
       depth cap and the min-gil floor are applied per row, so 1 of an item
       on one retainer and 10 on the other can price the small row under the
       floor and bucket it `vendor_or_discard` while the large row sells -
       the item is not marginal, the split just made one half look that way.
    2. Several listings of one item on one retainer burn a slot each for no
       extra throughput; merging them frees slots outright.
    3. Stock sitting unlisted on the retainer that is *not* the one already
       listing that item cannot sell through the existing slot at all.
    """
    lines, notes = [], []

    inv = {}
    for r in data.get("all_rows", []):
        inv.setdefault((r["name"], bool(r.get("hq"))), []).append(r)

    split = {k: v for k, v in inv.items()
             if len({r.get("retainer") for r in v}) > 1}
    verdict_split = {k: v for k, v in split.items()
                     if len({r["verdict"] for r in v}) > 1}

    listings = {}
    for ret in data.get("retainers") or []:
        for l in ret.get("market_listings") or []:
            listings.setdefault((l.get("name"), bool(l.get("hq"))),
                                []).append((ret.get("name"), l))

    dupes = {k: v for k, v in listings.items()
             if len({r for r, _ in v}) < len(v)}
    stranded = {k: v for k, v in listings.items()
                if k in inv and any(r.get("retainer") not in {w for w, _ in v}
                                    for r in inv[k])}

    if not (split or dupes or stranded):
        return []

    total_slots = sum(len(v) - 1 for v in dupes.values())
    lines += ["## Consolidate first", "",
              "Same item in more than one place. Worth doing before the "
              "listing plan below, because it changes what is worth listing.",
              ""]

    if verdict_split:
        lines += ["**Split stacks whose verdicts disagree** - the item is not "
                  "marginal, the split made one half look that way. Merge, "
                  "then re-run:", ""]
        for (name, hq), rows in sorted(
                verdict_split.items(),
                key=lambda kv: -sum(r.get("quantity") or 0 for r in kv[1])):
            tot = sum(r.get("quantity") or 0 for r in rows)
            where = ", ".join(f"{r.get('retainer')} x{r.get('quantity')} "
                              f"[{r['verdict']}]" for r in rows)
            lines.append(f"- **{name}**{' (HQ)' if hq else ''} - {tot} total: "
                         f"{where}")
        lines.append("")

    plain = {k: v for k, v in split.items() if k not in verdict_split}
    if plain:
        lines += ["**Split across retainers** (same verdict on each, "
                  "so this is tidying rather than a missed sale):", ""]
        for (name, hq), rows in sorted(
                plain.items(),
                key=lambda kv: -sum(r.get("quantity") or 0 for r in kv[1])):
            tot = sum(r.get("quantity") or 0 for r in rows)
            lines.append(f"- {name}{' (HQ)' if hq else ''} - {tot} total: "
                         + ", ".join(f"{r.get('retainer')} x{r.get('quantity')}"
                                     for r in rows))
        lines.append("")

    if dupes:
        lines += [f"**Duplicate listings** - one slot each, no extra "
                  f"throughput. Merging frees **{total_slots} slot(s)**:", ""]
        for (name, hq), v in dupes.items():
            per = {}
            for ret, l in v:
                per.setdefault(ret, []).append(l)
            for ret, ls in per.items():
                if len(ls) > 1:
                    prices = sorted({l.get("unit_price") for l in ls})
                    qty = [l.get("quantity") for l in ls]
                    lines.append(
                        f"- **{name}**{' (HQ)' if hq else ''} [{ret}] - "
                        f"{len(ls)} listings, qty {qty}, "
                        f"{'all at' if len(prices) == 1 else 'prices'} "
                        f"{', '.join(f'{p:,}g' for p in prices if p)} "
                        f"-> frees {len(ls) - 1}")
        lines.append("")

    if stranded:
        lines += ["**Listed on one retainer, stock stranded on the other** - "
                  "that stock cannot sell through the existing slot. Move it "
                  "to the retainer already listing it:", ""]
        for (name, hq), v in stranded.items():
            holders = {r for r, _ in v}
            for r in inv[(name, hq)]:
                if r.get("retainer") not in holders:
                    lines.append(
                        f"- **{name}**{' (HQ)' if hq else ''} - listed on "
                        f"{', '.join(sorted(holders))}, "
                        f"x{r.get('quantity')} sitting on {r.get('retainer')}")
        lines.append("")

    return lines


def build_report(data):
    lines = ["# Retainer cleanup", "",
             f"Generated {data['fetched_at_utc']}", "",
             f"**Selling World: {data.get('world') or 'your home World'}**. "
             "Retainers sell only on the character's home World. Other "
             "World/DC prices are references for comparison, buying, or "
             "provisional home-World listing prices, never selling destinations.", ""]
    buckets = {}
    for r in data.get("all_rows", []):
        buckets.setdefault(r["verdict"], []).append(r)
    order = [("sell", "Sell on your world"),
             ("sell_slow", "Listable, but slow movers"),
             ("non_home_world_price", "Non-home-World price - provisional home-World listings"),
             ("vendor_or_discard", "Vendor or discard"),
             ("protected_quest_material",
              "Protected - feeds a pending class-quest turn-in"),
             ("protected_leveling_item",
              "Protected - DoH/DoL leveling XP boost, never discard"),
             ("keep_unknown", "Unresolved - check manually before touching")]
    summary = data.get("summary", {})
    total = summary.get("estimated_recoverable_gil") or 0
    optimistic = summary.get("estimated_recoverable_gil_optimistic") or 0
    lines += [f"**Estimated recoverable: ~{total:,.0f} gil** "
              f"(naive full-stack-at-best-price math would say "
              f"~{optimistic:,.0f} gil - see depth note below)", ""]

    if buckets.get("non_home_world_price"):
        lines += ["Non-home-World reference prices can be used as provisional "
                  "starting prices for home-World listings. These items are "
                  "excluded from the estimated proceeds and ranked listing "
                  "plan because local sale prices and demand are unknown.", ""]

    lines += consolidation_lines(data)

    slots_total = summary.get("market_slots_total") or 0
    occupied = summary.get("market_slots_occupied") or 0
    # Plan against slots you can actually fill, not the theoretical total.
    # These were the same number only while market_slots_occupied was stuck
    # at 0 (see parse_listing_rows); with real occupancy, planning
    # slots_total items tells you to list 40 things into 15 free slots.
    free_slots = max(0, slots_total - occupied)
    # Free slots are per-retainer, not one shared pool. Inventory can only
    # be listed from the board belonging to the retainer holding it.
    # Planning against the global free count alone silently over-assigns
    # whichever retainer holds the better stock - on 2026-09-08 it put 16
    # listings onto a retainer with 13 free slots while the global 24/24
    # still balanced, so nothing in the totals looked wrong.
    capacity = {ret.get("name"): max(0, MARKET_SLOTS_PER_RETAINER
                                     - len(ret.get("market_listings") or []))
                for ret in data.get("retainers") or []}
    if slots_total and free_slots:
        listable = [r for r in data.get("all_rows", [])
                   if r["verdict"] == "sell"]
        # Under a hard slot cap the objective is gil per slot per week, not
        # gil per item: a 99-stack of something that clears weekly out-earns
        # a pricier item that occupies a slot for a month. A few high-value
        # slow movers are still worth parking, so reserve a minority of slots
        # for them rather than letting throughput crowd them out entirely.
        slow_parks = max(1, free_slots // 8)
        fast = sorted((r for r in listable
                       if (r.get("weeks_to_clear") or 99) <= DEPTH_HORIZON_WEEKS),
                      key=lambda r: -(r.get("gil_per_slot_week") or 0))
        slow = sorted((r for r in listable
                       if (r.get("weeks_to_clear") or 99) > DEPTH_HORIZON_WEEKS),
                      key=lambda r: -(r.get("est_value") or 0))
        top, picked = [], set()

        def admit(cands, limit):
            """Take rows in the order given until `top` reaches `limit`,
            skipping any whose retainer has no free slot left."""
            for r in cands:
                if len(top) >= limit:
                    break
                if id(r) in picked:
                    continue
                who = r.get("retainer")
                if who in capacity:
                    if capacity[who] <= 0:
                        continue
                    capacity[who] -= 1
                top.append(r)
                picked.add(id(r))

        admit(fast, free_slots - slow_parks)
        admit(slow, len(top) + slow_parks)
        admit(fast + slow, free_slots)
        top = sorted(top, key=lambda r: -(r.get("gil_per_slot_week") or 0))
        plan_week = sum(r.get("gil_per_slot_week") or 0 for r in top)
        short = free_slots - len(top)
        lines += [f"## List right now ({len(top)} into {free_slots} free "
                 f"market slot(s))",
                 "", f"{occupied} of {slots_total} slots are already in use "
                 f"across {summary.get('retainers', 0)} retainer(s) "
                 f"({MARKET_SLOTS_PER_RETAINER}/retainer), leaving "
                 f"**{free_slots} free**. Ranked by gil per slot per week, "
                 f"since slots - not stock - are the binding constraint; up "
                 f"to {slow_parks} slot(s) held for high-value slow movers. "
                 f"This plan turns over roughly **{plan_week:,.0f}g/week** if "
                 f"it all clears at estimate."
                 + (f" {short} free slot(s) go unused: the stacks that would "
                    f"fill them sit on a retainer whose own board is already "
                    f"full, and a stack can only be listed from the retainer "
                    f"holding it." if short > 0 else ""),
                 ""]
        for r in top:
            hq = " (HQ)" if r.get("hq") else ""
            flag = " ⚠ verify price" if r.get("price_suspect") else ""
            lines.append(f"- **{r['name']}**{hq} x{r['quantity']} "
                         f"[{r['retainer']}] - {r['reason']}{flag}")
        lines.append("")
        queue = [r for r in listable if r not in top][:20]
        if queue:
            lines += ["### Refill queue (next up as slots free)", ""]
            for r in sorted(queue, key=lambda r: -(r.get("gil_per_slot_week") or 0)):
                lines.append(f"- {r['name']} x{r['quantity']} "
                             f"[{r['retainer']}] - "
                             f"~{r.get('gil_per_slot_week') or 0:,.0f}g/slot/week")
            lines.append("")
    elif slots_total:
        # Board full. Silence here would read as "nothing worth listing",
        # which is the opposite of the truth.
        listable = [r for r in data.get("all_rows", [])
                   if r["verdict"] == "sell"]
        best = sorted(listable,
                      key=lambda r: -(r.get("gil_per_slot_week") or 0))[:10]
        lines += [f"## Board is full ({occupied}/{slots_total} slots in use)",
                 "", "Nothing can be listed until something comes down. The "
                 f"{len(listable)} listable stack(s) still in storage are "
                 "waiting on a free slot - the best of them by gil per slot "
                 "per week, to compare against what's currently listed:", ""]
        for r in best:
            lines.append(f"- {r['name']} x{r['quantity']} [{r['retainer']}] - "
                         f"~{r.get('gil_per_slot_week') or 0:,.0f}g/slot/week")
        lines.append("")

    suspect = [r for r in data.get("all_rows", []) if r.get("price_suspect")]
    if suspect:
        lines += [f"## Verify these on the board before trusting them "
                 f"({len(suspect)})", "",
                 "The price uses a non-home-World reference, disagrees sharply "
                 "with realised sale history, or rests on a single current "
                 "listing with nothing to check it against.", ""]
        for r in sorted(suspect, key=lambda r: -(r.get("est_value") or 0)):
            hq = " (HQ)" if r.get("hq") else ""
            lines.append(f"- **{r['name']}**{hq} x{r['quantity']} "
                         f"[{r['retainer']}] - {r['reason']} "
                         f"(source: {r.get('price_source')})")
        lines.append("")

    for key, title in order:
        rows = sorted(buckets.get(key, []), key=lambda r: -(r["est_value"] or 0))
        if not rows:
            continue
        lines += [f"## {title} ({len(rows)})", ""]
        for r in rows[:200]:
            hq = " (HQ)" if r.get("hq") else ""
            flag = " ⚠" if r.get("price_suspect") else ""
            lines.append(f"- **{r['name']}**{hq} x{r['quantity']} "
                         f"[{r['retainer']}] - {r['reason']}{flag}")
        lines.append("")
    lines += ["---", "", "Slot count matters more than gil per item: a 200g "
              "stack and a 200,000g stack free the same space. Clear the "
              "bottom bucket first, then list the top.", ""]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #

def resolve_cookie(args):
    """Resolve credentials only after the requested refresh mode is known."""
    if args.mode == "public":
        if args.cookie is not None or args.cookie_env:
            sys.exit("Public mode conflicts with cookie options. Use --mode full "
                     "for an authenticated refresh, or remove the cookie option.")
        return None
    if args.cookie is not None:
        cookie = args.cookie.strip()
    elif args.cookie_env:
        cookie = os.environ.get("LODESTONE_COOKIE", "").strip()
    else:
        if not sys.stdin.isatty():
            sys.exit("Full mode requires a cookie. No TTY for hidden input; "
                     "use --cookie-env, or explicitly select --mode public.")
        print("Paste ldst_sess cookie value (input hidden; required for full mode)",
              file=sys.stderr)
        try:
            cookie = getpass.getpass("ldst_sess: ").strip()
        except EOFError:
            sys.exit("Cookie input ended. Full refresh cancelled; no files written.")
    if not cookie:
        sys.exit("Cookie is empty. Full refresh cancelled; no files written. "
                 "Provide credentials or explicitly select --mode public.")
    return cookie


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(CONFIG_PATH))
    ap.add_argument("--id")
    ap.add_argument("--world")
    ap.add_argument("--dc")
    credentials = ap.add_mutually_exclusive_group()
    credentials.add_argument("--cookie", help="NOTE: lands in shell history; --cookie-env is safer")
    credentials.add_argument("--cookie-env", action="store_true",
                             help="read cookie from $LODESTONE_COOKIE (full mode)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--mode", choices=("full", "public"),
                      help="override configured mode for this run; explicit identity defaults to full")
    mode.add_argument("--anon", dest="mode", action="store_const", const="public",
                      help="alias for --mode public")
    ap.add_argument("--out", metavar="FILE", default="status.json")
    ap.add_argument("--report", metavar="FILE",
                    help="also write the cleanup report as standalone markdown")
    ap.add_argument("--dump", metavar="DIR", help="save raw HTML for debugging")
    ap.add_argument("--probe", action="store_true",
                    help="verbose retainer URL probing")
    ap.add_argument("--compact", action="store_true")
    ap.add_argument("--fast", action="store_true",
                    help="skip achievements and collections")
    ap.add_argument("--no-retainers", action="store_true")
    ap.add_argument("--no-pricing", action="store_true")
    ap.add_argument("--pricing-batch-size", type=int, metavar="N",
                    help="items per request in both pricing scopes (default: World 50, DC 4)")
    ap.add_argument("--retry-pricing-single-items", action="store_true", default=None,
                    help="authorize one retry pass of missing prices with batch size 1")
    ap.add_argument("--min-gil", type=int, default=1000)
    ap.add_argument("--refresh-items", action="store_true")
    ap.add_argument("--quest-pages", type=int, default=1)
    ap.add_argument("--recent-quests", type=int, default=100)
    ap.add_argument("--recent", type=int, default=25)
    ap.add_argument("--max-pages", type=int, default=4)
    ap.add_argument("--quest-mats", metavar="FILE", default="quest_mats.json",
                    help="protected-materials file from scionbook_quest_mats.py "
                         "(--check's closure of pending class-quest turn-in "
                         "ingredients); skipped silently if missing")
    ap.add_argument("--quest-turnins", default="quest_turnins.json",
                    help="persistent version 2 crafting quest references and explicit keeps")
    ap.add_argument("--quest-mats-out", help="write reconciled protection here; reads cache from --quest-mats")
    ap.add_argument("--no-quest-mats", action="store_true",
                    help="don't apply quest-material protection even if "
                         "--quest-mats resolves to a real file")
    args = ap.parse_args()
    if args.pricing_batch_size is not None and args.pricing_batch_size < 1:
        ap.error("--pricing-batch-size must be at least 1")

    try:
        args.mode = resolve_mode(args.mode, args.config,
                                 explicit_identity=any((args.id, args.world, args.dc)))
        args.id, args.world, args.dc = resolve_identity(args.id, args.world, args.dc, args.config)
    except ValueError as exc:
        ap.error(str(exc))

    cookie = resolve_cookie(args)
    HEADERS.pop("Cookie", None)
    if cookie:
        HEADERS["Cookie"] = cookie if "=" in cookie else f"ldst_sess={cookie}"

    session = requests.Session()
    session.headers.update(HTTP_HEADERS)
    notes = []
    if not cookie:
        notes.append("Running anonymously: quests, currencies and retainers "
                     "unavailable, and public pages may be days stale.")
        print("WARNING: " + notes[-1], file=sys.stderr)

    data = {"character_id": args.id,
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "mode": args.mode, "lodestone_url": LODESTONE,
            "authenticated": bool(cookie), "world": args.world, "data_center": args.dc}

    # ---- profile ---------------------------------------------------------
    try:
        p_soup, p_html = fetch(f"{BASE}/{args.id}/", session, args.dump,
                               "profile")
    except FileNotFoundError:
        sys.exit(f"Character {args.id} not found (404).")
    except requests.RequestException as e:
        sys.exit(f"Network error: {e}")
    character = parse_profile(p_soup, p_html)
    if not character.get("name") or not character.get("world"):
        sys.exit("Profile could not be verified; refusing to write a snapshot.")
    location = re.fullmatch(r"\s*(.+?)\s*\[([^\]]+)\]\s*", character["world"])
    if not location:
        sys.exit("Profile home world/data center could not be verified.")
    actual_world, actual_dc = (part.strip() for part in location.groups())
    if (actual_world.casefold() != args.world.casefold()
            or actual_dc.casefold() != args.dc.casefold()):
        sys.exit("Profile home world/data center differs from configuration. Run $setup again.")

    # ---- jobs ------------------------------------------------------------
    try:
        c_soup, c_html = fetch(f"{BASE}/{args.id}/class_job/", session,
                               args.dump, "class_job")
        jobs = parse_class_job(c_soup, c_html)
    except (FileNotFoundError, requests.RequestException) as e:
        jobs = {}
        notes.append(f"class_job fetch failed: {e}")
    buckets = bucket(jobs)
    attribute_item_level(character, jobs, buckets)
    data["character"] = character
    data["jobs"] = buckets
    data["jobs_parsed"] = len(jobs)

    # ---- quests ----------------------------------------------------------
    if cookie:
        quests, q_total, q_pages, q_note = fetch_quests(
            args.id, session, args.dump, pages=args.quest_pages)
    else:
        quests, q_total, q_pages, q_note = [], None, None, "Private quest history unavailable in public mode."
    qout = {"total_completed": q_total, "history_pages": q_pages}
    if q_note:
        qout["note"] = q_note
        notes.append(q_note)
    qout["recent"] = quests[:args.recent_quests] if args.recent_quests else quests
    # No most_recent_msq field on purpose: the category label changes every
    # patch ("Dawntrail", "The New Dawn", "Winter's Prelude"), so any filter
    # here silently goes stale. Read the recent list instead.
    data["quests"] = qout

    # ---- currencies ------------------------------------------------------
    if cookie:
        cur, rep, active_seal, c_note = fetch_currency(args.id, session, args.dump)
    else:
        cur, rep, active_seal, c_note = None, None, None, "Private currencies unavailable in public mode."
    if c_note:
        notes.append(c_note)
    if cur is not None:
        cur, inferred_zero, gc_warning = reconcile_currencies(
            character, cur, active_seal)
        if inferred_zero:
            data["currencies_inferred_zero"] = inferred_zero
            notes.append("Backfilled as confirmed-zero (not scraped, not on "
                         f"the page - see currencies_inferred_zero): "
                         f"{', '.join(inferred_zero)}.")
        if gc_warning:
            data["character"]["grand_company_seal_mismatch"] = gc_warning
            notes.append(gc_warning)
            print("!!! " + gc_warning, file=sys.stderr)
    data["currencies"], data["reputation"] = cur, rep

    # ---- achievements + collections --------------------------------------
    if not args.fast:
        entries, points, note = fetch_achievements(
            args.id, session, args.dump, max_pages=args.max_pages)
        ach = {"total_points": points, "count_parsed": len(entries)}
        if note:
            ach["note"] = note
            notes.append(note)
        if entries and entries[0]["completed_utc"]:
            ach["most_recent_utc"] = entries[0]["completed_utc"]
        ach["recent"] = entries[:args.recent] if args.recent else entries
        data["achievements"] = ach

        mounts, m_ct = fetch_collection(args.id, session, "mount", args.dump)
        minions, n_ct = fetch_collection(args.id, session, "minion", args.dump)
        data["collections"] = {"mount_count": m_ct, "mounts": mounts,
                               "minion_count": n_ct, "minions": minions}

    # Reconcile persistent crafting data once using this run's levels/history.
    # Recipe lookups are limited to uncached items. Writes happen with outputs.
    quest_protection = None
    if not args.no_quest_mats and cookie:
        from crafting_protection import read_json, reconcile
        from scionbook_quest_mats import UnresolvedTurnIn
        try:
            plan = read_json(args.quest_turnins)
            if isinstance(plan, dict) and plan.get("version") == 2:
                quest_protection = reconcile(plan, data, read_json(args.quest_mats))
                data["crafting_protection"] = {
                    "reconciled": True,
                    **{k: quest_protection[k] for k in (
                        "source_fetched_at_utc", "coverage_gaps", "protected_materials",
                        "added_materials", "released_materials")}}
                notes.extend(quest_protection["coverage_gaps"])
        except (ValueError, OSError, requests.RequestException, UnresolvedTurnIn) as exc:
            notes.append(f"Crafting protection reconciliation failed: {exc}")
            data["crafting_protection"] = {"reconciled": False, "error": str(exc)}

    # ---- retainers + pricing ---------------------------------------------
    data["retainers"], data["all_rows"] = [], []
    world_px, calibration = {}, None
    if args.no_retainers:
        notes.append("Retainers skipped (--no-retainers).")
    elif not cookie:
        notes.append("Retainers skipped: authentication required.")
    else:
        print("locating retainer index...", file=sys.stderr)
        idx_url, r_soup, r_html = find_retainer_index(
            args.id, session, args.dump, verbose=args.probe)
        if not r_soup:
            notes.append("No retainer index responded. Cookie expired, or the "
                         "index path differs from all candidates. Re-run with "
                         "--probe --dump and check the status codes.")
        else:
            data["retainer_index_url"] = idx_url
            found = parse_retainer_list(r_soup, r_html)
            if not found:
                notes.append(f"Index at {idx_url} loaded but no retainer links "
                             "parsed - markup differs from the parser. Re-run "
                             "with --dump and inspect retainer_index.html.")
            for r in found:
                print(f"  scraping {r['name'] or r['retainer_id']}...",
                      file=sys.stderr)
                det = scrape_retainer(args.id, r["retainer_id"], session,
                                      args.dump, verbose=args.probe)
                det["name"] = r["name"] or det.get("name")
                data["retainers"].append(det)

        # Only current storage (inventory) is eligible for a verdict.
        # recent_sales are items already sold - nothing to clean up there.
        rows = []
        for ret in data["retainers"]:
            label = ret.get("name") or ret["retainer_id"][:8]
            for it in ret["inventory"]:
                rows.append({**it, "retainer": label})

        if rows:
            by_name = load_item_index(session, args.refresh_items, notes)
            for r in rows:
                r["item_id"] = by_name.get((r["name"] or "").strip().lower())

            if args.no_pricing:
                notes.append("Pricing skipped (--no-pricing).")
                for r in rows:
                    r.update(verdict="keep_unknown", reason="pricing skipped",
                             est_value=None)
            else:
                print("pricing against Universalis...", file=sys.stderr)
                # min_gil is a floor worth having when slots are contested -
                # with 40/40 full, a 940g item genuinely isn't worth bumping
                # something better. But it makes no sense as a flat constant
                # when slots sit empty: flagged live 2026-09-04 with 0/40
                # occupied, where 139 rows worth ~23,800g on the board (vendor
                # value only ~6,200g) were being discarded for no reason at
                # all - there was zero in-game opportunity cost to listing
                # them. Scale the floor down as free slots open up - but not
                # to zero: a first attempt that scaled all the way to 1g
                # turned "sell" into 125 rows including 1-4g bait (Helmet
                # Crab, Animal Sinew, Lightning Rock), which is technically
                # positive value but not worth the player's time to
                # list. MIN_GIL_NUISANCE_FLOOR is the floor under which
                # nothing is worth listing regardless of slot pressure;
                # min_gil itself is only approached as slots fill up.
                slots_total = len(data["retainers"]) * MARKET_SLOTS_PER_RETAINER
                occupied = sum(len(ret.get("market_listings") or [])
                              for ret in data["retainers"])
                effective_min_gil = scale_min_gil(args.min_gil, occupied,
                                                  slots_total)
                if effective_min_gil != args.min_gil:
                    notes.append(
                        f"min-gil floor scaled from {args.min_gil:,} to "
                        f"{effective_min_gil:,} - {occupied}/{slots_total} "
                        "market slots occupied, so idle capacity makes a "
                        "flat floor too strict (never scaled below "
                        f"{MIN_GIL_NUISANCE_FLOOR:,}g - not worth listing "
                        "regardless of slot pressure).")
                marketable = fetch_marketable(session)
                if marketable is None:
                    notes.append("Universalis marketable list unavailable; "
                                 "trying resolved IDs without a known market prohibition. Missing prices do "
                                 "not establish that an item is untradeable.")
                # Tooltip market flags and vendor sale values are already
                # available. Vendor-only items need no remote market pricing;
                # vendor-unsellable items may still be marketable. Preserve
                # unknown eligibility rather than interpreting it as blocked.
                pricing_ids = sorted({r["item_id"] for r in rows
                                      if r["item_id"]
                                      and r.get("market_allowed") is not False
                                      and (marketable is None or r["item_id"] in marketable)})
                world_px = fetch_prices(
                    pricing_ids, args.world, session,
                    chunk=args.pricing_batch_size or 50,
                    retry_single_items=args.retry_pricing_single_items, notes=notes)
                # DC scope aggregates every world in the DC and is much
                # more prone to 504s under load than a single-world query
                # at the same size (confirmed live, 2026-08-28) - smaller
                # chunks/params and more retries reduce but don't eliminate
                # that; a gap here just means no DC comparison for that
                # item, not a wrong price (see fetch_prices).
                # listings/entries=50 matches the world pass and costs
                # nothing measurable on the DC endpoint (chunk=4 averaged
                # 1.6s at 50 vs 2.1s at 20 on 2026-09-09) - the timeout is
                # driven by per-item aggregation, not response size. More
                # history means better medians, so take it.
                dc_px = fetch_prices(
                    pricing_ids, args.dc, session, chunk=args.pricing_batch_size or 4,
                    listings=50, entries=50, attempts=3,
                    retry_single_items=args.retry_pricing_single_items, notes=notes)
                if pricing_ids and len(dc_px) < 0.5 * len(pricing_ids):
                    notes.append(
                        f"DC pricing ({args.dc}) only resolved for "
                        f"{len(dc_px)}/{len(pricing_ids)} items this run, "
                        "likely Universalis load on the cross-world "
                        "endpoint - comparison data is incomplete; "
                        "home-World selling estimates are unaffected.")
                # Missing market data does not erase known vendor value.
                if pricing_ids and not world_px and not dc_px:
                    notes.append("Universalis returned no data for any item. "
                                 "Market estimates unavailable; only known vendor "
                                 "values are retained. Missing prices are not "
                                 "evidence to discard. Check connectivity and re-run.")
                    print(notes[-1], file=sys.stderr)
                    for r in rows:
                        r.update(verdict_for(r, {}, {}, marketable,
                                             effective_min_gil, args.world,
                                             args.dc))
                else:
                    # Check NPC availability for valuable home prices and DC
                    # references alike. Shop prices warn; they do not cap.
                    candidates = []
                    for r in rows:
                        iid = r.get("item_id")
                        if not iid:
                            continue
                        px, _, _, _ = pick_unit_price(world_px.get(iid),
                                                      bool(r.get("hq")))
                        if not px:
                            px, _, _, _ = pick_unit_price(dc_px.get(iid),
                                                         bool(r.get("hq")))
                        if px and px > 1000:
                            candidates.append(iid)
                    print("checking NPC vendor ceilings...", file=sys.stderr)
                    vendor_buy = fetch_vendor_buy_prices(
                        pricing_ids, session, candidates=candidates)
                    for r in rows:
                        r.update(verdict_for(r, world_px, dc_px, marketable,
                                             effective_min_gil, args.world,
                                             args.dc, vendor_buy=vendor_buy))
                    calibration = calibrate_against_sales(
                        data["retainers"], world_px, by_name)
        if not args.no_quest_mats:
            protected = ({n.strip().lower() for n in quest_protection["protected_materials"]}
                         if quest_protection is not None else load_protected_materials(args.quest_mats))
            protected_count = apply_quest_material_protection(rows, protected)
            status_note = quest_mats_status_note(
                protected, args.quest_mats,
                tiers_covered=load_quest_mats_meta(args.quest_mats),
                crafter_levels=(data.get("jobs") or {}).get("crafters"),
                protection=quest_protection)
            if status_note:
                notes.append(status_note)
            elif protected_count:
                print(f"protected {protected_count} row(s) feeding a "
                     "pending class-quest turn-in", file=sys.stderr)
        never_discard_count = apply_never_discard_protection(rows)
        if never_discard_count:
            print(f"protected {never_discard_count} leveling XP-boost "
                 "item(s) (Engineering/Survival Manuals)", file=sys.stderr)
        data["all_rows"] = rows

        sale_rows_dropped = sum(ret.get("sale_rows_dropped") or 0
                                for ret in data["retainers"])
        if sale_rows_dropped:
            notes.append(f"Dropped {sale_rows_dropped} unrecognised row(s) "
                         "from recent_sales - rows with neither a buyer cell "
                         "nor a data-epoch timestamp, and not the shape of a "
                         "market listing either. Active listings are no "
                         "longer counted here (see parse_listing_rows), so a "
                         "nonzero count now means the sale-history markup "
                         "genuinely changed - worth a --dump.")
        unreconciled = [l for ret in data["retainers"]
                        for l in (ret.get("market_listings") or [])
                        if not l.get("total_reconciles")]
        if unreconciled:
            notes.append(
                f"{len(unreconciled)} market listing(s) where unit price x "
                "quantity != total, so the Sale Inventory cell order may "
                "have changed - market_slots_occupied may be wrong.")

    sellable_tags = ("sell", "sell_slow")
    optimistic_total = round(sum(r.get("est_value_optimistic") or 0
                                 for r in data["all_rows"]
                                 if r.get("verdict") in sellable_tags))
    realistic_total = round(sum(r.get("est_value") or 0
                                for r in data["all_rows"]
                                if r.get("verdict") in sellable_tags))
    slots_total = len(data["retainers"]) * MARKET_SLOTS_PER_RETAINER
    # Slot capacity is per-retainer, so a listable stack only counts toward
    # the plan if its own retainer still has room - counting them globally
    # reports a plan larger than build_report can actually lay out.
    _room = {ret.get("name"): max(0, MARKET_SLOTS_PER_RETAINER
                                  - len(ret.get("market_listings") or []))
             for ret in data["retainers"]}
    listable_now = 0
    for r in data["all_rows"]:
        if r.get("verdict") != "sell":
            continue
        who = r.get("retainer")
        if who in _room:
            if _room[who] <= 0:
                continue
            _room[who] -= 1
        listable_now += 1
    data["summary"] = {
        "retainers": len(data["retainers"]),
        "distinct_stacks": len(data["all_rows"]),
        "unresolved_names": sum(1 for r in data["all_rows"]
                                if not r.get("item_id")),
        # Headline figure is the depth-capped realistic total, not a naive
        # sum of (best current price x full quantity) - see verdict_for.
        "estimated_recoverable_gil": realistic_total,
        "estimated_recoverable_gil_optimistic": optimistic_total,
        "market_slots_total": slots_total,
        # Two different numbers, previously conflated under one misleading
        # name ("market_slots_used", which read as "your board is full" when
        # it actually meant "the plan wants this many slots" - it reported
        # 40/40 on 2026-09-03 with both retainers listing nothing at all).
        # occupied = what is actually on the board right now.
        "market_slots_occupied": sum(len(ret.get("market_listings") or [])
                                     for ret in data["retainers"]),
        # planned = how many slots the "list right now" plan actually fills.
        # Capped by *free* slots, not the theoretical total - you cannot list
        # into a slot that already has something in it, and reporting 40
        # here against a 15-item plan (as this did while occupancy was stuck
        # at 0) contradicts the report it is supposed to summarise.
        "market_slots_planned": min(
            listable_now,
            max(0, slots_total - sum(len(ret.get("market_listings") or [])
                                     for ret in data["retainers"]))),
        "suspect_price_rows": sum(1 for r in data["all_rows"]
                                  if r.get("price_suspect")),
    }
    data["report_md"] = build_report(data) if data["all_rows"] else None
    data["pricing_calibration"] = calibration

    data["still_not_available"] = derive_still_not_available(data)

    if not character.get("name"):
        notes.append("profile selectors likely changed - rerun with --dump")
    if not jobs:
        notes.append("class_job selectors likely changed - rerun with --dump")
    if not qout.get("recent") and not q_note:
        notes.append("quest page parsed but empty - rerun with --dump")
    data["notes"] = notes

    if quest_protection is not None:
        from crafting_protection import write_json
        write_json(args.quest_mats_out or args.quest_mats, quest_protection)
    text = json.dumps(data, indent=None if args.compact else 2,
                      ensure_ascii=False)
    pathlib.Path(args.out).write_text(text + "\n", encoding="utf-8")
    if args.report:
        pathlib.Path(args.report).write_text(data["report_md"] or "", encoding="utf-8")
    print(json.dumps(data["summary"], indent=2))
    if data.get("pricing_calibration"):
        print("\npricing vs this character's own realised sales "
             "(largest residual first):", file=sys.stderr)
        for r in data["pricing_calibration"][:15]:
            print(f"  {r['name']}{' (HQ)' if r['hq'] else ''}: "
                 f"estimated {r['estimated_unit_price']:,} vs realised "
                 f"{r['realized_unit_price']:,} "
                 f"({r['residual_pct']:+.0f}%, source={r['price_source']})",
                 file=sys.stderr)
    print(f"wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
