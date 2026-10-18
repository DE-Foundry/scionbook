"""Only conventional, single-line titles become release-driving squash subjects."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_pr_title import valid_title


@pytest.mark.parametrize('title', ['feat: add setup', 'fix(report): preserve unknowns',
                                  'feat!: change format', 'refactor(cache)!: change schema',
                                  'chore(deps): bump dependencies'])
def test_accepts_conventional_titles(title):
    assert valid_title(title)


@pytest.mark.parametrize('title', ['Update files', 'feat: ', 'feat:  leading space',
                                  'feat: first\nfix: second', 'feat: first\rsecond', 'misc: change'])
def test_rejects_nonconventional_titles(title):
    assert not valid_title(title)
