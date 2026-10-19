"""Tests for scripts/release.sh against a throwaway repo with a bare remote."""

import os
import shutil
import subprocess

SCRIPT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'scripts', 'release.sh'))

CHANGELOG = '# Changelog\n\n## [Unreleased]\n\n### Fixed\n- thing\n\n## [1.0.0] - 2026-01-01\n'


def git(cwd, *args):
    subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True)


def test_summary_backslashes_are_kept_literally(tmp_path):
    remote = tmp_path / 'remote.git'
    work = tmp_path / 'work'
    git(tmp_path, 'init', '--bare', '-b', 'main', str(remote))
    (work / 'tar1090').mkdir(parents=True)
    (work / 'scripts').mkdir()
    shutil.copy(SCRIPT, work / 'scripts' / 'release.sh')
    (work / 'tar1090' / 'config.yaml').write_text('version: "1.0.0"\n')
    for name in ('CHANGELOG.md', 'tar1090/CHANGELOG.md'):
        (work / name).write_text(CHANGELOG)
    git(work, 'init', '-b', 'main')
    git(work, 'config', 'user.email', 't@example.com')
    git(work, 'config', 'user.name', 'T')
    git(work, 'add', '.')
    git(work, 'commit', '-m', 'init')
    git(work, 'remote', 'add', 'origin', str(remote))

    summary = r'Fix C:\new\table and a\tb'
    subprocess.run(['bash', 'scripts/release.sh', '1.0.1', summary],
                   cwd=work, check=True, capture_output=True)

    for name in ('CHANGELOG.md', 'tar1090/CHANGELOG.md'):
        text = (work / name).read_text()
        assert '\n' + summary + '\n' in text
        assert '## [Unreleased]' in text and '- thing' in text
    assert 'version: "1.0.1"' in (work / 'tar1090/config.yaml').read_text()
