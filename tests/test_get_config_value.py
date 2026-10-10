"""Tests for app.get_config_value: env vs options.json, fallbacks, secrets."""

import json
import logging

import pytest

import app


@pytest.fixture
def options_file(tmp_path, monkeypatch):
    """A fresh options.json for every test; app reads through its cache."""
    path = str(tmp_path / 'options.json')
    with open(path, 'w') as f:
        json.dump({}, f)
    monkeypatch.setattr(app, 'OPTIONS_PATH', path)
    monkeypatch.setattr(app, '_options', None)
    yield path
    monkeypatch.setattr(app, '_options', None)


def test_env_beats_options(monkeypatch, options_file):
    monkeypatch.setenv('TAR1090_HOST', 'from-env')
    assert app.get_config_value('tar1090_host', 'default') == 'from-env'


def test_options_fallback_used_when_env_missing(monkeypatch, options_file):
    monkeypatch.delenv('TAR1090_HOST', raising=False)
    with open(options_file, 'w') as f:
        json.dump({'tar1090_host': 'from-options'}, f)
    assert app.get_config_value('tar1090_host', 'default') == 'from-options'


def test_empty_env_falls_back_to_option(monkeypatch, options_file):
    monkeypatch.setenv('TAR1090_HOST', '')
    with open(options_file, 'w') as f:
        json.dump({'tar1090_host': 'from-options'}, f)
    assert app.get_config_value('tar1090_host', 'default') == 'from-options'


def test_options_are_cached(monkeypatch, options_file):
    monkeypatch.delenv('TAR1090_HOST', raising=False)
    with open(options_file, 'w') as f:
        json.dump({'tar1090_host': 'first'}, f)
    assert app.get_config_value('tar1090_host', 'default') == 'first'
    with open(options_file, 'w') as f:
        json.dump({'tar1090_host': 'changed'}, f)
    assert app.get_config_value('tar1090_host', 'default') == 'first'


def test_missing_everywhere_returns_default(monkeypatch, options_file):
    monkeypatch.delenv('TAR1090_HOST', raising=False)
    assert app.get_config_value('tar1090_host', 'default') == 'default'


def test_null_string_treated_as_missing(monkeypatch, options_file):
    monkeypatch.setenv('TAR1090_HOST', 'null')
    assert app.get_config_value('tar1090_host', 'default') == 'default'


def test_missing_options_file_is_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(app, 'OPTIONS_PATH', str(tmp_path / 'nope.json'))
    monkeypatch.setattr(app, '_options', None)
    monkeypatch.delenv('TAR1090_HOST', raising=False)
    assert app.get_config_value('tar1090_host', 'default') == 'default'


def test_bad_int_falls_back_to_default(monkeypatch, options_file, caplog):
    monkeypatch.setenv('TAR1090_PORT', 'not-a-number')
    with caplog.at_level(logging.WARNING):
        assert app.get_config_value('tar1090_port', 8080, int) == 8080
    assert any('Invalid value for tar1090_port' in r.getMessage() for r in caplog.records)


def test_bad_float_falls_back_to_default(monkeypatch, options_file):
    monkeypatch.setenv('MAP_CENTER_LAT', 'xyz')
    assert app.get_config_value('map_center_lat', 0.5, float) == 0.5


def test_bool_true_values(monkeypatch, options_file):
    for raw in ('true', '1', 'yes', 'on'):
        monkeypatch.setenv('SHOW_HISTORY', raw)
        assert app.get_config_value('show_history', False, bool) is True


def test_bool_false_values(monkeypatch, options_file):
    for raw in ('false', '0', 'no', 'off', 'anything'):
        monkeypatch.setenv('SHOW_HISTORY', raw)
        assert app.get_config_value('show_history', True, bool) is False


def test_int_accepted_from_options_json_float(monkeypatch, options_file):
    monkeypatch.delenv('TAR1090_PORT', raising=False)
    with open(options_file, 'w') as f:
        json.dump({'tar1090_port': 8080.0}, f)
    assert app.get_config_value('tar1090_port', 1, int) == 8080


def test_value_logged_plainly(monkeypatch, options_file, caplog):
    monkeypatch.setenv('TAR1090_HOST', '1.2.3.4')
    with caplog.at_level(logging.INFO):
        app.get_config_value('tar1090_host', 'default')
    assert any('Read tar1090_host from environment: 1.2.3.4' in r.getMessage()
               for r in caplog.records)


def test_secret_value_masked_in_log(monkeypatch, options_file, caplog):
    monkeypatch.setenv('CARTO_API_KEY', 'super-secret')
    with caplog.at_level(logging.INFO):
        app.get_config_value('carto_api_key', '', str)
    assert not any('super-secret' in r.getMessage() for r in caplog.records)
    assert any('<set>' in r.getMessage() for r in caplog.records)


def test_secret_default_not_masked_when_unset(monkeypatch, options_file):
    monkeypatch.delenv('CARTO_API_KEY', raising=False)
    assert app.get_config_value('carto_api_key', 'unset-marker') == 'unset-marker'