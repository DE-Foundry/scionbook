#!/usr/bin/env python3
"""Read Git objects as data; report instruction hazards without executing candidate code."""
import argparse
import codecs
import json
import os
import html
from pathlib import Path, PurePosixPath
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


def read_blob(repo, oid, name):
    """Classify UTF-8 incrementally; skipped binaries consume no scan-size budget."""
    decoder = codecs.getincrementaldecoder("utf-8")()
    chunks, size = [], 0
    with subprocess.Popen(["git", "-C", str(repo), "cat-file", "blob", oid],
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:
        try:
            while chunk := process.stdout.read(65536):
                decoder.decode(chunk)
                size += len(chunk)
                if size <= MAX_FILE:
                    chunks.append(chunk)
            decoder.decode(b"", final=True)
        except UnicodeDecodeError:
            process.kill()
            process.wait()
            # Preserve the invalid-text finding for instruction/configuration paths.
            return b"\xff" if relevant(name) else None
        if process.wait():
            raise ValueError("Could not read a Git blob.")
    if size > MAX_FILE:
        raise ValueError(f"UTF-8 file exceeds {MAX_FILE} scan bytes: {json.dumps(name, ensure_ascii=True)}")
    return b"".join(chunks)


def tree(repo, revision):
    if not re.fullmatch(r"[0-9a-f]{40,64}", revision):
        raise ValueError("Expected a full commit object ID.")
    entries = git(repo, "ls-tree", "-rz", "--full-tree", revision).split(b"\0")
    files, total = {}, 0
    for entry in filter(None, entries):
        metadata, raw_name = entry.split(b"\t", 1)
        mode, kind, oid = metadata.decode("ascii").split()
        name = raw_name.decode("utf-8", "strict")
        if kind != "blob":
            files[name] = (mode, b"")
            continue
        raw = read_blob(repo, oid, name)
        if raw is None:
            continue
        total += len(raw)
        if total > MAX_TREE:
            raise ValueError(f"Scanned text exceeds {MAX_TREE} total bytes at {json.dumps(name, ensure_ascii=True)}")
        files[name] = (mode, raw)
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
            if relevant(name):
                findings.append(("error", name, "instruction input is not UTF-8"))
            continue
        if any(unicodedata.category(char) in {"Cf", "Cc"} and char not in "\n\r\t" for char in name + text):
            findings.append(("error", name, "hidden or bidirectional control character"))
        if not relevant(name):
            continue
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


def write_summary(findings):
    destination = os.environ.get("GITHUB_STEP_SUMMARY")
    if not destination:
        return
    # JSON quotes controls; HTML escapes markup. Inside pre, Markdown is inert.
    rows = [json.dumps({"severity": level, "path": name, "reason": reason}, ensure_ascii=True)
            for level, name, reason in findings]
    body = "\n".join(rows) if rows else "No instruction-security findings."
    with Path(destination).open("a", encoding="utf-8") as stream:
        stream.write("## Instruction security findings\n\n")
        stream.write("Review findings require maintainer inspection even when the check is green.\n\n")
        stream.write("<pre>" + html.escape(body) + "</pre>\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--head", required=True)
    parser.add_argument("--base")
    args = parser.parse_args()
    try:
        findings = scan(tree(args.repo, args.head), tree(args.repo, args.base) if args.base else None)
    except ValueError as exc:
        raise SystemExit(f"Instruction scan could not complete: {exc}") from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit("Instruction scan could not read Git objects.") from exc
    # ASCII JSON avoids control/annotation injection from candidate filenames or content.
    print(json.dumps([{"severity": level, "path": name, "reason": reason}
                      for level, name, reason in findings], ensure_ascii=True, indent=2))
    write_summary(findings)
    raise SystemExit(1 if any(level == "error" for level, _, _ in findings) else 0)


if __name__ == "__main__":
    main()
