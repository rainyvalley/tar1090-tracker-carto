"""Tests for the stale-data logic: data_age, data_is_stale."""

import time

import pytest

import app


def test_no_data_ever_is_stale():
    assert app.last_success is None
    assert app.data_age() is None
    assert app.data_is_stale() is True


@pytest.mark.usefixtures('reset_state_fixture')
def test_recent_data_is_fresh():
    app.last_success = time.monotonic()
    assert app.data_age() is not None
    assert app.data_age() <= app.STALE_AFTER
    assert app.data_is_stale() is False


@pytest.mark.usefixtures('reset_state_fixture')
def test_old_data_is_stale():
    app.last_success = time.monotonic() - (app.STALE_AFTER + 1)
    assert app.data_is_stale() is True


@pytest.mark.usefixtures('reset_state_fixture')
def test_boundary_age_is_not_stale(monkeypatch):
    # Strictly-greater comparison: exactly STALE_AFTER seconds is still fresh.
    now = 1000.0
    monkeypatch.setattr(app.time, 'monotonic', lambda: now)
    app.last_success = now - app.STALE_AFTER
    assert app.data_is_stale() is False
    app.last_success = now - app.STALE_AFTER - 0.001
    assert app.data_is_stale() is True


def test_stale_after_tracks_update_interval():
    # max(10, 3 * UPDATE_INTERVAL + 5): 1 s poll gives the 10 s floor.
    assert app.STALE_AFTER >= 10
    assert app.STALE_AFTER == max(10, 3 * app.UPDATE_INTERVAL + 5)