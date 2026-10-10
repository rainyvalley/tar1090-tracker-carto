"""Shared test setup for the tar1090 tracker app.

Module-level configuration in app.py reads the environment at import time,
so the variables must be set BEFORE app is imported. They are set here,
at pytest collection time (conftest.py is imported before test modules).
"""

import os
import sys
import time

# Realistic defaults so import-time config reads succeed everywhere.
os.environ.setdefault('TAR1090_HOST', '192.0.2.100')
os.environ.setdefault('TAR1090_PORT', '8080')
os.environ.setdefault('UPDATE_INTERVAL', '1')
os.environ.setdefault('SHOW_HISTORY', 'true')
os.environ.setdefault('AUTO_CENTER', 'false')
os.environ.setdefault('MAP_PROVIDER', 'carto_dark')
os.environ.setdefault('CARTO_API_KEY', 'test-api-key')
os.environ.setdefault('MAP_CENTER_LAT', '54.7023')
os.environ.setdefault('MAP_CENTER_LON', '-3.2765')
os.environ.setdefault('MAP_ZOOM', '8')
os.environ.setdefault('BIND_HOST', '127.0.0.1')
os.environ.setdefault('WEB_PORT', '5000')

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'tar1090', 'rootfs', 'app')))

import app  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture
def reset_options():
    """Point the options.json fallback at a nonexistent file and clear cache."""
    app.OPTIONS_PATH = os.path.join(app.STATIC_DIR, '..', 'no-such-options.json')
    app._options = None
    yield
    app._options = None


def reset_state():
    """Wipe shared data state (fresh, dataless, stale) between tests."""
    with app.data_lock:
        app.aircraft_data = {"aircraft": [], "now": 0, "messages": 0}
        app.aircraft_history.clear()
        app.trails.clear()
        app.last_success = None


@pytest.fixture
def reset_state_fixture():
    reset_state()
    yield
    reset_state()


def feed_aircraft(aircraft):
    """Fake a successful fetch: install current data and reset staleness."""
    now_ts = int(time.time())
    with app.data_lock:
        app.aircraft_data = {"aircraft": aircraft, "now": now_ts, "messages": 1}
        app.last_success = time.monotonic()
        app.record_trails(aircraft, app.last_success)
        if app.SHOW_HISTORY:
            app.aircraft_history.append(app.aircraft_data)


@pytest.fixture
def client():
    return app.app.test_client()