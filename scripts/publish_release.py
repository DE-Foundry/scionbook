#!/usr/bin/env python3
"""Publish tested main commits as verified ZIP releases using GitHub CLI."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

import build_release as package


def git(*args):
    return package.source.git(*args).stdout.decode().strip()


def gh(*args):
    return subprocess.check_output(['gh', *args], text=True)


def releases():
    pages = json.loads(gh('api', f'repos/{os.environ["GITHUB_REPOSITORY"]}/releases',
                          '--paginate', '--slurp'))
    return [release for page in pages for release in page]


def stable(tag):
    return tag.startswith('v') and package.VERSION.fullmatch(tag[1:]) is not None


def next_version(previous, messages):
    if previous is None:
        return '0.1.0'
    major, minor, patch = package.version_key(previous)
    breaking = any(re.search(r'^[a-z]+(?:\([^\n)]+\))?!: ', msg)
                   or re.search(r'^BREAKING[ -]CHANGE: ', msg, re.M) for msg in messages)
    feature = any(re.match(r'^feat(?:\([^\n)]+\))?: ', msg) for msg in messages)
    if breaking and major:
        return f'{major + 1}.0.0'
    if breaking or feature:
        return f'{major}.{minor + 1}.0'
    if messages and all(re.match(r'^(?:ci|test|docs|chore)(?:\([^\n)]+\))?: ', msg) for msg in messages):
        return None
    return f'{major}.{minor}.{patch + 1}'


def ancestor(older, newer):
    result = subprocess.run(['git', '-C', str(package.source.REPO), 'merge-base', '--is-ancestor', older, newer], check=False)
    if result.returncode not in (0, 1):
        raise RuntimeError('Cannot determine release ancestry.')
    return result.returncode == 0


def plan(existing):
    head = git('rev-parse', 'HEAD')
    tags = [tag for tag in git('tag', '--list', 'v*').splitlines() if stable(tag)]
    latest = max(tags, key=lambda tag: package.version_key(tag[1:]), default=None)
    if latest:
        commit = git('rev-parse', latest + '^{commit}')
        if commit == head:
            return latest[1:]
        if ancestor(head, commit):
            return None  # A newer tested commit was already published.
        if not ancestor(commit, head):
            raise RuntimeError('Latest release tag is not an ancestor of this commit.')
    drafts = [r for r in existing if r['draft'] and stable(r['tag_name'])]
    if drafts:
        if len(drafts) != 1 or drafts[0]['target_commitish'] != head:
            raise RuntimeError('Unfinished release draft: rerun its original workflow before releasing new commits.')
        return drafts[0]['tag_name'][1:]
    revision = latest + '..HEAD' if latest else 'HEAD'
    messages = git('log', '--no-merges', '--format=%B%x00', revision).split('\x00')
    messages = [msg.strip() for msg in messages if msg.strip()]
    # Markdown skills/templates are executable product behavior too. Only explicitly
    # maintenance-scoped paths may be skipped for a maintenance-only commit range.
    if latest:
        changed = [name for name in git('diff', '--no-renames', '--name-only', '-z',
                                       latest, 'HEAD').split('\0') if name]
        if any(not (name.startswith(('.github/', 'tests/'))
                    or name in {'requirements-dev.txt', 'requirements-ci.txt'}) for name in changed):
            messages.append('fix: update shipped product files')
    return next_version(latest[1:] if latest else None, messages)


def expired(existing):
    published = [r for r in existing if not r['draft'] and not r['prerelease']
                 and stable(r['tag_name'])]
    return sorted(published, key=lambda r: package.version_key(r['tag_name'][1:]),
                  reverse=True)[package.RETAIN:]


def release_notes(version):
    tags = [tag for tag in git('tag', '--list', 'v*').splitlines()
            if stable(tag) and package.version_key(tag[1:]) < package.version_key(version)]
    previous = max(tags, key=lambda tag: package.version_key(tag[1:]), default=None)
    revision = previous + '..HEAD' if previous else 'HEAD'
    subjects = git('log', '--no-merges', '--format=%s', '--reverse', revision).splitlines()
    notes = (f'Scionbook {version}\n\n'
             'Requires Python 3.10+ and installation of requirements.txt. See '
             'docs/installation.md in the ZIP for setup, updates, and private backups.\n\n'
             '## Changes\n\n' + ''.join(f'- {subject}\n' for subject in subjects))
    changed = git('diff', '--name-only', previous, 'HEAD').splitlines() if previous else git(
        'ls-tree', '-r', '--name-only', 'HEAD').splitlines()
    appendix = package.source.REPO / 'RELEASE_NOTES.md'
    if 'RELEASE_NOTES.md' in changed and appendix.is_file():
        notes += '\n## Compatibility and migration\n\n' + appendix.read_text(encoding='utf-8')
    check_notes(notes)
    return notes


def check_notes(notes):
    if package.source.scan({'release notes': notes.encode('utf-8')}, package.source.identifying_terms()):
        raise ValueError('Privacy check failed in release notes; no publication attempted.')


def verify(tag, expected, compare_build=True):
    """Check hosted integrity; compare unpublished drafts to the tested build as well."""
    with tempfile.TemporaryDirectory() as directory:
        gh('release', 'download', tag, '--dir', directory,
           '--pattern', expected.name, '--pattern', expected.name + '.sha256')
        downloaded = Path(directory) / expected.name
        digest = hashlib.sha256(downloaded.read_bytes()).hexdigest()
        checksum = downloaded.with_suffix('.zip.sha256').read_text().split()
        if (checksum != [digest, expected.name]
                or (compare_build and digest != hashlib.sha256(expected.read_bytes()).hexdigest())):
            raise RuntimeError('Release download verification failed; no older releases removed.')


def publish():
    existing = releases()
    version = plan(existing)
    if version is None:
        print('Skipping superseded commit or maintenance-only changes.')
        return
    tag = 'v' + version
    matching = next((r for r in existing if r['tag_name'] == tag), None)
    if matching and matching['draft'] and matching['target_commitish'] != git('rev-parse', 'HEAD'):
        raise RuntimeError('Draft target does not match the tested commit.')
    if matching and matching['prerelease']:
        raise RuntimeError('Stable version collides with a prerelease.')
    with tempfile.TemporaryDirectory() as directory:
        artifact = Path(directory) / f'scionbook-{version}.zip'
        if not matching or matching['draft']:
            artifact = package.build(version, directory)
            if matching:
                check_notes(matching.get('body') or '')
            if not matching:
                notes = Path(directory) / 'notes.md'
                notes.write_text(release_notes(version), encoding='utf-8')
                gh('release', 'create', tag, '--draft', '--target', git('rev-parse', 'HEAD'),
                   '--title', f'Scionbook {version}', '--notes-file', str(notes))
            gh('release', 'upload', tag, str(artifact), str(artifact.with_suffix('.zip.sha256')),
               '--clobber')  # Only unpublished drafts may be repaired.
            verify(tag, artifact)
            gh('release', 'edit', tag, '--draft=false', '--latest')
        # Published ZIPs need not match a rebuild using a different zlib version.
        verify(tag, artifact, False)
        confirmed = releases()
        if not any(r['tag_name'] == tag and not r['draft'] for r in confirmed):
            raise RuntimeError('Publication could not be confirmed.')
        for release in expired(confirmed):
            # Deliberately omit --cleanup-tag: source tags remain as version history.
            gh('release', 'delete', release['tag_name'], '--yes')
        print(f'Published and verified {tag}; retained current plus three previous releases.')


if __name__ == '__main__':
    if (os.environ.get('GITHUB_REF') != 'refs/heads/main'
            or os.environ.get('GITHUB_EVENT_NAME') not in ('push', 'workflow_dispatch')):
        raise SystemExit('Publication is restricted to main push/manual workflow runs.')
    publish()
