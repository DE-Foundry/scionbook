#!/usr/bin/env python3
"""Read Git objects as data; report instruction hazards without executing candidate code."""
import argparse
import json
from pathlib import PurePosixPath
import re
import subprocess
import unicodedata

MAX_FILE = 2_000_000
MAX_TREE = 20_000_000
PROTECTED = ("scripts/check_instruction_security.py", ".github/workflows/", "scionbook_handoff.py",
             "scionbook_recap.py", "tests/test_instruction_security.py", "tests/test_recap_security.py")
RISK = re.compile(r"dangerously[-_]\w+|bypassPermissions|danger-full-access|"
                  r"(?:curl|wget)\b[^\n]*\|\s*(?:ba)?sh|"
                  r"ignore (?:all |previous |prior )*instructions|"
                  r"(?:hooks|mcpServers|mcp_servers|allowedTools|permissions)\s*[=:]", re.I)
URL = re.compile(r"https?://[^\s<>\[\]`\"')]+", re.I)


def relevant(name):
    return (PurePosixPath(name).suffix.lower() in {".md", ".toml", ".json", ".yaml", ".yml"}
            or name.startswith((".agents/", ".claude/", ".codex/", ".github/", "scripts/"))
            or name in {"scionbook_handoff.py", "scionbook_recap.py"})


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def tree(repo, revision):
    if not re.fullmatch(r"[0-9a-f]{40,64}", revision):
        raise ValueError("Expected a full commit object ID.")
    entries = git(repo, "ls-tree", "-rz", "--full-tree", revision).split(b"\0")
    files, total = {}, 0
    for entry in filter(None, entries):
        metadata, raw_name = entry.split(b"\t", 1)
        mode, kind, oid = metadata.decode("ascii").split()
        name = raw_name.decode("utf-8", "strict")
        if not relevant(name):
            continue
        if kind != "blob":
            files[name] = (mode, b"")
            continue
        size = int(git(repo, "cat-file", "-s", oid))
        total += size
        if size > MAX_FILE or total > MAX_TREE:
            raise ValueError("Instruction scan size limit exceeded.")
        files[name] = (mode, git(repo, "cat-file", "blob", oid))
    return files


def scan(candidate, baseline=None):
    baseline = baseline or {}
    findings = []
    for name, (mode, raw) in sorted(candidate.items()):
        if (name == ".claude/skills" and mode == "120000" and raw == b"../.agents/skills"
                and any(p.startswith(".agents/skills/") for p in candidate)):
            continue  # The sole shipped adapter alias; target files are scanned independently.
        if mode not in {"100644", "100755"}:
            findings.append(("error", name, "linked instruction/configuration path"))
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            findings.append(("error", name, "instruction input is not UTF-8"))
            continue
        if any(unicodedata.category(char) in {"Cf", "Cc"} and char not in "\n\r\t" for char in name + text):
            findings.append(("error", name, "hidden or bidirectional control character"))
        previous = baseline.get(name, (None, b""))
        if previous == (mode, raw):
            continue
        before = previous[1].decode("utf-8", "replace")
        if any(name == prefix or name.startswith(prefix) for prefix in PROTECTED):
            findings.append(("review", name, "security evaluator, adapter, test, or workflow changed"))
        if mode == "100755" and previous[0] != mode:
            findings.append(("review", name, "new executable input"))
        if set(URL.findall(text)) - set(URL.findall(before)):
            findings.append(("review", name, "new external destination; review diff before approval"))
        if set(RISK.findall(text)) - set(RISK.findall(before)):
            findings.append(("review", name, "execution/permission instruction requires human review"))
    for name in baseline.keys() - candidate.keys():
        if any(name == prefix or name.startswith(prefix) for prefix in PROTECTED):
            findings.append(("review", name, "security control removed"))
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--head", required=True)
    parser.add_argument("--base")
    args = parser.parse_args()
    try:
        findings = scan(tree(args.repo, args.head), tree(args.repo, args.base) if args.base else None)
    except (ValueError, subprocess.CalledProcessError) as exc:
        raise SystemExit("Instruction scan could not complete; review inputs and limits.") from exc
    # ASCII JSON avoids control/annotation injection from candidate filenames or content.
    print(json.dumps([{"severity": level, "path": name, "reason": reason}
                      for level, name, reason in findings], ensure_ascii=True, indent=2))
    raise SystemExit(1 if any(level == "error" for level, _, _ in findings) else 0)


if __name__ == "__main__":
    main()
