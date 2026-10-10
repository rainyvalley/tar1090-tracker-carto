#!/usr/bin/env python3
"""Container smoke test, run inside the built add-on image (ci.yml docker job).

Asserts the app comes up through its real run.sh entrypoint with a mounted
options.json and answers on the ingress port. tar1090 is unreachable here, so
the API must report degraded and serve no aircraft.
"""

import json
import sys
import urllib.request

BASE = 'http://127.0.0.1:5000'


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=5) as response:
        return response.status, json.loads(response.read().decode())


status, health = get('/api/health')
assert status == 200, status
assert health['status'] == 'degraded', health
assert health['tar1090_reachable'] is False, health
assert health['aircraft_count'] == 0, health

status, aircraft = get('/api/aircraft')
assert status == 200, status
assert aircraft['stale'] is True and aircraft['aircraft'] == [], aircraft

status, config = get('/api/config')
assert status == 200, status
assert config['tar1090_host'] == '192.0.2.100', config
assert config['tar1090_port'] == 8080, config

with urllib.request.urlopen(BASE + '/', timeout=5) as response:
    index = response.read().decode()
    assert response.status == 200 and 'Aircraft Tracker' in index, index[:200]

status, trails = get('/api/trails')
assert status == 200 and trails['stale'] is True, trails

with urllib.request.urlopen(BASE + '/ping', timeout=5) as response:
    assert response.read().decode() == 'pong'

print('container smoke test OK (degraded until tar1090 answers)')
sys.exit(0)