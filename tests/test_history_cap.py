"""History snapshots are rate limited and size capped."""

import time

import pytest

import app



def _poll_once(monkeypatch, aircraft):
    data = {"aircraft": aircraft, "now": 1, "messages": 1}
    monkeypatch.setattr(app, 'fetch_aircraft_data', lambda: (data, None))

    def stop(_):
        raise SystemExit

    monkeypatch.setattr(app.time, 'sleep', stop)
    with pytest.raises(SystemExit):
        app.update_aircraft_data()


@pytest.mark.usefixtures('reset_state_fixture')
def test_history_gets_one_snapshot_per_spacing(monkeypatch):
    monkeypatch.setattr(app, 'last_history', None)
    _poll_once(monkeypatch, [{"hex": "a1b2c3"}])
    _poll_once(monkeypatch, [{"hex": "a1b2c3"}])  # immediately after: skipped
    assert len(app.aircraft_history) == 1
    monkeypatch.setattr(app, 'last_history', time.monotonic() - app.HISTORY_MIN_SPACING - 1)
    _poll_once(monkeypatch, [{"hex": "a1b2c3"}])
    assert len(app.aircraft_history) == 2


@pytest.mark.usefixtures('reset_state_fixture')
def test_oversized_feed_is_not_kept_in_history(monkeypatch):
    monkeypatch.setattr(app, 'last_history', None)
    many = [{"hex": "%06x" % i} for i in range(app.HISTORY_MAX_AIRCRAFT + 1)]
    _poll_once(monkeypatch, many)
    assert len(app.aircraft_history) == 0
