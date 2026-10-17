#!/usr/bin/env python3
"""Install and exercise a committed ZIP in a fresh environment, without player credentials."""
import os
from pathlib import Path
import subprocess
import tempfile
import venv
import zipfile

import build_release


def smoke():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        artifact = build_release.build('0.1.0', root / 'packages')
        with zipfile.ZipFile(artifact) as archive:
            archive.extractall(root / 'extracted')
        project = root / 'extracted/scionbook-0.1.0'
        for name in ['.agents/skills/setup/SKILL.md', '.claude/skills/setup/SKILL.md',
                     '.codex/config.toml', 'templates/SCIONBOOK_MEMORY.md', 'README.md']:
            if not (project / name).is_file():
                raise RuntimeError(f'Package is missing {name}')
        environment = root / 'environment'
        venv.create(environment, with_pip=True)
        python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        env = {k: v for k, v in os.environ.items() if k not in
               {'LODESTONE_COOKIE', 'GH_TOKEN', 'GITHUB_TOKEN', 'PYTHONPATH'}}
        subprocess.run([str(python), '-m', 'pip', 'install', '-r', 'requirements.txt'],
                       cwd=project, env=env, check=True)
        for script in ['scionbook_setup.py', 'scionbook_report.py', 'scionbook_quest_history.py',
                       'scionbook_quest_mats.py', 'scionbook_handoff.py']:
            subprocess.run([str(python), script, '--help'], cwd=project, env=env,
                           check=True, stdout=subprocess.DEVNULL)
        print('Extracted ZIP installs and all five CLI entry points start without Git or player data.')


if __name__ == '__main__':
    smoke()
