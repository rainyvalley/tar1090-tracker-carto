"""Tests for app.record_trails: dedupe, spacing, trimming, expiry, rejects."""

import time

import pytest

import app


def record(aircraft, now):
    app.record_trails(aircraft, now)
    return app.trails


def test_first_point_recorded():
    trails = record([{"hex": "abc", "lat": 54.0, "lon": -1.0}], 100)
    assert trails["abc"]["points"] == [[54.0, -1.0]]
    assert trails["abc"]["last_point"] == 100


def test_identical_point_deduped():
    record([{"hex": "abc", "lat": 54.0, "lon": -1.0}], 100)
    record([{"hex": "abc", "lat": 54.0, "lon": -1.0}], 110)
    assert app.trails["abc"]["points"] == [[54.0, -1.0]]


def test_moved_position_updates_last_point_within_spacing():
    record([{"hex": "abc", "lat": 54.0, "lon": -1.0}], 100)
    record([{"hex": "abc", "lat": 54.001, "lon": -1.0}], 103)
    points = app.trails["abc"]["points"]
    assert points == [[54.001, -1.0]]  # replaced, not appended
    assert app.trails["abc"]["last_point"] == 100


def test_new_point_after_spacing():
    record([{"hex": "abc", "lat": 54.0, "lon": -1.0}], 100)
    record([{"hex": "abc", "lat": 54.001, "lon": -1.0}], 103)
    record([{"hex": "abc", "lat": 54.002, "lon": -1.0}], 106)  # 6 s after t0
    points = app.trails["abc"]["points"]
    assert points == [[54.001, -1.0], [54.002, -1.0]]
    assert app.trails["abc"]["last_point"] == 106


def test_point_count_trimmed_to_max():
    now = 1000
    for i in range(app.TRAIL_MAX_POINTS + 10):
        record([{"hex": "abc",
                 "lat": 54.0 + i * 0.01, "lon": -1.0 + i * 0.01}], now + i * 10)
    points = app.trails["abc"]["points"]
    assert len(points) == app.TRAIL_MAX_POINTS
    assert points[0] == [round(54.0 + 10 * 0.01, 5), round(-1.0 + 10 * 0.01, 5)]


def test_unseen_trail_expires():
    now = 1000
    record([{"hex": "abc", "lat": 54.0, "lon": -1.0}], now)
    record([{"hex": "other", "lat": 54.5, "lon": -1.5}], now + app.TRAIL_EXPIRE + 1)
    assert "abc" not in app.trails
    assert "other" in app.trails


def test_seen_timestamp_touches_other_trails_nevermind():
    record([{"hex": "abc", "lat": 54.0, "lon": -1.0}], 100)
    record([{"hex": "abc", "lat": 54.0, "lon": -2.0}], 400)  # exactly at expiry: kept
    record([{"hex": "zz", "lat": 54.5, "lon": -1.5}], 500)
    assert "abc" in app.trails


def test_points_are_rounded():
    record([{"hex": "abc", "lat": 54.123456789, "lon": -1.987654321}], 100)
    assert app.trails["abc"]["points"] == [[54.12346, -1.98765]]


def test_hex_is_lowercased_and_stripped():
    record([{"hex": " A1B2C3 ", "lat": 54.0, "lon": -1.0}], 100)
    assert app.trails["a1b2c3"]["points"] == [[54.0, -1.0]]


def test_empty_or_missing_hex_rejected():
    record([{"lat": 54.0, "lon": -1.0}, {"hex": "", "lat": 54.0, "lon": -1.0},
            {"hex": "   ", "lat": 54.0, "lon": -1.0}], 100)
    assert app.trails == {}


def test_bad_positions_rejected():
    for aircraft in ({"hex": "abc"},                                  # no position
                     {"hex": "abc", "lat": 91, "lon": 0},             # lat out of range
                     {"hex": "abc", "lat": 0, "lon": 181},            # lon out of range
                     {"hex": "abc", "lat": True, "lon": 0},           # bool is not int
                     {"hex": "abc", "lat": "x", "lon": 0},            # non-numeric
                     {"hex": "abc", "lat": None, "lon": 0}):
        record([aircraft], 100)
        assert app.trails == {}, aircraft


@pytest.fixture
def reset_trails():
    app.trails.clear()
    yield
    app.trails.clear()


pytestmark = pytest.mark.usefixtures('reset_trails')