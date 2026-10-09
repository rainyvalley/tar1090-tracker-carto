#!/bin/bash
# Run the tracker without Home Assistant, from a checkout of this repository.
# Requires Python 3 with Flask and Requests (waitress is used if installed).
#
# The web server has no authentication. It listens on all interfaces by
# default; set BIND_HOST=127.0.0.1 to keep it to this machine.

set -euo pipefail

# Configuration
TAR1090_HOST=${TAR1090_HOST:-"192.0.2.100"}
TAR1090_PORT=${TAR1090_PORT:-"8080"}
UPDATE_INTERVAL=${UPDATE_INTERVAL:-"1"}
SHOW_HISTORY=${SHOW_HISTORY:-"true"}
MAP_CENTER_LAT=${MAP_CENTER_LAT:-"40.7128"}
MAP_CENTER_LON=${MAP_CENTER_LON:-"-74.0060"}
MAP_ZOOM=${MAP_ZOOM:-"8"}
AUTO_CENTER=${AUTO_CENTER:-"false"}
MAP_PROVIDER=${MAP_PROVIDER:-"carto_dark"}
CARTO_API_KEY=${CARTO_API_KEY:-""}
BIND_HOST=${BIND_HOST:-"0.0.0.0"}
WEB_PORT=${WEB_PORT:-"8099"}

# Best-effort LAN address for the startup message (Linux, then macOS)
if [ "$BIND_HOST" = "0.0.0.0" ]; then
    ADDR=$(hostname -I 2>/dev/null | awk '{print $1}' || true)
    [ -n "$ADDR" ] || ADDR=$(ipconfig getifaddr en0 2>/dev/null || true)
    [ -n "$ADDR" ] || ADDR=localhost
else
    ADDR=$BIND_HOST
fi

echo "Starting Tar1090 Aircraft Tracker..."
echo "Connecting to tar1090 at ${TAR1090_HOST}:${TAR1090_PORT}"
echo "Web interface will be at http://${ADDR}:${WEB_PORT}"

export TAR1090_HOST TAR1090_PORT UPDATE_INTERVAL SHOW_HISTORY
export MAP_CENTER_LAT MAP_CENTER_LON MAP_ZOOM AUTO_CENTER
export MAP_PROVIDER CARTO_API_KEY BIND_HOST WEB_PORT

# Start the Python app
cd "$(dirname "$0")/tar1090/rootfs/app" || exit 1
exec python3 app.py
