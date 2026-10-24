"""getAircraftIconSize in script.js: helicopters (A7) must not get the biggest icon."""

import json
import pathlib
import re
import shutil
import subprocess

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'tar1090/rootfs/var/www/tar1090/script.js'


@pytest.mark.skipif(shutil.which('node') is None, reason='node not installed')
def test_icon_sizes():
    src = SCRIPT.read_text()
    m = re.search(r'getAircraftIconSize\(aircraft\) \{.*?\n    \}\n', src, re.S)
    assert m
    js = 'const f = function ' + m.group(0)[len('getAircraftIconSize'):] + ''';
    const out = {};
    for (const [k, v] of Object.entries({
        heli: {category: 'A7', type: ''}, heavy: {category: 'A5', type: ''},
        a380: {category: '', type: 'A388'}, plain: {category: '', type: ''}})) out[k] = f(v);
    console.log(JSON.stringify(out));'''
    res = subprocess.run(['node', '-e', js], capture_output=True, text=True, check=True)
    sizes = json.loads(res.stdout)
    assert sizes['heli'] < sizes['heavy'] < sizes['a380']
