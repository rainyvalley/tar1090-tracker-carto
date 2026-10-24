"""Tests for app.sanitize_aircraft_data."""

import app


def test_valid_data_passes_through():
    data = {"aircraft": [{"hex": "a1b2c3"}], "now": 1, "messages": 2}
    assert app.sanitize_aircraft_data(data) is data


def test_non_dict_entries_are_filtered():
    data = {"aircraft": [{"hex": "a1b2c3"}, "junk", 5, None]}
    assert app.sanitize_aircraft_data(data)["aircraft"] == [{"hex": "a1b2c3"}]


def test_non_dict_data_rejected():
    assert app.sanitize_aircraft_data(None) is None
    assert app.sanitize_aircraft_data([]) is None
    assert app.sanitize_aircraft_data("aircraft.json") is None


def test_missing_aircraft_key_rejected():
    assert app.sanitize_aircraft_data({"now": 1}) is None


def test_aircraft_not_a_list_rejected():
    assert app.sanitize_aircraft_data({"aircraft": {}}) is None
    assert app.sanitize_aircraft_data({"aircraft": "many"}) is None


def test_bad_hex_records_are_dropped():
    data = {"aircraft": [{"hex": "a1b2c3"}, {"hex": "bad"}, {"hex": 5}, {"lat": 1.0},
                         {"hex": "~a1b2c3"}, {"hex": "ZZZZZZ"}]}
    assert [a["hex"] for a in app.sanitize_aircraft_data(data)["aircraft"]] == ["a1b2c3", "~a1b2c3"]


def test_bad_position_is_removed_but_aircraft_kept():
    data = {"aircraft": [
        {"hex": "a1b2c3", "lat": 95, "lon": 1.0},
        {"hex": "a1b2c4", "lat": "x", "lon": 1.0},
        {"hex": "a1b2c5", "lat": 10.0, "lon": 181},
        {"hex": "a1b2c6", "lat": True, "lon": 1.0},
        {"hex": "a1b2c7", "lat": 10.0, "lon": 20.0},
    ]}
    out = app.sanitize_aircraft_data(data)["aircraft"]
    assert [a["hex"] for a in out] == ["a1b2c3", "a1b2c4", "a1b2c5", "a1b2c6", "a1b2c7"]
    assert all("lat" not in a and "lon" not in a for a in out[:4])
    assert out[4]["lat"] == 10.0
