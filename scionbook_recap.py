"""Validate untrusted recap proposals and install only local player-state changes."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import stat
import tempfile
import shutil
import unicodedata

from scionbook_config import validate_config

OUTPUTS = ("SCIONBOOK_MEMORY.md", "SCIONBOOK_DAILY_WEEKLY_CHECKLIST.md", "scionbook.json")
INPUTS = (*OUTPUTS, "status.json", "quest_history.md", "SCIONBOOK_INSTRUCTIONS.md",
          "AGENTS.md", "standards.md", ".agents/skills/apply-recap/SKILL.md")
SKILL = ".agents/skills/apply-recap/SKILL.md"
MAX_FILE = 2_000_000


def hidden_controls(text):
    return any(unicodedata.category(char) in {"Cf", "Cc"} and char not in "\n\r\t" for char in text)

def hidden_json_controls(value):
    if isinstance(value, str):
        return hidden_controls(value)
    if isinstance(value, dict):
        return any(hidden_controls(key) or hidden_json_controls(item) for key, item in value.items())
    if isinstance(value, list):
        return any(hidden_json_controls(item) for item in value)
    return False


SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "status": {"type": "string", "enum": ["proposed", "needs_input", "failed"]},
        "changes": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {"path": {"type": "string", "enum": list(OUTPUTS)},
                           "content": {"type": "string"}},
            "required": ["path", "content"]}}},
    "required": ["status", "changes"]}


def read_file(root, name):
    """Read bounded regular files only; reject links, including parent-directory links."""
    path = root / name
    for parent in path.relative_to(root).parents:
        if (root / parent).is_symlink():
            raise ValueError("Recap input contains a linked directory.")
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("Recap inputs must be unlinked regular files.")
    with os.fdopen(os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)), "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
            raise ValueError("Recap input changed while opening it.")
        data = stream.read(MAX_FILE + 1)
    if len(data) > MAX_FILE:
        raise ValueError("Recap input exceeds the size limit.")
    data.decode("utf-8")
    return data


def snapshot(root):
    state = {name: read_file(root, name) for name in INPUTS}
    if state["scionbook.json"] is None:
        raise ValueError("Configure this checkout with setup before applying recaps.")
    if not state[SKILL] or not state[SKILL].strip():
        raise ValueError("The apply-recap skill is missing or empty; repair the installation.")
    validate_config(parse_json(state["scionbook.json"]))
    return state


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
    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


@contextmanager
def locked(root):
    if any(root.glob(".scionbook-recap-*/journal.json")):
        raise RuntimeError("An interrupted recap journal needs manual review before another handoff.")
    path = root / ".scionbook-recap.lock"
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise RuntimeError("Recap lock exists; check for an active or interrupted handoff before retrying.") from exc
    os.close(descriptor)
    try:
        yield
    finally:
        path.unlink()


def validate(proposal, original):
    if (not isinstance(proposal, dict) or set(proposal) != {"status", "changes"}
            or proposal["status"] != "proposed" or not isinstance(proposal["changes"], list)
            or not 1 <= len(proposal["changes"]) <= len(OUTPUTS)):
        raise RuntimeError("Recap handoff stopped: no valid proposal; use a manual handoff if clarification is needed.")
    changes = {}
    for item in proposal["changes"]:
        if (not isinstance(item, dict) or set(item) != {"path", "content"}
                or not isinstance(item["path"], str) or item["path"] not in OUTPUTS
                or item["path"] in changes or not isinstance(item["content"], str)
                or not item["content"].strip() or hidden_controls(item["content"])):
            raise ValueError("Invalid recap output; nothing was saved.")
        name, data = item["path"], item["content"].encode("utf-8")
        if len(data) > MAX_FILE:
            raise ValueError("Recap output exceeds the size limit.")
        if name == "scionbook.json":
            before, after = parse_json(original[name]), parse_json(data)
            validate_config(after)
            if hidden_json_controls(after):
                raise ValueError("Hidden control characters are not allowed in preferences.")
            if ({k: v for k, v in before.items() if k != "preferences"}
                    != {k: v for k, v in after.items() if k != "preferences"}):
                raise ValueError("Recaps may change preferences only, never character configuration.")
        changes[name] = data
    return changes


def install(root, original, proposal):
    """Validate all outputs before writing; roll back ordinary installation failures."""
    changes = validate(proposal, original)
    if snapshot(root) != original:
        raise RuntimeError("Recap sources changed during proposal generation; nothing was installed.")
    changes = {name: data for name, data in changes.items() if original[name] != data}
    if not changes:
        return {"status": "unchanged", "summary": "Proposed files already match the saved files; no writes needed."}
    # Retained backups allow manual recovery after a process/machine crash. Never tracked.
    temporary = Path(tempfile.mkdtemp(prefix=".scionbook-recap-", dir=root))
    installed = []
    cleanup = False
    try:
        for index, (name, data) in enumerate(changes.items()):
            with (temporary / f"new-{index}").open("wb") as output:
                os.chmod(output.name, 0o600)
                output.write(data)
            if original[name] is not None:
                (temporary / f"old-{index}").write_bytes(original[name])
        (temporary / "journal.json").write_text(json.dumps(list(changes)), encoding="utf-8")
        for index, (name, data) in enumerate(changes.items()):
            if read_file(root, name) != original[name]:
                raise RuntimeError("Recap destination changed before installation.")
            os.replace(temporary / f"new-{index}", root / name)
            installed.append((index, name, data))
        if snapshot(root) != {**original, **changes}:
            raise RuntimeError("Saved recap bytes or protected sources could not be verified.")
    except BaseException:
        for index, name, data in reversed(installed):
            if read_file(root, name) != data:
                raise RuntimeError("Concurrent edit during save; retain the local recap journal for recovery.")
            if original[name] is None:
                (root / name).unlink()
            else:
                os.replace(temporary / f"old-{index}", root / name)
        cleanup = all(read_file(root, name) == original[name] for name in changes)
        raise
    else:
        cleanup = True
        return {"status": "applied", "summary": f"Saved and verified {len(changes)} recap file(s)."}
    finally:
        # Remove only verified successful saves or verified complete rollbacks.
        if cleanup:
            shutil.rmtree(temporary)
