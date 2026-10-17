"""Generate quest-material protection from a local quest_turnins.json mapping.

Input shape: {"Carpenter": {"10": ["Verified turn-in item name"]}}.
Include confirmed or inferred unfinished quests. Infer using job levels plus complete
quest history and verified quest-chain references; levels alone do not prove completion.
Version 2 inputs persist quest evidence and explicit keeps; --status reconciles them
against completed quests and levels, reusing the recipe cache in the output file.
Run: python3 scionbook_quest_mats.py --turnins quest_turnins.json
Unknown recipes fail without replacing the previous protection file.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone

import requests
from scionbook_http import HTTP_HEADERS

XIVAPI = "https://beta.xivapi.com/api/1"

def load_turnins(path):
    with open(path, encoding="utf-8") as source:
        data = json.load(source)
    if not isinstance(data, dict) or not data:
        raise ValueError("Provide a non-empty mapping of pending job quest turn-ins.")
    result = {}
    for job, levels in data.items():
        if not isinstance(job, str) or not job.strip() or not isinstance(levels, dict) or not levels:
            raise ValueError("Each job needs a mapping of levels to item names.")
        result[job] = {}
        for level, names in levels.items():
            if not str(level).isdigit() or int(level) < 1:
                raise ValueError("Turn-in levels must be positive integers.")
            if not isinstance(names, list) or not names or any(not isinstance(n, str) or not n.strip() for n in names):
                raise ValueError("Each level needs a non-empty list of item names.")
            result[job][int(level)] = [n.strip() for n in names]
    return result


def find_recipe(name, session):
    """First recipe whose ItemResult exactly matches `name`. Some items have
    multiple recipes (different crafting classes, or a HQ/collectable
    variant) - the ingredient list is the same set of raw materials either
    way for every case checked here, so the first match is enough."""
    url = (f"{XIVAPI}/search?sheets=Recipe&query=ItemResult.Name=\"{name}\""
          f"&fields=ItemResult.Name,AmountResult,AmountIngredient,"
          f"Ingredient[].Name&limit=1")
    r = session.get(url, timeout=30)
    r.raise_for_status()
    results = r.json().get("results")
    return results[0]["fields"] if results else None


def recipe_ingredients(recipe_fields):
    """(name, qty) pairs for a recipe's real ingredients - filters the
    padding slots (item id 0) and the -1 array-length sentinel."""
    names = recipe_fields.get("Ingredient") or []
    amounts = recipe_fields.get("AmountIngredient") or []
    out = []
    for ing, qty in zip(names, amounts):
        if not isinstance(ing, dict):
            continue
        item_name = (ing.get("fields") or {}).get("Name")
        if item_name and ing.get("row_id"):
            out.append((item_name, qty))
    return out


def cache_has_batch_yields(node):
    """Legacy trees must be fetched again, including nested recipe copies."""
    if node.get("is_craftable"):
        amount = node.get("amount_result")
        if type(amount) is not int or amount < 1:
            return False
        for child in node.get("ingredients", []):
            qty = child.get("qty_per_craft")
            if type(qty) is not int or qty < 1 or "qty_per_unit" in child:
                return False
    return all(cache_has_batch_yields(child) for child in node.get("ingredients", []))


def walk_closure(item_name, session, cache, path=()):
    """Recursively expand an item into its raw-material closure.

    Returns a dict: {"name": ..., "is_craftable": bool,
                     "amount_result": output per craft (craftable nodes only),
                     "ingredients": [subtree with qty_per_craft, ...]}
    A leaf (no recipe found - a gatherable, a shard/crystal, a monster drop,
    or a vendor purchase) has an empty ingredients list.

    `cache` memoizes by name since ingredients repeat heavily across
    recipes (Ice Shard and Earth Shard appear in nearly every level-40-50
    Armorer/Carpenter/Leatherworker recipe). `path` guards against a cyclic
    recipe graph, which shouldn't exist in FFXIV's data but costs nothing to
    guard against."""
    if item_name in cache and cache_has_batch_yields(cache[item_name]):
        return cache[item_name]
    if item_name in path:
        return {"name": item_name, "is_craftable": False, "ingredients": [],
                "note": "cycle detected, treated as leaf"}
    recipe = find_recipe(item_name, session)
    time.sleep(0.1)
    if not recipe:
        node = {"name": item_name, "is_craftable": False, "ingredients": []}
    else:
        amount_result = recipe.get("AmountResult")
        if type(amount_result) is not int or amount_result < 1:
            raise ValueError(f"Invalid or missing recipe yield for {item_name!r}.")
        children = []
        for ing_name, qty in recipe_ingredients(recipe):
            child = walk_closure(ing_name, session, cache, path + (item_name,))
            if type(qty) is not int or qty < 1:
                raise ValueError(f"Invalid ingredient quantity for {item_name!r}.")
            children.append({**child, "qty_per_craft": qty})
        node = {"name": item_name, "is_craftable": True,
                "amount_result": amount_result, "ingredients": children}
    cache[item_name] = node
    return node


def flatten_leaves(node, out=None):
    """Every material name under a closure tree, at every level - raw
    leaves AND intermediate crafts, including the turn-in item itself.

    Originally this only collected leaves, on the assumption that an
    intermediate craft (Mythril Plate, Boar Leather, ...) "either doesn't
    exist yet in the bag or isn't the thing being sold off." That assumption
    was wrong and cost real protection: flagged live 2026-09-04 - Taffeta
    Cloth, Boar Leather, Horn Glue, Fine Wax, Silver Ingot, and Hard Leather
    are all intermediate crafts that genuinely sit in retainer inventory and
    genuinely got marked sellable, because none of them are leaves in their
    own recipe tree (they're each one step from a raw material). Whatever
    stage of a recipe you're holding - raw material, half-finished
    intermediate, or the completed turn-in item itself - selling it costs
    you the same quest turn-in, so all of it is protected now."""
    if out is None:
        out = set()
    out.add(node["name"])
    for child in node["ingredients"]:
        flatten_leaves(child, out)
    return out


class UnresolvedTurnIn(Exception):
    """A configured turn-in item matched no recipe. See check_turnins_resolve."""


def check_turnins_resolve(turnins):
    """Every turn-in in quest_turnins must have resolved a real recipe.

    This is the mechanical replacement for "hand-check each name against the
    Item sheet before adding it," which was a comment asking a human to be
    careful. The failure it catches is silent by construction: walk_closure
    on a misspelled or invented item name finds no recipe, returns a
    childless leaf, and flatten_leaves then "protects" exactly one string
    that matches nothing in inventory. The run still succeeds, quest_mats.json
    still looks populated, and the tier it was supposed to cover is protecting
    nothing at all - the worst possible outcome for a fail-closed pipeline,
    since it looks identical to success.

    Every Disciple of the Hand class-quest turn-in is a crafted item by
    definition, so "no recipe" is never legitimate here - it always means the
    name is wrong. Returns [(job, level, item), ...] for each bad entry."""
    bad = []
    for job, levels in turnins.items():
        for level, trees in levels.items():
            for tree in trees:
                if not tree.get("is_craftable"):
                    bad.append((job, level, tree["name"]))
    return bad


def build_closure(quest_turnins, cache=None):
    session = requests.Session()
    session.headers.update(HTTP_HEADERS)
    cache = {} if cache is None else cache
    # Repair every retained legacy entry, including currently inactive recipes.
    for name in list(cache):
        if not cache_has_batch_yields(cache[name]):
            walk_closure(name, session, cache)
    turnins = {}
    all_leaves = set()
    for job, levels in quest_turnins.items():
        turnins[job] = {}
        for level, items in sorted(levels.items()):
            trees = []
            for item in items:
                print(f"  {job} {level}: {item}...", file=sys.stderr)
                tree = walk_closure(item, session, cache)
                trees.append(tree)
                all_leaves |= flatten_leaves(tree)
            turnins[job][level] = trees

    bad = check_turnins_resolve(turnins)
    if bad:
        lines = "\n".join(f"    {job} {level}: {item!r}"
                          for job, level, item in bad)
        raise UnresolvedTurnIn(
            f"{len(bad)} turn-in item(s) in quest_turnins matched no "
            f"recipe:\n{lines}\n"
            "  Every DoH class-quest turn-in is craftable, so this means the "
            "name is wrong - check it against the class's wiki quest page and "
            "the Item sheet, then fix quest_turnins. Refusing to write a "
            "quest_mats.json that would silently protect nothing for that "
            "tier.")

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "tiers_covered": {job: sorted(levels) for job, levels
                          in quest_turnins.items()},
        "turnins": turnins,
        "protected_materials": sorted(all_leaves),
        "recipe_cache": cache,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--turnins", default="quest_turnins.json", help="local mapping of pending quest turn-ins")
    ap.add_argument("--status", help="reconcile a version 2 plan against a complete snapshot")
    ap.add_argument("--cache", help="previous protection/cache file (defaults to --out)")
    ap.add_argument("--refresh-recipes", action="store_true", help="explicitly rebuild cached recipe data")
    ap.add_argument("--check", metavar="STATUS_JSON",
                    help="cross-reference protected materials against a "
                         "status.json's retainer inventory")
    ap.add_argument("--out", default="quest_mats.json",
                    help="where to write the material closure (default: "
                         "quest_mats.json). Use this rather than a shell "
                         "redirect - progress goes to stderr and the file is "
                         "written here, so '> quest_mats.json' just truncates "
                         "it to empty.")
    args = ap.parse_args()

    print("walking quest turn-in recipe trees...", file=sys.stderr)
    try:
        from crafting_protection import read_json, reconcile, write_json
        try:
            previous = read_json(args.cache or args.out)
        except ValueError:
            raise ValueError("Previous protection is malformed; preserve it and repair before rebuilding.")
        if args.status:
            closure = reconcile(read_json(args.turnins), read_json(args.status), previous,
                                refresh_recipes=args.refresh_recipes)
        else:
            cache = {} if args.refresh_recipes else (previous or {}).get("recipe_cache", {})
            closure = build_closure(load_turnins(args.turnins), cache=cache)
    except (UnresolvedTurnIn, ValueError, OSError, requests.RequestException) as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        return 1
    write_json(args.out, closure)
    tiers = sorted({lvl for lvls in closure["tiers_covered"].values()
                    for lvl in lvls})
    print(f"wrote {args.out}: {len(closure['protected_materials'])} "
         f"protected materials across tiers {tiers}", file=sys.stderr)

    if args.check:
        with open(args.check, encoding="utf-8") as f:
            status = json.load(f)
        protected = {n.lower() for n in closure["protected_materials"]}
        hits = [r for r in status.get("all_rows", [])
               if (r.get("name") or "").strip().lower() in protected
               and r.get("verdict") in ("sell", "sell_on_dc", "sell_slow",
                                        "non_home_world_price", "vendor_or_discard")]
        print(f"\n{len(hits)} inventory row(s) currently marked sellable "
             f"but feed a pending quest turn-in:", file=sys.stderr)
        for r in sorted(hits, key=lambda r: -(r.get("est_value") or 0)):
            print(f"  {r['name']} x{r['quantity']} [{r['retainer']}] - "
                 f"currently: {r['verdict']} (~{r.get('est_value') or 0:,}g)",
                 file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
