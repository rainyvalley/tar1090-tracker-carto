#!/usr/bin/env python3
"""Deliverability check for tar1090/config.yaml (AGENTS.md "already-shipped trap").

The Home Assistant Supervisor compares the version *string* in config.yaml;
commits below the last bump are invisible to it. This check verifies, per
situation:

- tag push:      the config version equals the pushed tag, and both CHANGELOG.md
                 files have a `## [<version>]` section for it.
- push to main:  the add-on sources under tar1090/rootfs must not be newer than
                 the last config.yaml bump (the deliverability rule), and a bump
                 in the checked-out commit must carry a version newer than every
                 existing v* tag.
- pull request:  same as push, evaluated on the merge commit.

Runs in ci.yml (push + pull_request) and in release.yml before the release.
Exits 1 with `::error::` annotations; never touches the working tree.
"""

import os
import re
import subprocess
import sys

CONFIG = 'tar1090/config.yaml'
ROOTFS = 'tar1090/rootfs'
CHANGELOGS = ('CHANGELOG.md', 'tar1090/CHANGELOG.md')
SEMVER_RE = re.compile(r'^(\d+)\.(\d+)\.(\d+)$')


def git(*args):
    result = subprocess.run(['git', *args], capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"::error::git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def config_version():
    with open(CONFIG, 'r', encoding='utf-8') as f:
        match = re.search(r'^version: "([^"]+)"', f.read(), re.MULTILINE)
    if not match:
        sys.exit(f"::error::{CONFIG} has no 'version: \"x.y.z\"' line")
    return match.group(1)


def newest_tag():
    tags = [t[1:] for t in git('tag', '--list').splitlines() if re.match(r'^v\d', t)]
    tags = [t for t in tags if SEMVER_RE.match(t)]
    if not tags:
        return None
    return max(tags, key=lambda t: tuple(map(int, t.split('.'))))


def head_touched_config():
    return CONFIG in git('show', '--name-only', '--pretty=format:', 'HEAD').splitlines()


def fail(*messages):
    for message in messages:
        print(f'::error::{message}')
    sys.exit(1)


def tag_mode(ref_name):
    version = config_version()
    tag_version = ref_name[1:]  # 'v1.3.1' -> '1.3.1'
    if version != tag_version:
        fail(f'{CONFIG} says version {version} but the pushed tag is v{tag_version}. '
             f'Tag push rejected: re-tag only after ./scripts/release.sh bumped the version.')

    for changelog in CHANGELOGS:
        if f'## [{version}]' not in git('show', f'HEAD:{changelog}'):
            fail(f'{changelog} has no "## [{version}]" section; releases carry their notes')
    print(f'version {version} matches tag v{tag_version} with changelog sections')
    return 0


def push_mode():
    version = config_version()
    if not SEMVER_RE.match(version):
        fail(f'{CONFIG} version {version!r} is not x.y.z')

    bump_ts = int(git('log', '-1', '--format=%ct', '--', CONFIG) or 0)
    rootfs_ts = int(git('log', '-1', '--format=%ct', '--', ROOTFS) or 0)
    bumped_in_head = head_touched_config()

    # Deliverability: sources changed after the last bump are unreachable.
    if rootfs_ts > bump_ts and not bumped_in_head:
        fail(f'{CONFIG} still says {version}, but code under {ROOTFS} changed after '
             f'the last version bump; HA would keep serving {version}. Bump the '
             f'version (./scripts/release.sh) before pushing.')

    newest = newest_tag()
    if bumped_in_head and newest is not None:
        head = tuple(map(int, version.split('.')))
        if head <= tuple(map(int, newest.split('.'))):
            fail(f'{CONFIG} is changed in this commit but {version} is not newer than '
                 f'the newest tag {newest}; a bump must raise the version so HA '
                 f'sees an update.')

    for changelog in CHANGELOGS:
        if f'## [{version}]' not in git('show', f'HEAD:{changelog}'):
            fail(f'{changelog} has no "## [{version}]" section for the shipped version')
    if newest and version <= newest and not bumped_in_head:
        print(f'note: {CONFIG} ({version}) equals/ships below newest tag {newest}; '
              f'{ROOTFS} is unchanged since the bump, so this is deliverable')
    print(f'config version {version} is deliverable (rootfs <= config bump, '
          f'changelog sections present)')
    return 0


def main():
    event = os.environ.get('GITHUB_EVENT_NAME', '')
    ref_name = os.environ.get('GITHUB_REF_NAME', '')
    if event == 'push' and os.environ.get('GITHUB_REF_TYPE') == 'tag' \
            and SEMVER_RE.match(ref_name[1:] if ref_name.startswith('v') else ''):
        return tag_mode(ref_name)
    return push_mode()


if __name__ == '__main__':
    sys.exit(main())