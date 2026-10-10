"""Smoke tests of the Flask routes through the test client."""

import time

import pytest

from conftest import feed_aircraft

import app


def test_ping(client):
    resp = client.get('/ping')
    assert resp.status_code == 200
    assert resp.data == b'pong'


def test_index_served(client):
    resp = client.get('/')
    assert resp.status_code == 200
    assert b'Aircraft Tracker' in resp.data


def test_security_headers(client):
    resp = client.get('/ping')
    assert resp.headers['Content-Security-Policy'].startswith("default-src 'self'")
    assert resp.headers['X-Content-Type-Options'] == 'nosniff'
    assert resp.headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'


@pytest.mark.usefixtures('reset_state_fixture')
def test_aircraft_stale_while_no_data(client):
    resp = client.get('/api/aircraft')
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['stale'] is True
    assert body['aircraft'] == []


@pytest.mark.usefixtures('reset_state_fixture')
def test_aircraft_served_when_fresh(client):
    feed_aircraft([{"hex": "a1b2c3", "lat": 54.0, "lon": -1.0}])
    for route in ('/api/aircraft', '/aircraft'):
        body = client.get(route).get_json()
        assert body['stale'] is False
        assert [a['hex'] for a in body['aircraft']] == ['a1b2c3']


@pytest.mark.usefixtures('reset_state_fixture')
def test_aircraft_empty_once_stale(client):
    feed_aircraft([{"hex": "a1b2c3", "lat": 54.0, "lon": -1.0}])
    app.last_success = time.monotonic() - (app.STALE_AFTER + 1)
    body = client.get('/api/aircraft').get_json()
    assert body['stale'] is True
    assert body['aircraft'] == []


@pytest.mark.usefixtures('reset_state_fixture')
def test_health_fresh(client):
    feed_aircraft([{"hex": "a1b2c3", "lat": 54.0, "lon": -1.0}])
    body = client.get('/api/health').get_json()
    assert body['status'] == 'healthy'
    assert body['tar1090_reachable'] is True
    assert body['aircraft_count'] == 1
    assert body['seconds_since_last_data'] is not None


@pytest.mark.usefixtures('reset_state_fixture')
def test_health_degraded_when_stale(client):
    app.last_success = time.monotonic() - (app.STALE_AFTER + 1)
    body = client.get('/api/health').get_json()
    assert body['status'] == 'degraded'
    assert body['tar1090_reachable'] is False
    assert body['aircraft_count'] == 0
    assert body['seconds_since_last_data'] > app.STALE_AFTER


@pytest.mark.usefixtures('reset_state_fixture')
def test_health_never_seen_data(client):
    body = client.get('/api/health').get_json()
    assert body['status'] == 'degraded'
    assert body['seconds_since_last_data'] is None


@pytest.mark.usefixtures('reset_state_fixture')
def test_trails_stale_is_empty(client):
    feed_aircraft([{"hex": "a1b2c3", "lat": 54.0, "lon": -1.0},
                   {"hex": "a1b2c3", "lat": 54.01, "lon": -1.01}])
    app.last_success = time.monotonic() - (app.STALE_AFTER + 1)
    body = client.get('/api/trails').get_json()
    assert body == {"trails": {}, "stale": True}


@pytest.mark.usefixtures('reset_state_fixture')
def test_trails_fresh_multi_point_only(client):
    with app.data_lock:
        # Space the points past TRAIL_MIN_SPACING so both are kept.
        app.record_trails([{"hex": "a1b2c3", "lat": 54.0, "lon": -1.0}], 1000)
        app.record_trails(
            [{"hex": "a1b2c3", "lat": 54.01, "lon": -1.01},
             {"hex": "d4e5f6", "lat": 55.0, "lon": -2.0}], 1010)
        app.last_success = time.monotonic()  # fresh, so /api/trails serves them
    body = client.get('/api/trails').get_json()
    assert body['stale'] is False
    # d4e5f6 has one point only and is excluded.
    assert list(body['trails']) == ['a1b2c3']
    assert len(body['trails']['a1b2c3']) == 2


@pytest.mark.usefixtures('reset_state_fixture')
def test_config_endpoint_reports_module_config(client):
    body = client.get('/api/config').get_json()
    assert body['tar1090_host'] == app.TAR1090_HOST
    assert body['tar1090_port'] == app.TAR1090_PORT
    assert body['update_interval'] == app.UPDATE_INTERVAL
    assert body['map_provider'] == app.MAP_PROVIDER
    assert body['carto_api_key'] == app.CARTO_API_KEY
    assert body['carto_api_key'] == 'test-api-key'  # from tests/conftest.py


@pytest.mark.usefixtures('reset_state_fixture')
def test_stats_fresh(client):
    feed_aircraft([{"hex": "a1b2c3", "lat": 54.0, "lon": -1.0, "flight": "BA123"},
                   {"hex": "d4e5f6"}])
    body = client.get('/api/stats').get_json()
    assert body['total_aircraft'] == 2
    assert body['aircraft_with_position'] == 1
    assert body['aircraft_with_callsign'] == 1
    assert body['stale'] is False


@pytest.mark.usefixtures('reset_state_fixture')
def test_stats_stale_counts_are_zeroed(client):
    feed_aircraft([{"hex": "a1b2c3", "lat": 54.0, "lon": -1.0}])
    app.last_success = time.monotonic() - (app.STALE_AFTER + 1)
    body = client.get('/api/stats').get_json()
    assert body['total_aircraft'] == 0
    assert body['stale'] is True


@pytest.mark.usefixtures('reset_state_fixture')
def test_history_limit(client):
    feed_aircraft([{"hex": "a1b2c3", "lat": 54.0, "lon": -1.0}])
    time.sleep(0.01)
    feed_aircraft([{"hex": "d4e5f6", "lat": 55.0, "lon": -2.0}])
    full = client.get('/api/history').get_json()['history']
    assert len(full) == 2
    one = client.get('/api/history?limit=1').get_json()['history']
    assert len(one) == 1
    assert one[0]['aircraft'] == [{"hex": "d4e5f6", "lat": 55.0, "lon": -2.0}]
    none = client.get('/api/history?limit=0').get_json()['history']
    assert none == []