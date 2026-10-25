#!/usr/bin/env python3
"""Prepare and verify local player-state edits without a model or chat handoff."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

import scionbook_recap as store

REPO = Path(__file__).resolve().parent
TOKEN = re.compile(r"[a-z0-9_]{8,32}\Z")


def check_private_destinations(root):
    """In Git checkouts refuse tracked or nonignored personal destinations."""
    if not any((parent / ".git").exists() for parent in (root, *root.parents)):
        return  # Release ZIPs do not require Git.
    command = ["git", "-C", str(root)]
    destinations = (*store.OUTPUTS, ".scionbook-state-probe/original.json",
                    ".scionbook-recap-probe/journal.json", ".scionbook-recap.lock",
                    "local/state-update.json")
    try:
        tracked = subprocess.run(command + ["ls-files", "-z", "--", *store.OUTPUTS],
                                 capture_output=True, check=True).stdout
        ignored = subprocess.run(command + ["check-ignore", "--no-index", "-z", "--stdin"],
                                 input="\0".join(destinations).encode() + b"\0",
                                 capture_output=True, check=False)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError("Cannot verify local player-file privacy; nothing was saved.") from exc
    if tracked or ignored.returncode not in (0, 1) or set(ignored.stdout.split(b"\0")) - {b""} != {
            name.encode() for name in destinations}:
        raise ValueError("Player destinations must be untracked and ignored; nothing was saved.")


def prepare(root=REPO):
    root = Path(root).resolve()
    check_private_destinations(root)
    with store.locked(root):
        original = store.snapshot(root)
        directory = Path(tempfile.mkdtemp(prefix=".scionbook-state-", dir=root))
        try:
            payload = {name: data.decode("utf-8") if data is not None else None
                       for name, data in original.items()}
            target = directory / "original.json"
            target.touch(mode=0o600)
            target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        except BaseException:
            shutil.rmtree(directory)
            raise
    return directory.name.removeprefix(".scionbook-state-")


def edit_directory(root, token):
    if not TOKEN.fullmatch(token):
        raise ValueError("Invalid local state-edit token.")
    directory = root / (".scionbook-state-" + token)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Local state edit is missing or linked; prepare a new edit.")
    return directory


def apply(token, proposal, root=REPO):
    root = Path(root).resolve()
    check_private_destinations(root)
    directory = edit_directory(root, token)
    with store.locked(root):
        raw = store.read_file(directory, "original.json", max_bytes=store.MAX_FILE * len(store.INPUTS) * 6)
        if raw is None:
            raise ValueError("Local state edit has no original snapshot.")
        original = store.parse_json(raw)
        if (not isinstance(original, dict) or set(original) != set(store.INPUTS)
                or any(value is not None and not isinstance(value, str) for value in original.values())):
            raise ValueError("Invalid local state-edit snapshot.")
        original = {name: value.encode("utf-8") if value is not None else None
                    for name, value in original.items()}
        result = store.install(root, original, proposal)
    shutil.rmtree(directory)
    return result


def cancel(token, root=REPO):
    root = Path(root).resolve()
    with store.locked(root):
        shutil.rmtree(edit_directory(root, token))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("prepare", help="capture original sources before composing changes")
    update = actions.add_parser("apply", help="read a proposed edit from stdin and verify its save")
    update.add_argument("token")
    discard = actions.add_parser("cancel", help="discard an unused prepared edit")
    discard.add_argument("token")
    args = parser.parse_args(argv)
    try:
        if args.action == "prepare":
            print(prepare())
        elif args.action == "cancel":
            cancel(args.token)
            print(json.dumps({"status": "cancelled"}))
        else:
            limit = store.MAX_FILE * len(store.OUTPUTS) * 6 + 10_000  # JSON escaping plus envelope
            raw = sys.stdin.buffer.read(limit + 1)
            if len(raw) > limit:
                raise ValueError("Local state proposal exceeds the size limit.")
            result = apply(args.token, store.parse_json(raw))
            print(json.dumps(result))
    except (OSError, ValueError, RuntimeError):
        # Do not echo parser errors, proposal contents, private paths, or file values.
        parser.exit(1, "Local state edit failed; no success receipt was issued. "
                    "Check the proposal, changed sources, and local recovery journals.\n")


if __name__ == "__main__":
    main()
