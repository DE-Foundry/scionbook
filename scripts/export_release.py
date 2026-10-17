#!/usr/bin/env python3
"""Export the committed tree into a new repository with no prior history.

Use this optional tool when preparing a source-only release from a checkout whose history
should not be published. Existing clean repositories can use their normal release workflow.

    python3 scripts/export_release.py ../scionbook-release
    python3 scripts/export_release.py ../scionbook-release --deny extra-terms.txt --commit

The export takes only committed files at HEAD, refuses personal-state filenames, and scans every file
for identifying terms: the local character's ID, name and retainer names (from scionbook.json and
status.json when present), plus any terms in .scionbook-release-denylist or --deny, one per line.
Terms are matched case-insensitively. Nothing is pushed.
"""
import argparse
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DENYLIST = ".scionbook-release-denylist"
# Personal state names from .gitignore; only the neutral templates may carry these names.
PERSONAL_NAMES = ("scionbook.json", "status.json", "cleanup.md", "quest_history.md",
                  "quest_mats.json", "quest_turnins.json", "SCIONBOOK_MEMORY.md",
                  "SCIONBOOK_DAILY_WEEKLY_CHECKLIST.md")
ALLOWED_TEMPLATES = {"templates/SCIONBOOK_MEMORY.md", "templates/SCIONBOOK_DAILY_WEEKLY_CHECKLIST.md"}
MIN_TERM = 4  # shorter terms match ordinary words and code


def git(*args, repo=None, **kwargs):
    return subprocess.run(["git", "-C", str(repo or REPO), *args], check=True, capture_output=True, **kwargs)


def local_terms(repo=None):
    """Identifying values from this checkout's own player files, if any."""
    repo = repo or REPO
    terms = set()
    for name, pick in (("scionbook.json", lambda d: [d.get("character_id"), d.get("name")]),
                       ("status.json", lambda d: [d.get("character_id"),
                                                  (d.get("character") or {}).get("name"),
                                                  *[r.get("name") for r in d.get("retainers") or []]])):
        path = Path(repo) / name
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            terms.update(str(v).strip() for v in pick(data) if v)
    return terms


def read_terms(path):
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()
    return {line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")}


def personal_paths(names):
    return sorted(n for n in names if n not in ALLOWED_TEMPLATES
                  and (any(PurePosixPath(n).name.startswith(p) for p in PERSONAL_NAMES)
                       or any(part in {".git", ".venv", "__pycache__", ".pytest_cache",
                                       "local", "raw", ".cache", "cache"}
                              or part.startswith((".env", ".scionbook-"))
                              for part in PurePosixPath(n).parts)))


def scan(files, terms):
    """Return (path, term) for every file containing a term, including in its path."""
    needles = sorted({t.lower() for t in terms if len(t) >= MIN_TERM})
    hits = []
    for path, content in files.items():
        haystack = path.lower() + "\n" + content.decode("utf-8", "ignore").lower()
        hits.extend((path, term) for term in needles if term in haystack)
    return hits


def committed_files(repo=None):
    archive = git("archive", "--format=tar", "HEAD", repo=repo).stdout
    files = {}
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar.getmembers():
            if member.isfile():
                files[member.name] = tar.extractfile(member).read()
            elif member.issym():
                files[member.name] = member.linkname.encode()
    return archive, files


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("destination", help="new, empty directory for the release repository")
    parser.add_argument("--deny", action="append", default=[], metavar="FILE",
                        help="extra identifying terms, one per line (repeatable)")
    parser.add_argument("--commit", action="store_true",
                        help="create the single initial commit with your git identity")
    args = parser.parse_args(argv)

    destination = Path(args.destination).resolve()
    if destination == REPO or REPO in destination.parents:
        parser.error("Export outside this repository.")
    if destination.exists() and any(destination.iterdir()):
        parser.error(f"{destination} is not empty.")
    if git("status", "--porcelain", "--untracked-files=no").stdout.strip():
        parser.error("Commit or stash tracked changes first; the export uses HEAD only.")

    archive, files = committed_files()
    blocked = personal_paths(files)
    terms = local_terms() | read_terms(REPO / DEFAULT_DENYLIST)
    for extra in args.deny:
        terms |= read_terms(extra)
    hits = scan(files, terms)
    if blocked or hits:
        for path in blocked:
            print(f"personal-state file tracked: {path}", file=sys.stderr)
        for path, _ in hits:
            print(f"identifying term found in: {path}", file=sys.stderr)
        sys.exit("Export refused; nothing was written.")
    if not terms:
        print("WARNING: no identifying terms found; add them to "
              f"{DEFAULT_DENYLIST} or pass --deny.", file=sys.stderr)

    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        if hasattr(tarfile, "data_filter"):
            tar.extractall(destination, filter="data")
        else:  # Python releases before the extraction filter; the archive is our own HEAD.
            tar.extractall(destination)
    git("init", "-q", "-b", "main", repo=destination)
    git("add", "-A", repo=destination)
    if args.commit:
        git("commit", "-q", "-m", "chore: initial public release", repo=destination)
    print(f"Exported {len(files)} files to {destination} with fresh history "
          f"({len(terms)} identifying terms checked). Review, then add a remote and push.")


if __name__ == "__main__":
    main()
