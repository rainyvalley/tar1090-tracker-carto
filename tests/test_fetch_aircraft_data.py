"""fetch_aircraft_data() against a fake upstream (no network)."""

import json

import app


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        yield self.body


class FakeSession:
    def __init__(self, body):
        self.body = body
        self.calls = 0

    def get(self, url, **kwargs):
        self.calls += 1
        return FakeResponse(self.body)


def test_polls_reuse_one_session(monkeypatch):
    session = FakeSession(json.dumps({'now': 1, 'aircraft': [{'hex': 'abc123'}]}).encode())
    monkeypatch.setattr(app, '_session', session)
    for _ in range(3):
        data, error = app.fetch_aircraft_data()
        assert error is None
        assert data['aircraft'] == [{'hex': 'abc123'}]
    assert session.calls == 3


def test_non_aircraft_json_rejected(monkeypatch):
    monkeypatch.setattr(app, '_session', FakeSession(b'[1, 2, 3]'))
    data, error = app.fetch_aircraft_data()
    assert data is None
    assert 'aircraft.json' in error
