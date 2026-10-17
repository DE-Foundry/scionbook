#!/usr/bin/env python3
"""Validate PR titles before they become squash commit subjects."""
import json
import os
from pathlib import Path
import re

PATTERN = re.compile(r'^(feat|fix|docs|test|refactor|chore|ci|build|perf|revert)(\([^\r\n()]+\))?!?: [^\s].*$')


def valid_title(title):
    return '\n' not in title and '\r' not in title and PATTERN.fullmatch(title) is not None


if __name__ == '__main__':
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text(encoding='utf-8'))
    if not valid_title(event['pull_request']['title']):
        raise SystemExit('Use a Conventional Commit PR title: type(optional-scope): summary')
    print('Conventional Commit PR title verified.')
