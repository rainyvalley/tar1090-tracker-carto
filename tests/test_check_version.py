"""Tests for .github/scripts/check_version.py against throwaway git repos."""

import importlib.util
import os
import subprocess

import pytest

SCRIPT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '.github', 'scripts', 'check_version.py'))

spec = importlib.util.spec_from_file_location('check_version', SCRIPT)
check_version = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_version)


def run(*args):
    subprocess.run(['git', *args], check=True, capture_output=True)


def write(path, text):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A repo on main with config.yaml at 1.0.0 and a file to change."""
    monkeypatch.chdir(tmp_path)
    for var in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE'):
        monkeypatch.delenv(var, raising=False)
    run('init', '-q', '-b', 'main')
    run('config', 'user.email', 'test@example.com')
    run('config', 'user.name', 'test')
    run('config', 'commit.gpgsign', 'false')
    write(check_version.CONFIG, 'version: "1.0.0"\n')
    write('other.txt', 'a\n')
    run('add', '.')
    run('commit', '-q', '-m', 'init')
    return tmp_path


def test_head_touched_config_plain_commit(repo):
    write(check_version.CONFIG, 'version: "1.0.1"\n')
    run('commit', '-q', '-am', 'bump')
    assert check_version.head_touched_config() is True


def test_head_untouched_config_plain_commit(repo):
    write('other.txt', 'b\n')
    run('commit', '-q', '-am', 'change')
    assert check_version.head_touched_config() is False


def test_head_touched_config_root_commit(repo):
    assert check_version.head_touched_config() is True


def test_head_touched_config_merge_commit(repo):
    """A PR bump is seen on the merge commit CI checks out for the PR."""
    run('checkout', '-q', '-b', 'pr')
    write(check_version.CONFIG, 'version: "1.0.1"\n')
    run('commit', '-q', '-am', 'bump')
    run('checkout', '-q', 'main')
    write('other.txt', 'b\n')
    run('commit', '-q', '-am', 'base moves on')
    run('merge', '-q', '--no-ff', 'pr', '-m', 'merge')
    assert check_version.head_touched_config() is True


def ship(version):
    """Commit a bump to version with changelog sections, tagged v<version>."""
    write(check_version.CONFIG, f'version: "{version}"\n')
    for changelog in check_version.CHANGELOGS:
        write(changelog, f'# Changelog\n\n## [{version}]\n')
    run('add', '.')
    run('commit', '-q', '-m', f'release {version}')
    run('tag', f'v{version}')


def test_note_compares_versions_numerically(repo, capsys):
    """1.10.0 is newer than 1.9.0, not "below" it as strings would say."""
    ship('1.9.0')
    ship('1.10.0')
    run('tag', '-d', 'v1.10.0')  # newest tag is now v1.9.0
    write('other.txt', 'b\n')
    run('commit', '-q', '-am', 'docs only')
    assert check_version.push_mode() == 0
    assert 'ships below newest tag' not in capsys.readouterr().out


def test_note_when_config_equals_newest_tag(repo, capsys):
    ship('1.9.0')
    write('other.txt', 'b\n')
    run('commit', '-q', '-am', 'docs only')
    assert check_version.push_mode() == 0
    assert 'equals/ships below newest tag 1.9.0' in capsys.readouterr().out
