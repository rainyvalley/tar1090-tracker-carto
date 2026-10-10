"""Tests for app.build_tar1090_url against actual behavior."""

import app


def test_bare_ipv4_host():
    assert app.build_tar1090_url('192.0.2.100', 8080) == \
        'http://192.0.2.100:8080/data/aircraft.json'


def test_bare_hostname():
    assert app.build_tar1090_url('tar1090.local', 8080) == \
        'http://tar1090.local:8080/data/aircraft.json'


def test_whitespace_is_stripped():
    assert app.build_tar1090_url(' 192.0.2.100 ', '8080') == \
        'http://192.0.2.100:8080/data/aircraft.json'


def test_scheme_in_host_is_normalized():
    assert app.build_tar1090_url('http://192.0.2.100', 8080) == \
        'http://192.0.2.100:8080/data/aircraft.json'


def test_scheme_with_path_is_dropped():
    assert app.build_tar1090_url('http://192.0.2.100/data/aircraft.json', 8080) == \
        'http://192.0.2.100:8080/data/aircraft.json'


def test_port_in_host_wins():
    result = app.build_tar1090_url('http://192.0.2.100:9001', 8080)
    assert result == 'http://192.0.2.100:9001/data/aircraft.json'


def test_port_in_host_plain():
    result = app.build_tar1090_url('192.0.2.100:9001', 8080)
    assert result == 'http://192.0.2.100:9001/data/aircraft.json'


def test_port_in_host_same_as_port_is_no_change(capsys):
    # Same port spelled in the host: no override warning.
    app.build_tar1090_url('192.0.2.100:8080', 8080)
    out = capsys.readouterr().out
    assert 'instead of tar1090_port' not in out


def test_ipv6_bare_literal_is_bracketed():
    result = app.build_tar1090_url('2001:db8::1', 8080)
    assert result == 'http://[2001:db8::1]:8080/data/aircraft.json'


def test_ipv6_bracketed_literal():
    result = app.build_tar1090_url('[2001:db8::1]', 8080)
    assert result == 'http://[2001:db8::1]:8080/data/aircraft.json'


def test_invalid_host_falls_back_to_raw_value():
    # Unparseable: used verbatim after the error log, brackets skipped.
    result = app.build_tar1090_url('not a host!', 8080)
    assert result.endswith(':8080/data/aircraft.json')


def test_empty_host_falls_back_to_raw_value():
    result = app.build_tar1090_url('', 8080)
    assert result == 'http://:8080/data/aircraft.json'


def test_none_host_falls_back_to_raw_value():
    result = app.build_tar1090_url(None, 8080)
    assert result == 'http://:8080/data/aircraft.json'
