"""Local character configuration shared by the command-line tools."""
import json
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

REPO = Path(__file__).resolve().parent
CONFIG_PATH = REPO / "scionbook.json"


def parse_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key.")
            result[key] = value
        return result
    def constant(_):
        raise ValueError("Non-finite JSON value.")
    if isinstance(text, bytes):
        text = text.decode("utf-8-sig")
    if isinstance(text, str):
        text = text.removeprefix("\ufeff")
    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def default_preferences():
    """Return fresh defaults without reading a pre-setup seed."""
    return {"platform": "unspecified", "input": "unspecified", "spoilers": "minimal",
            "goals": [], "retainer_order": [], "inventory_policy": "conservative"}


def validate_preferences(preferences):
    """Validate optional gameplay fields without restricting legacy preferences."""
    if not isinstance(preferences, dict):
        raise ValueError("preferences must be an object.")
    gameplay = preferences.get("gameplay", {})
    if not isinstance(gameplay, dict):
        raise ValueError("preferences.gameplay must be an object.")
    for key in ("priorities", "combat_leveling_routine"):
        if key in gameplay:
            values = gameplay[key]
            if not isinstance(values, list) or any(
                    not isinstance(value, str) or not value.strip() for value in values):
                raise ValueError(f"preferences.gameplay.{key} must be a list of nonblank strings.")
    return preferences


def initial_preferences(directory):
    """Read a preferences-only seed for first setup, never an alternate identity."""
    path = Path(directory) / "local" / "gameplay-preferences.json"
    defaults = default_preferences()
    if path.exists():
        try:
            seed = parse_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError("Cannot read local gameplay preferences.") from exc
        if not isinstance(seed, dict) or set(seed) != {"preferences"}:
            raise ValueError("Local gameplay preferences must contain only preferences.")
        preferences = validate_preferences(seed["preferences"])
        if set(preferences) - {"gameplay"}:
            raise ValueError("Local gameplay preference seeds may contain only preferences.gameplay.")
        defaults.update(preferences)
    return defaults


def validate_config(config):
    if not isinstance(config, dict) or config.get("version") != 1:
        raise ValueError("Unsupported Scionbook configuration; run $setup.")
    for key in ("character_id", "name", "world", "data_center", "timezone"):
        if not isinstance(config.get(key), str) or not config[key].strip():
            raise ValueError(f"Missing configuration field: {key}")
    if not config["character_id"].isascii() or not config["character_id"].isdigit() or int(config["character_id"]) <= 0:
        raise ValueError("character_id must be a positive numeric Lodestone ID.")
    try:
        ZoneInfo(config["timezone"])
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("timezone must be a valid IANA timezone, for example UTC.") from exc
    if config.get("mode") not in ("full", "public"):
        raise ValueError("mode must be full or public.")
    validate_preferences(config.get("preferences", {}))
    return config


def load_config(path=CONFIG_PATH, required=True):
    path = Path(path)
    if not path.exists():
        if required:
            raise ValueError("Character is not configured. Run $setup first.")
        return None
    try:
        config = parse_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot read configuration: {path.name}") from exc
    return validate_config(config)


def resolve_identity(character_id=None, world=None, data_center=None, config_path=CONFIG_PATH):
    explicit = (character_id, world, data_center)
    if any(explicit):
        if not all(explicit):
            raise ValueError("Supply --id, --world and --dc together, or use $setup.")
        if not str(character_id).isascii() or not str(character_id).isdigit() or int(character_id) <= 0:
            raise ValueError("--id must be a positive numeric Lodestone ID.")
        return tuple(str(value).strip() for value in explicit)
    config = load_config(config_path)
    return config["character_id"], config["world"], config["data_center"]


def resolve_mode(mode=None, config_path=CONFIG_PATH, *, explicit_identity=False):
    """Explicit mode wins; standalone identities do not inherit another character's mode."""
    if mode is not None:
        if mode not in ("full", "public"):
            raise ValueError("mode must be full or public.")
        return mode
    if explicit_identity:
        return "full"
    return load_config(config_path)["mode"]
