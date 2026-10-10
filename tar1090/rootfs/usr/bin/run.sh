#!/usr/bin/env bashio

# Read configuration straight from the options file the Supervisor writes.
# bashio::config goes through the Supervisor API, which newer bashio calls on
# a path this add-on is not granted ("Unable to access the API, forbidden").
CONFIG_PATH=/data/options.json
[ -r "$CONFIG_PATH" ] || bashio::exit.nok "Cannot read $CONFIG_PATH"

# Read all options in one jq pass instead of one jq process per key.
# @tsv turns null into "" (same as the old select(. != null) -> empty fallback)
# and separates fields with tabs, which read -r splits with a tab IFS.
IFS=$'\t' read -r TAR1090_HOST TAR1090_PORT UPDATE_INTERVAL SHOW_HISTORY \
    MAP_CENTER_LAT MAP_CENTER_LON MAP_ZOOM AUTO_CENTER \
    MAP_PROVIDER CARTO_API_KEY < <(jq -r '[
        .tar1090_host, .tar1090_port, .update_interval, .show_history,
        .map_center_lat, .map_center_lon, .map_zoom, .auto_center,
        .map_provider, .carto_api_key
    ] | @tsv' "$CONFIG_PATH")

bashio::log.info "Starting Tar1090 Aircraft Tracker with Ingress..."

# Export environment variables for Python app
# (Every option is logged by app.py's get_config_value(), so it is not repeated
# here. carto_api_key is optional: Carto vector maps still work without one.)
export TAR1090_HOST
export TAR1090_PORT
export UPDATE_INTERVAL
export SHOW_HISTORY
export MAP_CENTER_LAT
export MAP_CENTER_LON
export MAP_ZOOM
export AUTO_CENTER
export MAP_PROVIDER
export CARTO_API_KEY

# Start the Python app with ingress support. exec so it receives SIGTERM
# directly when the add-on is stopped.
cd /app || bashio::exit.nok "Cannot change to /app"
exec python3 app.py
