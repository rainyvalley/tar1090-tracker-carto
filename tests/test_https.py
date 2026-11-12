"""Opt-in HTTPS for standalone runs: warnings and a real TLS round trip."""

import os
import pathlib
import shutil
import socket
import ssl
import subprocess
import threading
import time
import urllib.request

import pytest

import app

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_no_warning_on_loopback_or_tls_or_addon():
    assert app.tls_warnings('127.0.0.1', '', '') == []
    assert app.tls_warnings('0.0.0.0', '/c', '/k') == []
    assert app.tls_warnings('0.0.0.0', '', '', addon=True) == []


def test_warns_on_exposed_plain_http():
    out = app.tls_warnings('0.0.0.0', '', '')
    assert len(out) == 1 and 'plain HTTP' in out[0]


def test_half_set_is_reported():
    assert 'both' in app.tls_warnings('127.0.0.1', '/c', '')[0]


def test_simple_start_resolves_relative_tls_paths(tmp_path):
    """The README's relative cert paths must survive the script's cd into app/."""
    stub_dir = tmp_path / 'bin'
    stub_dir.mkdir()
    stub = stub_dir / 'python3'
    stub.write_text('#!/bin/sh\nprintf "%s\\n%s\\n" "$WEB_TLS_CERT" "$WEB_TLS_KEY"\n')
    stub.chmod(0o755)
    env = dict(os.environ)
    env.update(PATH=f'{stub_dir}{os.pathsep}{env.get("PATH", "")}',
               WEB_TLS_CERT='certs/tracker.crt',
               WEB_TLS_KEY='certs/tracker.key')
    result = subprocess.run([str(ROOT / 'simple-start.sh')], cwd=ROOT, env=env,
                            capture_output=True, text=True, check=True)
    assert result.stdout.splitlines()[-2:] == [
        str(ROOT / 'certs/tracker.crt'), str(ROOT / 'certs/tracker.key')]


@pytest.mark.skipif(not shutil.which('openssl'), reason='openssl missing')
def test_serves_https_with_generated_cert(tmp_path):
    subprocess.run([str(ROOT / 'scripts' / 'make-cert.sh'), str(tmp_path)],
                   check=True, capture_output=True)
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    threading.Thread(
        target=app.serve_https,
        args=(app.app, '127.0.0.1', port,
              str(tmp_path / 'tracker.crt'), str(tmp_path / 'tracker.key')),
        daemon=True).start()
    ctx = ssl.create_default_context(cafile=str(tmp_path / 'tracker.crt'))
    for _ in range(50):
        try:
            with urllib.request.urlopen(f'https://localhost:{port}/ping',
                                        context=ctx, timeout=2) as r:
                assert r.read().decode() == 'pong'
            break
        except (urllib.error.URLError, ConnectionError):
            time.sleep(0.1)
    else:
        pytest.fail('HTTPS server never answered')
    # a plain HTTP request to the TLS port must not be served
    with pytest.raises(Exception):
        urllib.request.urlopen(f'http://127.0.0.1:{port}/ping', timeout=3)
