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
