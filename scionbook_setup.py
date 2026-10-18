#!/usr/bin/env python3
"""Resolve a Lodestone character and initialize local Scionbook state.

Run from the repository root. This helper never handles credentials or scrapes
private state; the setup skill follows initialization with a validated sync.
"""
import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from scionbook_config import REPO, initial_preferences, load_config, validate_config

from scionbook_http import LODESTONE, LODESTONE_HEADERS

BASE = f"{LODESTONE}/character"
STATE_FILES = ("status.json", "cleanup.md", "quest_history.md", "quest_mats.json",
               "quest_turnins.json", "SCIONBOOK_MEMORY.md",
               "SCIONBOOK_DAILY_WEEKLY_CHECKLIST.md")


def normalized(value):
    return " ".join(value.split()).casefold()


def world_and_dc(text):
    match = re.fullmatch(r"\s*(.+?)\s*\[([^\]]+)\]\s*", text)
    if not match:
        raise ValueError("Lodestone world/data-center markup was not recognized.")
    return match.group(1).strip(), match.group(2).strip()


def profile_id(value):
    if value.isascii() and value.isdigit() and int(value) > 0:
        return value
    url = urlparse(value)
    match = re.fullmatch(r"/lodestone/character/([1-9][0-9]*)/?", url.path)
    if (url.scheme != "https" or url.hostname not in {
            "na.finalfantasyxiv.com", "eu.finalfantasyxiv.com",
            "fr.finalfantasyxiv.com", "de.finalfantasyxiv.com", "jp.finalfantasyxiv.com"}
            or url.username or url.password or url.port or not match):
        raise ValueError("Use a numeric ID or an official HTTPS Lodestone character URL.")
    return match.group(1)


def parse_search(html, name, world):
    matches = {}
    soup = BeautifulSoup(html, "html.parser")
    for entry in soup.select("a.entry__link, a.entry__chara__link"):
        match = re.fullmatch(r"/lodestone/character/([1-9][0-9]*)/", entry.get("href", ""))
        name_el, world_el = entry.select_one(".entry__name"), entry.select_one(".entry__world")
        if not match or name_el is None or world_el is None:
            continue
        found_world, dc = world_and_dc(world_el.get_text(" ", strip=True))
        found_name = name_el.get_text(" ", strip=True)
        if normalized(found_name) == normalized(name) and normalized(found_world) == normalized(world):
            cid = match.group(1)
            matches[cid] = dict(character_id=cid, name=found_name, world=found_world, data_center=dc)
    return list(matches.values())


def get_html(session, url, **kwargs):
    response = session.get(url, timeout=30, **kwargs)
    response.raise_for_status()
    return response.text


def verify_profile(session, cid, name=None, world=None):
    html = get_html(session, f"{BASE}/{cid}/")
    soup = BeautifulSoup(html, "html.parser")
    name_el, world_el = soup.select_one(".frame__chara__name"), soup.select_one(".frame__chara__world")
    if name_el is None or world_el is None:
        raise ValueError("Could not verify the character profile; no local files were initialized.")
    found_name = name_el.get_text(" ", strip=True)
    found_world, dc = world_and_dc(world_el.get_text(" ", strip=True))
    if name and normalized(name) != normalized(found_name):
        raise ValueError("Profile name does not match the requested character.")
    if world and normalized(world) != normalized(found_world):
        raise ValueError("Profile home world does not match the requested character.")
    return dict(character_id=cid, name=found_name, world=found_world, data_center=dc)


def find_character(session, name, world):
    matches = {}
    # Lodestone limits results to 20 pages. Never guess from a partial name.
    for page in range(1, 21):
        html = get_html(session, BASE + "/", params={"q": name, "worldname": world, "page": page})
        for candidate in parse_search(html, name, world):
            matches[candidate["character_id"]] = candidate
        soup = BeautifulSoup(html, "html.parser")
        if not soup.select_one(".btn__pager__next:not(.btn__pager__no)"):
            break
        time.sleep(0.4)
    if len(matches) != 1:
        raise ValueError(f"Found {len(matches)} exact matches. Check name/home world or supply --profile URL.")
    return verify_profile(session, next(iter(matches)), name, world)


def initialize(identity, timezone=None, mode=None, directory=REPO):
    directory = Path(directory)
    config_path = directory / "scionbook.json"
    old = load_config(config_path, required=False)
    if old and old["character_id"] != identity["character_id"]:
        raise ValueError("Another character is configured. Use a separate checkout to keep progress isolated.")
    if not old and any((directory / name).exists() for name in STATE_FILES):
        raise ValueError("Unconfigured player files already exist. Move them aside before setup; nothing was overwritten.")
    config = validate_config({
        "version": 1, **identity,
        "timezone": timezone or (old or {}).get("timezone", "UTC"),
        "mode": mode or (old or {}).get("mode", "full"),
        "preferences": old.get("preferences", {}) if old else initial_preferences(directory)})
    templates = REPO / "templates"
    pending = {name: (templates / name).read_text(encoding="utf-8")
               for name in ("SCIONBOOK_MEMORY.md", "SCIONBOOK_DAILY_WEEKLY_CHECKLIST.md")
               if not (directory / name).exists()}
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / "scionbook.json.tmp"
    created = []
    try:
        temporary.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        for name, content in pending.items():
            path = directory / name
            with path.open("x", encoding="utf-8") as output:
                created.append(path)
                output.write(content)
        temporary.replace(config_path)
    except OSError:
        for path in created:
            path.unlink(missing_ok=True)
        temporary.unlink(missing_ok=True)
        raise
    return config


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--name", help="full character name")
    ap.add_argument("--world", help="home world, not the currently visited world")
    ap.add_argument("--profile", help="official Lodestone profile URL or numeric ID")
    ap.add_argument("--timezone", help="IANA timezone (new setup: UTC; rerun: preserve)")
    ap.add_argument("--mode", choices=("full", "public"), help="new setup: full; rerun: preserve")
    ap.add_argument("--lookup-only", action="store_true", help="print verified identity without writing files")
    args = ap.parse_args()
    if not args.profile and not (args.name and args.world):
        ap.error("Provide --name and --world, or --profile.")
    try:
        with requests.Session() as session:
            session.headers.update(LODESTONE_HEADERS)
            identity = (verify_profile(session, profile_id(args.profile), args.name, args.world)
                        if args.profile else find_character(session, args.name, args.world))
        if args.lookup_only:
            print(json.dumps(identity, indent=2))
        else:
            config = initialize(identity, args.timezone, args.mode)
            print(f"Configured {config['name']} on {config['world']} [{config['data_center']}].")
            print("Local files initialized. Run $sync in the Maintainer chat for the first validated snapshot.")
    except (ValueError, OSError, requests.RequestException) as exc:
        ap.exit(1, f"Setup failed: {exc}\n")


if __name__ == "__main__":
    main()
