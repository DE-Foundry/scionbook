#!/usr/bin/env python3
"""Build a reviewed, committed source ZIP; retain current plus three previous versions."""
import argparse
import hashlib
import io
from pathlib import Path
import re
import tarfile
import zipfile

import export_release as source

# Published packages currently use stable SemVer; no prerelease/build channels.
VERSION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z")
RETAIN = 4


def version_key(value):
    if not VERSION.fullmatch(value):
        raise ValueError("Use a stable SemVer version: MAJOR.MINOR.PATCH, without leading zeros.")
    return tuple(map(int, value.split('.')))


def build(version, output, deny=()):
    key = version_key(version)
    repo = source.REPO
    if source.git('status', '--porcelain', '--untracked-files=no').stdout.strip():
        raise ValueError('Commit tracked changes first; releases use HEAD only.')
    archive, files = source.committed_files()
    terms = source.local_terms() | source.read_terms(repo / source.DEFAULT_DENYLIST)
    for path in deny:
        if not Path(path).is_file():
            raise ValueError('Requested denylist does not exist.')
        terms |= source.read_terms(path)
    if source.personal_paths(files) or source.scan(files, terms):
        raise ValueError('Privacy check failed; no archive written. Review tracked files locally.')
    output = Path(output)
    existing = []
    for path in output.glob('scionbook-*.zip'):
        candidate = path.name[len('scionbook-'):-4]
        if VERSION.fullmatch(candidate):
            existing.append((version_key(candidate), path))
    if any(old >= key for old, _ in existing):
        raise ValueError('Version must be newer than every retained release; never replace a release.')
    prefix = f'scionbook-{version}'
    # Materialize the one supported adapter link for extractors without symlink support.
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        modes = {}
        for member in tar.getmembers():
            if member.issym():
                if member.name != '.claude/skills' or member.linkname != '../.agents/skills':
                    raise ValueError('Unsupported symlink in release.')
                files.pop(member.name)
                for name, data in list(files.items()):
                    if name.startswith('.agents/skills/'):
                        files['.claude/skills/' + name[len('.agents/skills/'):]] = data
            elif not (member.isfile() or member.isdir()):
                raise ValueError('Unsupported archive entry.')
            modes[member.name] = member.mode
    if 'VERSION' in files:
        raise ValueError('VERSION is generated for the package; remove the tracked collision.')
    files['VERSION'] = (version + '\n').encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as package:
        for name, data in sorted(files.items()):
            entry = zipfile.ZipInfo(f'{prefix}/{name}')
            entry.create_system = 3
            entry.external_attr = (0o100000 | modes.get(name, 0o644)) << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            package.writestr(entry, data)
    payload = buffer.getvalue()
    output.mkdir(parents=True, exist_ok=True)
    target = output / f'{prefix}.zip'
    checksum = target.with_suffix('.zip.sha256')
    if checksum.exists():
        raise ValueError('Checksum already exists; refusing to overwrite.')
    with target.open('xb') as handle:
        handle.write(payload)
    checksum.write_text(f'{hashlib.sha256(payload).hexdigest()}  {target.name}\n')
    # Prune only recognized older packages, after both new outputs were written.
    for _, old in sorted(existing, reverse=True)[RETAIN - 1:]:
        old.unlink()
        old.with_suffix('.zip.sha256').unlink(missing_ok=True)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version')
    parser.add_argument('--output', default='local/releases')
    parser.add_argument('--deny', action='append', default=[])
    args = parser.parse_args()
    try:
        print(build(args.version, args.output, args.deny))
    except ValueError as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
