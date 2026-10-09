#!/usr/bin/env bashio

# Read configuration
TAR1090_HOST=$(bashio::config 'tar1090_host')
TAR1090_PORT=$(bashio::config 'tar1090_port')
UPDATE_INTERVAL=$(bashio::config 'update_interval')
SHOW_HISTORY=$(bashio::config 'show_history')
MAP_CENTER_LAT=$(bashio::config 'map_center_lat')
MAP_CENTER_LON=$(bashio::config 'map_center_lon')
MAP_ZOOM=$(bashio::config 'map_zoom')
AUTO_CENTER=$(bashio::config 'auto_center')
MAP_PROVIDER=$(bashio::config 'map_provider')
CARTO_API_KEY=$(bashio::config 'carto_api_key')

bashio::log.info "Starting Tar1090 Aircraft Tracker with Ingress..."
bashio::log.info "Configuration debug:"
bashio::log.info "TAR1090_HOST: ${TAR1090_HOST}"
bashio::log.info "TAR1090_PORT: ${TAR1090_PORT}"
bashio::log.info "UPDATE_INTERVAL: ${UPDATE_INTERVAL}"
bashio::log.info "MAP_PROVIDER: ${MAP_PROVIDER}"
if bashio::var.has_value "${CARTO_API_KEY}"; then
    bashio::log.info "CARTO_API_KEY: set"
else
    bashio::log.info "CARTO_API_KEY: not set (Carto vector maps still work without one)"
fi

# Export environment variables for Python app
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
