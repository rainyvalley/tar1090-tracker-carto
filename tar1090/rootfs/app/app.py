#!/usr/bin/env python3

import os
import re
import sys
import json
import time
import signal
import ipaddress
import logging
import threading
from collections import deque
from datetime import datetime
from urllib.parse import urlsplit

import requests
from flask import Flask, jsonify, request, send_from_directory

# Create Flask app with support for Home Assistant ingress. static_url_path=''
# serves every file under the static folder from the site root.
app = Flask(__name__, static_folder='/var/www/tar1090', static_url_path='')

# Configure logging. Per-poll and per-request messages are DEBUG so the
# Supervisor log is not flooded; connection changes are logged at INFO/WARNING.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger('werkzeug').setLevel(logging.WARNING)

# Configuration from environment variables with options.json fallback
OPTIONS_PATH = '/data/options.json'
SECRET_KEYS = {'CARTO_API_KEY'}
_options = None


def _load_options():
    """Read /data/options.json once; an unreadable file counts as empty."""
    global _options
    if _options is None:
        try:
            with open(OPTIONS_PATH, 'r') as f:
                loaded = json.load(f)
            _options = loaded if isinstance(loaded, dict) else {}
        except (OSError, ValueError):
            _options = {}
    return _options


def get_config_value(key, default, value_type=str):
    """Get a configuration value from env vars or options.json.

    Missing, empty or null values and values that fail type conversion fall
    back to the default.
    """
    value = os.getenv(key.upper())
    source = 'environment'
    if value is None or value in ('', 'null'):
        value = _load_options().get(key.lower())
        source = 'options.json'
    if value is None or value in ('', 'null'):
        return default

    try:
        if value_type == int:
            value = int(value)
        elif value_type == float:
            value = float(value)
        elif value_type == bool:
            value = str(value).lower() in ('true', '1', 'yes', 'on')
        else:
            value = str(value)
    except (TypeError, ValueError):
        logger.warning(f"Invalid value for {key} from {source}: {value!r}; using default {default!r}")
        return default

    shown = '<set>' if key.upper() in SECRET_KEYS else value
    logger.info(f"Read {key} from {source}: {shown}")
    return value


_HOSTNAME_RE = re.compile(r'[A-Za-z0-9._-]+|[0-9A-Fa-f:.]+')


def build_tar1090_url(raw_host, port):
    """Build the aircraft.json URL from the configured host and port.

    Accepts a bare host as well as values such as "http://host" or
    "host:8080" that users commonly paste in; a port in the host wins.
    """
    raw = str(raw_host or '').strip()
    try:
        host, host_port = str(ipaddress.IPv6Address(raw)), None  # bare IPv6
    except ValueError:
        try:
            parts = urlsplit(raw if '://' in raw else 'http://' + raw)
            host, host_port = parts.hostname, parts.port
        except ValueError:
            host, host_port = None, None

    if not host or not _HOSTNAME_RE.fullmatch(host):
        logger.error(f"tar1090_host {raw!r} is not a valid host name or IP address")
        host = raw
    elif raw != host:
        logger.warning(f"tar1090_host {raw!r} should be a bare host name or IP; using {host!r}")
    if host_port and host_port != port:
        logger.warning(f"Using port {host_port} from tar1090_host instead of tar1090_port {port}")
        port = host_port

    if ':' in host:  # IPv6 literal
        host = f"[{host}]"
    return f"http://{host}:{port}/data/aircraft.json"


TAR1090_HOST = get_config_value('TAR1090_HOST', '192.0.2.100')
TAR1090_PORT = get_config_value('TAR1090_PORT', 8080, int)
UPDATE_INTERVAL = max(1, get_config_value('UPDATE_INTERVAL', 1, int))
SHOW_HISTORY = get_config_value('SHOW_HISTORY', True, bool)
AUTO_CENTER = get_config_value('AUTO_CENTER', False, bool)
MAP_PROVIDER = get_config_value('MAP_PROVIDER', 'carto_dark')
CARTO_API_KEY = get_config_value('CARTO_API_KEY', '')
MAP_CENTER_LAT = get_config_value('MAP_CENTER_LAT', 54.7023, float)
MAP_CENTER_LON = get_config_value('MAP_CENTER_LON', -3.2765, float)
MAP_ZOOM = get_config_value('MAP_ZOOM', 8, int)
# Listener address and port. The add-on is reached through ingress on 5000;
# standalone runs (simple-start.sh) may override them.
BIND_HOST = get_config_value('BIND_HOST', '0.0.0.0')
PORT = get_config_value('WEB_PORT', 5000, int)

TAR1090_URL = build_tar1090_url(TAR1090_HOST, TAR1090_PORT)

# Upper bound on a single aircraft.json body. A busy feeder produces well
# under 1 MB; anything far larger is a misconfiguration (e.g. an aggregator).
MAX_RESPONSE_BYTES = 10 * 1024 * 1024
HISTORY_LENGTH = 100
# Data older than this is treated as stale: the API stops serving aircraft
# and health reports "degraded".
STALE_AFTER = max(10, 3 * UPDATE_INTERVAL + 5)

# Global variables to store aircraft data
aircraft_data = {"aircraft": [], "now": 0, "messages": 0}
aircraft_history = deque(maxlen=HISTORY_LENGTH)
last_success = None  # time.monotonic() of the last good fetch
data_lock = threading.Lock()


def sanitize_aircraft_data(data):
    """Return data if it looks like tar1090's aircraft.json, else None."""
    if not isinstance(data, dict) or not isinstance(data.get('aircraft'), list):
        return None
    data['aircraft'] = [a for a in data['aircraft'] if isinstance(a, dict)]
    return data


def fetch_aircraft_data():
    """Fetch aircraft data from tar1090. Returns (data, error)."""
    try:
        with requests.get(TAR1090_URL, timeout=5, stream=True) as response:
            response.raise_for_status()
            body = bytearray()
            for chunk in response.iter_content(chunk_size=65536):
                body += chunk
                if len(body) > MAX_RESPONSE_BYTES:
                    return None, f"response larger than {MAX_RESPONSE_BYTES} bytes"
        data = sanitize_aircraft_data(json.loads(body))
    except (requests.exceptions.RequestException, ValueError) as e:
        return None, str(e)
    if data is None:
        return None, "response is not a tar1090 aircraft.json object"
    return data, None


def data_age():
    """Seconds since the last successful fetch, or None if there was none."""
    return None if last_success is None else time.monotonic() - last_success


def data_is_stale():
    age = data_age()
    return age is None or age > STALE_AFTER


def update_aircraft_data():
    """Background thread to continuously update aircraft data"""
    global aircraft_data, last_success

    connected = None
    next_run = time.monotonic()
    while True:
        try:
            new_data, error = fetch_aircraft_data()
        except Exception as e:  # keep the poller alive whatever happens
            new_data, error = None, f"unexpected error: {e}"

        if new_data is not None:
            # Add timestamp for history tracking
            new_data['timestamp'] = datetime.now().isoformat()
            with data_lock:
                aircraft_data = new_data
                last_success = time.monotonic()
                if SHOW_HISTORY:
                    aircraft_history.append(new_data)
            count = len(new_data['aircraft'])
            if connected is not True:
                logger.info(f"Receiving data from tar1090 at {TAR1090_URL} ({count} aircraft)")
            logger.debug(f"Updated aircraft data: {count} aircraft")
            connected = True
        else:
            if connected is not False:
                logger.warning(f"Cannot get data from tar1090 at {TAR1090_URL}: {error}")
            logger.debug(f"Fetch failed: {error}")
            connected = False

        # Fixed-rate schedule; if a slow fetch overran, start again right away
        next_run += UPDATE_INTERVAL
        delay = next_run - time.monotonic()
        if delay < 0:
            next_run = time.monotonic()
            delay = 0
        time.sleep(delay)


# Content Security Policy for the UI. Basemaps load from Carto (vector style,
# tiles, sprites, fonts) and Esri; MapLibre runs its tile workers from blob:
# URLs. Inline styles are needed for Leaflet markers and popups. No
# frame-ancestors / X-Frame-Options: the page is embedded by HA ingress.
CONTENT_SECURITY_POLICY = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob: https://*.cartocdn.com https://server.arcgisonline.com",
    "connect-src 'self' https://*.cartocdn.com",
    "worker-src 'self' blob:",
    "child-src blob:",
    "font-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'none'",
])


@app.after_request
def add_security_headers(response):
    response.headers.setdefault('Content-Security-Policy', CONTENT_SECURITY_POLICY)
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    return response


# API routes - both with and without /api/ prefix for compatibility
@app.route('/aircraft', methods=['GET'])
@app.route('/api/aircraft', methods=['GET'])
def get_aircraft():
    """Get current aircraft data (no aircraft while tar1090 is unreachable)"""
    with data_lock:
        stale = data_is_stale()
        data = dict(aircraft_data, stale=stale)
    if stale:
        data['aircraft'] = []
    return jsonify(data)


@app.route('/aircraft/history', methods=['GET'])
@app.route('/api/aircraft/history', methods=['GET'])
@app.route('/api/history', methods=['GET'])
def get_aircraft_history():
    """Get aircraft history data; ?limit=N returns only the newest N records"""
    if not SHOW_HISTORY:
        return jsonify({"error": "History not enabled"}), 400

    limit = request.args.get('limit', type=int)
    with data_lock:
        history = list(aircraft_history)
    if limit is not None:
        history = history[-limit:] if limit > 0 else []
    return jsonify({"history": history})


@app.route('/config', methods=['GET'])
@app.route('/api/config', methods=['GET'])
def get_config():
    """Get addon configuration.

    carto_api_key is returned on purpose: the browser needs it to request
    Carto tiles, so it is a client-side key (restrict it by domain at Carto).
    """
    return jsonify({
        "tar1090_host": TAR1090_HOST,
        "tar1090_port": TAR1090_PORT,
        "update_interval": UPDATE_INTERVAL,
        "show_history": SHOW_HISTORY,
        "auto_center": AUTO_CENTER,
        "map_provider": MAP_PROVIDER,
        "carto_api_key": CARTO_API_KEY,
        "map_center_lat": MAP_CENTER_LAT,
        "map_center_lon": MAP_CENTER_LON,
        "map_zoom": MAP_ZOOM
    })


@app.route('/health', methods=['GET'])
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint: "degraded" while tar1090 data is stale"""
    with data_lock:
        stale = data_is_stale()
        age = data_age()
        count = 0 if stale else len(aircraft_data.get('aircraft', []))
        now = aircraft_data.get('now', 0)
    return jsonify({
        "status": "degraded" if stale else "healthy",
        "tar1090_reachable": not stale,
        "seconds_since_last_data": None if age is None else round(age, 1),
        "timestamp": datetime.now().isoformat(),
        "aircraft_count": count,
        "last_update": now
    })


@app.route('/stats', methods=['GET'])
@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get statistics about the service"""
    with data_lock:
        stale = data_is_stale()
        current_aircraft = [] if stale else aircraft_data.get('aircraft', [])

        # Calculate some basic stats
        aircraft_with_position = [a for a in current_aircraft if 'lat' in a and 'lon' in a]
        aircraft_with_callsign = [a for a in current_aircraft
                                  if isinstance(a.get('flight'), str) and a['flight'].strip()]

        stats = {
            "total_aircraft": len(current_aircraft),
            "aircraft_with_position": len(aircraft_with_position),
            "aircraft_with_callsign": len(aircraft_with_callsign),
            "last_update": aircraft_data.get('now', 0),
            "messages_total": aircraft_data.get('messages', 0),
            "history_records": len(aircraft_history) if SHOW_HISTORY else 0,
            "stale": stale
        }

    return jsonify(stats)


@app.route('/')
def index():
    """Serve the main page"""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/ping')
def ping():
    """Simple ping endpoint for ingress health check"""
    return "pong"


def _handle_sigterm(signum, frame):
    sys.exit(0)


if __name__ == '__main__':
    logger.info("Starting Tar1090 Aircraft Tracker API")
    logger.info(f"Polling tar1090 at {TAR1090_URL} every {UPDATE_INTERVAL}s")

    # Exit promptly on docker/Supervisor stop, also when running as PID 1
    signal.signal(signal.SIGTERM, _handle_sigterm)

    # Start background thread for data updates
    update_thread = threading.Thread(target=update_aircraft_data, daemon=True)
    update_thread.start()

    try:
        from waitress import serve
    except ImportError:
        serve = None

    if serve is not None:
        logger.info(f"Starting web server (waitress) on {BIND_HOST}:{PORT}")
        serve(app, host=BIND_HOST, port=PORT, threads=8)
    else:
        logger.warning("waitress is not installed; using Flask's development server")
        app.run(host=BIND_HOST, port=PORT, debug=False, threaded=True)
