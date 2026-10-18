#!/usr/bin/env python3
"""Fail closed before pushing files or commit metadata containing known private terms."""
import argparse
import sys
import subprocess

import export_release as source


def check(updates):
    tips = []
    for line in updates.splitlines():
        fields = line.split()
        if len(fields) != 4:
            raise ValueError('Invalid pre-push input.')
        if set(fields[1]) != {'0'}:
            tips.append(fields[1])
    if not tips:
        return
    terms = source.identifying_terms()
    if not terms:
        raise ValueError('No privacy terms configured. Populate ignored .scionbook-release-denylist before pushing.')
    # Scan every reachable commit, including files deleted before the pushed tip.
    # Do not trust stale remote-tracking refs to determine what is already public.
    commits = source.git('rev-list', *tips).stdout.decode().splitlines()
    checked = set()
    for tip in tips:
        if source.git('cat-file', '-t', tip).stdout.strip() == b'tag':
            if source.scan({'tag metadata': source.git('cat-file', '-p', tip).stdout}, terms):
                raise ValueError('Privacy check failed in tag metadata; review locally.')
    for commit in commits:
        metadata = source.git('show', '-s', '--format=%B%n%an%n%ae%n%cn%n%ce', commit).stdout
        if source.scan({'commit metadata': metadata}, terms):
            raise ValueError('Privacy check failed in commit metadata; review history locally.')
        listing = source.git('ls-tree', '-rz', '--full-tree', commit).stdout
        files = {}
        for entry in listing.split(b'\0'):
            if not entry:
                continue
            info, name = entry.split(b'\t', 1)
            _, kind, oid = info.split()
            if kind != b'blob':
                raise ValueError('Unsupported tracked entry; review history locally.')
            path = name.decode('utf-8', 'surrogateescape')
            files[path] = b''
            if oid not in checked:
                if source.scan({'blob': source.git('cat-file', 'blob', oid.decode()).stdout}, terms):
                    raise ValueError('Privacy check failed in reachable files; review history locally.')
                checked.add(oid)
        if source.personal_paths(files) or source.scan(files, terms):
            raise ValueError('Privacy check failed in reachable files; review history locally.')
    if source.scan({'pushed references': updates.encode()}, terms):
        raise ValueError('Privacy check failed in reference names; review locally.')


def install():
    configured = subprocess.run(['git', '-C', str(source.REPO), 'config', '--get', 'core.hooksPath'],
                                capture_output=True, check=False)
    if configured.returncode == 0 and configured.stdout.decode().strip() != '.githooks':
        raise ValueError('Existing core.hooksPath must be integrated manually; not overwritten.')
    hook = source.git('rev-parse', '--git-path', 'hooks/pre-push').stdout.decode().strip()
    if (source.REPO / hook).exists() and configured.returncode != 0:
        raise ValueError('Existing pre-push hook must be integrated manually; not overwritten.')
    source.git('config', '--local', 'core.hooksPath', '.githooks')
    print('Installed privacy pre-push hook for this checkout.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    try:
        if args.install:
            install()
        else:
            check(sys.stdin.read())
    except (ValueError, OSError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
