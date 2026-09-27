"""Persist and reconcile crafting protection from researched quests and snapshots."""
import copy
import json
import os
from pathlib import Path
import tempfile
from datetime import datetime, timezone


def read_json(path, missing=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return missing


def write_json(path, data):
    """Replace one data file only after its complete contents are written."""
    path = Path(path)
    fd, temp = tempfile.mkstemp(prefix=".scionbook-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def positive(value):
    return type(value) is int and value > 0


def text(value):
    return isinstance(value, str) and bool(value.strip())


def timestamp(value):
    if not text(value):
        raise ValueError("A dated source is required.")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("Source timestamps must include a timezone.")
    return stamp


def validate_plan(plan):
    if not isinstance(plan, dict) or plan.get("version") != 2:
        raise ValueError("Automatic reconciliation requires quest_turnins.json version 2.")
    if not text(plan.get("character_id")):
        raise ValueError("Crafting plan needs a character_id.")
    coverage = plan.get("coverage")
    if not isinstance(coverage, dict) or any(not text(j) or not positive(l) for j, l in coverage.items()):
        raise ValueError("coverage must map researched jobs to their highest verified level.")
    quests = plan.get("quests")
    if not isinstance(quests, list):
        raise ValueError("quests must be a list of researched quest records.")
    keys = set()
    for quest in quests:
        if not isinstance(quest, dict):
            raise ValueError("Invalid quest record.")
        for key in ("qid", "name", "job"):
            if not text(quest.get(key)):
                raise ValueError(f"Quest requires {key}.")
        if quest["qid"] in keys:
            raise ValueError("Duplicate quest ID in crafting plan.")
        keys.add(quest["qid"])
        if not positive(quest.get("level")):
            raise ValueError("Quest level must be positive.")
        if quest.get("kind") not in ("ordinary", "special", "no_turnin"):
            raise ValueError("Quest kind must be ordinary, special, or no_turnin.")
        if not isinstance(quest.get("sources"), list) or not quest["sources"] or any(not text(s) for s in quest["sources"]):
            raise ValueError("Quest reference sources are required.")
        timestamp(quest.get("verified_at_utc"))
        items = quest.get("turnins")
        if not isinstance(items, list) or (quest["kind"] == "ordinary" and not items):
            raise ValueError("Ordinary quests need researched turn-ins.")
        if quest["kind"] == "no_turnin" and items:
            raise ValueError("A no-turn-in quest cannot contain turn-ins.")
        for item in items:
            if (not isinstance(item, dict) or not text(item.get("name"))
                    or not positive(item.get("quantity")) or type(item.get("hq")) is not bool):
                raise ValueError("Each turn-in needs name, positive quantity, and boolean hq.")
    keeps = plan.get("keeps", [])
    if not isinstance(keeps, list):
        raise ValueError("keeps must be a list.")
    for keep in keeps:
        if not isinstance(keep, dict) or not text(keep.get("name")) or not text(keep.get("reason")):
            raise ValueError("Explicit keeps need a name and reason.")
        if "until_level" in keep and (not positive(keep["until_level"]) or not text(keep.get("job"))):
            raise ValueError("Expiring keeps need a job and positive until_level.")
    return plan


def validated_snapshot(plan, status, previous):
    if not isinstance(status, dict):
        raise ValueError("A saved character snapshot is required.")
    if str(status.get("character_id")) != plan["character_id"]:
        raise ValueError("Crafting plan and snapshot belong to different characters.")
    fetched = timestamp(status.get("fetched_at_utc"))
    history = status.get("quests") or {}
    entries, total = history.get("recent"), history.get("total_completed")
    if (status.get("authenticated") is not True or history.get("note")
            or type(total) is not int or total < 0 or not isinstance(entries, list)
            or len(entries) != total):
        raise ValueError("Complete authenticated quest history is required; prior protection preserved.")
    if any(not isinstance(q, dict) or not text(q.get("qid")) for q in entries):
        raise ValueError("Completed quest entries must have Lodestone quest IDs.")
    completed = {q["qid"] for q in entries}
    if len(completed) != total:
        raise ValueError("Duplicate completed quests cannot establish complete history.")
    levels = (status.get("jobs") or {}).get("crafters")
    if (not isinstance(levels, dict) or status.get("jobs_parsed") == 0
            or any(not positive(l) for l in levels.values())):
        raise ValueError("Valid crafting job levels are required.")
    if previous and previous.get("version") == 2:
        if previous.get("character_id") != plan["character_id"]:
            raise ValueError("Previous crafting protection belongs to another character.")
        if fetched < timestamp(previous.get("source_fetched_at_utc")):
            raise ValueError("An older snapshot cannot replace newer crafting protection.")
        # A later scrape may still lag gameplay or have an incomplete history.
        old_completed = {q["qid"] for q in previous.get("quests", []) if q.get("state") == "completed"}
        if not old_completed <= completed:
            raise ValueError("Previously completed crafting quests vanished; prior protection preserved.")
        for job, level in previous.get("job_levels", {}).items():
            if levels.get(job, 0) < level:
                raise ValueError("Crafting levels regressed or disappeared; prior protection preserved.")
    return levels, completed


def reconcile(plan, status, previous=None, refresh_recipes=False):
    """Reuse saved recipes, select unfinished quests, and rebuild the keep union."""
    from scionbook_quest_mats import build_closure, flatten_leaves

    validate_plan(plan)
    if previous is not None and not isinstance(previous, dict):
        raise ValueError("Previous protection must be an object.")
    levels, completed = validated_snapshot(plan, status, previous)
    cache = copy.deepcopy((previous or {}).get("recipe_cache", {})) if not refresh_recipes else {}
    if not isinstance(cache, dict):
        raise ValueError("Invalid recipe cache; refresh recipes explicitly.")
    def validate_tree(node):
        if (not isinstance(node, dict) or not text(node.get("name"))
                or type(node.get("is_craftable")) is not bool
                or not isinstance(node.get("ingredients"), list)):
            raise ValueError("Malformed cached recipe; refresh recipes explicitly.")
        for child in node["ingredients"]:
            validate_tree(child)
    for name, tree in cache.items():
        validate_tree(tree)
        if tree["name"] != name:
            raise ValueError("Recipe cache key/name mismatch.")
    cached_names = set(cache)
    selected, records, gaps = {}, [], []
    for job, level in levels.items():
        if plan["coverage"].get(job, 0) < level:
            gaps.append(f"{job}: quest references researched through level {plan['coverage'].get(job, 0)}, current level {level}")
    for quest in plan["quests"]:
        state = "completed" if quest["qid"] in completed else (
            "unfinished" if quest["level"] <= levels.get(quest["job"], 0) else "future")
        records.append({**quest, "state": state})
        if state != "unfinished":
            continue
        if quest["kind"] == "special":
            gaps.append(f"{quest['name']}: special quest materials need separate verification")
        elif quest["kind"] == "ordinary":
            names = selected.setdefault(quest["job"], {}).setdefault(quest["level"], [])
            names.extend(i["name"] for i in quest["turnins"] if i["name"] not in names)
    closure = build_closure(selected, cache=cache)
    checked_at = {} if refresh_recipes else dict((previous or {}).get("recipe_checked_at_utc", {}))
    for name in set(cache) - cached_names:
        checked_at[name] = closure["generated_at_utc"]
    reasons = {}
    for quest in records:
        if quest["state"] != "unfinished" or quest["kind"] != "ordinary":
            continue
        for item in quest["turnins"]:
            for name in flatten_leaves(cache[item["name"]]):
                reason = {"kind": "quest", "qid": quest["qid"], "quest": quest["name"],
                          "job": quest["job"], "level": quest["level"], "basis": "inferred_unfinished"}
                if reason not in reasons.setdefault(name, []):
                    reasons[name].append(reason)
    active_keeps = []
    for keep in plan.get("keeps", []):
        if "until_level" in keep and levels.get(keep["job"], 0) >= keep["until_level"]:
            continue
        active_keeps.append(keep)
        reasons.setdefault(keep["name"], []).append({"kind": "explicit_keep", **keep})
    old = set((previous or {}).get("protected_materials", []))
    protected = set(reasons)
    return {**closure, "version": 2, "character_id": plan["character_id"],
            "source_fetched_at_utc": status["fetched_at_utc"], "job_levels": levels,
            "coverage": plan["coverage"], "coverage_gaps": gaps,
            "recipe_checked_at_utc": checked_at,
            "recipe_source": "https://beta.xivapi.com/api/1",
            "quests": records, "active_keeps": active_keeps,
            "protected_materials": sorted(protected), "material_reasons": reasons,
            "added_materials": sorted(protected - old), "released_materials": sorted(old - protected)}
