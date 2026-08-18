# Tar1090 Aircraft Tracker (Carto) — Home Assistant Add-on

A Home Assistant add-on that displays aircraft tracking data from a [tar1090](https://github.com/wiedehopf/tar1090) server on an interactive map with full dashboard integration.

> **This is a fork.** It is based on [`random-robbie/tar1090-tracker`](https://github.com/random-robbie/tar1090-tracker) by [random-robbie](https://github.com/random-robbie) and maintained independently. All original functionality is preserved; the differences are summarized below. See [Credits](#credits--license).

## What's different in this fork

This fork exists to fix two things that were broken or limiting in the upstream add-on:

- **Selectable Carto base maps (multiple providers).** Upstream defaulted to OpenStreetMap's public tile servers, which return **HTTP 403** for self-hosted apps under OSM's tile usage policy — so the map often failed to load. This fork adds a `map_provider` option and ships four working base layers you can pick as the default and switch between live from the map dropdown: **Carto Light**, **Carto Dark** (default), **Carto Voyager**, and **Esri Satellite**. The broken OpenStreetMap layer has been removed entirely so it can't be selected by mistake.
- **Flight links now use FlightAware instead of FlightRadar24.** Upstream linked aircraft to FlightRadar24's `/data/flights/<ident>` path, which only accepts airline flight numbers — so clicking a general-aviation tail number (e.g. `N76KA`) landed on a broken page. This fork links to FlightAware's `/live/flight/<ident>` endpoint, which resolves both registrations and callsigns, so tail-number lookups work.

See [CHANGELOG.md](CHANGELOG.md) for the detailed history.

## Features

- **Real-time Aircraft Tracking**: Connect to your tar1090 server and display live aircraft positions
- **Interactive Map**: Leaflet-based map with multiple Carto base layers plus satellite imagery
- **Aircraft Details**: Click an aircraft for callsign, altitude, speed, and track — with a working **View on FlightAware** link
- **Flight History**: Optional trail display showing aircraft movement history
- **Home Assistant Integration**: Seamless dashboard integration with ingress support
- **Responsive UI**: Dark theme interface optimized for Home Assistant
- **Configurable**: Customizable update intervals, map center, default base map, and display options

## Installation Methods

### Method 1: Home Assistant Add-on (Recommended)

1. Add this repository to your Home Assistant: **Settings → Add-ons → Add-on Store → ⋮ (top right) → Repositories**, then paste:

   ```
   https://github.com/rainyvalley/tar1090-tracker
   ```

2. Install the **"Tar1090 Aircraft Tracker (Carto)"** add-on
3. **Configure the add-on** on the "Configuration" tab:
   - **Tar1090 Host**: Your tar1090 server IP (e.g. `192.168.1.100`)
   - **Tar1090 Port**: Usually `8080` (default)
   - **Update Interval**: How often to fetch data, in seconds (1–60)
   - **Show History**: Enable/disable flight trails
   - **Map Center**: Your location coordinates for map centering
   - **Map Zoom**: Initial zoom level (1 = world view, 18 = street level)
   - **Auto Center**: Automatically center the map on aircraft
   - **Map Provider**: Default base map — `carto_light`, `carto_dark`, `carto_voyager`, or `esri_satellite`. Defaults to `carto_dark`. You can still switch layers live from the map's dropdown.
4. Click **Save**, then **Start** the add-on
5. The add-on appears in your sidebar with an airplane icon

> **Running it as a local add-on instead?** Drop the `tar1090/` folder into `/addons/tar1090-carto/` on your HA host, then **Settings → Add-ons → Add-on Store → ⋮ → Check for updates**. It will appear under **Local add-ons**. After any edit to files under `/addons`, use **Rebuild** (not just Restart).

### Method 2: Standalone Installation

If the add-on method has issues, you can run it standalone:

1. SSH into your Home Assistant system
2. Install dependencies:
   ```bash
   apk add --no-cache py3-flask py3-requests
   ```
3. Download and run:
   ```bash
   wget https://raw.githubusercontent.com/rainyvalley/tar1090-tracker/main/simple-start.sh
   chmod +x simple-start.sh
   TAR1090_HOST=192.168.1.175 ./simple-start.sh
   ```
4. Access at `http://your-ha-ip:8099`

## Flight information links

When you open an aircraft's popup, the **📡 View on FlightAware** link opens that aircraft on FlightAware. Ctrl+click or right-click on an aircraft marker opens the same page directly.

- If a **registration** (tail number) is known, the link points to `https://www.flightaware.com/live/flight/<registration>`
- Otherwise it falls back to the **callsign**: `https://www.flightaware.com/live/flight/<callsign>`

Because FlightAware's `/live/flight/` endpoint resolves both registrations and callsigns, general-aviation tail numbers such as `N76KA` resolve correctly — unlike the upstream FlightRadar24 `/data/flights/` path, which only accepts airline flight numbers.

## Adding to Home Assistant Dashboard

Once running (either method), integrate it into your HA dashboard.

### Option 1: Webpage Card
1. **Edit your dashboard**
2. **Add Card → Webpage Card**
3. **Settings:**
   - **URL:** `http://your-ha-ip:8099` (standalone) or the add-on's ingress URL
   - **Title:** `Aircraft Tracker`
   - **Aspect Ratio:** `16:9` (recommended)

### Option 2: Panel Dashboard
1. **Settings → Dashboards → Add Dashboard**
2. **Create new dashboard:**
   - **Type:** Panel (iframe)
   - **URL:** `http://your-ha-ip:8099`
   - **Title:** `Aircraft Tracker`
   - **Icon:** `mdi:airplane`
3. This creates a dedicated full-screen aircraft tracking tab

### Option 3: Native Map Card Integration

The Webpage Card (Option 1) is the best experience. If you'd rather have aircraft as Home Assistant entities on the built-in map card, add REST sensors and template device trackers to your `configuration.yaml`:

```yaml
# Aircraft data sensor
sensor:
  - platform: rest
    resource: http://192.168.1.212:8099/api/aircraft
    name: aircraft_data
    json_attributes:
      - aircraft
    value_template: "{{ value_json.aircraft | length }}"
    unit_of_measurement: "aircraft"
    scan_interval: 2

# Device trackers for each aircraft (repeat the pattern for aircraft_1 … aircraft_10)
device_tracker:
  - platform: template
    trackers:
      aircraft_1:
        friendly_name: "Aircraft 1"
        latitude_template: >
          {% set aircraft = state_attr('sensor.aircraft_data', 'aircraft') %}
          {% if aircraft and aircraft|length >= 1 and aircraft[0].lat %}
            {{ aircraft[0].lat }}
          {% endif %}
        longitude_template: >
          {% set aircraft = state_attr('sensor.aircraft_data', 'aircraft') %}
          {% if aircraft and aircraft|length >= 1 and aircraft[0].lon %}
            {{ aircraft[0].lon }}
          {% endif %}
        attributes_template: >
          {% set aircraft = state_attr('sensor.aircraft_data', 'aircraft') %}
          {% if aircraft and aircraft|length >= 1 %}
            {
              "callsign": "{{ aircraft[0].flight | default('Unknown') }}",
              "altitude": "{{ aircraft[0].alt_baro | default('N/A') }} ft",
              "speed": "{{ aircraft[0].gs | default('N/A') }} kts",
              "hex": "{{ aircraft[0].hex }}"
            }
          {% endif %}
```

**Then add a map card to your dashboard:**

```yaml
type: map
entities:
  - device_tracker.aircraft_1
  - device_tracker.aircraft_2
  - device_tracker.aircraft_3
auto_fit: true
default_zoom: 8
title: Live Aircraft Map
theme_mode: auto
```

**Note:** the entity-based map card shows aircraft as points but has limitations — no flight trails or detailed aircraft info, and updates are limited to Home Assistant's sensor scan intervals. For the full interactive experience, use the Webpage Card.

## Configuration

```yaml
tar1090_host: "192.168.1.175"  # IP address of your tar1090 server
tar1090_port: 8080             # Port of your tar1090 server (usually 8080)
update_interval: 1             # Data update interval in seconds (1-60)
show_history: true             # Show aircraft movement trails
map_center_lat: 40.7128        # Map center latitude (your location)
map_center_lon: -74.0060       # Map center longitude (your location)
map_zoom: 8                    # Initial map zoom level (1-18)
map_provider: "carto_dark"     # Default base map: carto_light | carto_dark | carto_voyager | esri_satellite
```

## API Endpoints

The tracker provides several REST API endpoints:

- `/api/aircraft` — Current aircraft data
- `/api/history` — Historical aircraft positions (if enabled)
- `/api/config` — Current configuration
- `/api/health` — Service health status
- `/api/stats` — Aircraft statistics

## Requirements

- A running tar1090 server (part of an ADS-B aircraft tracking setup)
- Network access from Home Assistant to the tar1090 server
- For the add-on: Home Assistant OS or Supervised installation
- For standalone: Python 3 with Flask and Requests

## Troubleshooting

### Map tiles won't load
This fork defaults to Carto specifically because OpenStreetMap's public tiles return HTTP 403 for self-hosted apps. If tiles still fail, switch the **Map Provider** to another Carto option or `esri_satellite` from the dropdown, and confirm the HA host has outbound internet access to `basemaps.cartocdn.com` / `server.arcgisonline.com`.

### Add-on not appearing
- Check Home Assistant logs for validation errors
- Ensure the repository URL is correct
- Try the standalone installation method

### No aircraft data
- Verify the tar1090 server is running and reachable
- Check network connectivity between HA and the tar1090 server
- Confirm `tar1090_host` and `tar1090_port`

### Dashboard integration issues
- For ingress mode, use the add-on's internal URL
- For standalone, use `http://your-ha-ip:8099`
- Ensure the HTTP/HTTPS protocol matches your HA setup

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed history of changes in each release.

## Credits & License

- Original project: **[random-robbie/tar1090-tracker](https://github.com/random-robbie/tar1090-tracker)** by [random-robbie](https://github.com/random-robbie). Full credit for the original add-on goes to the upstream author.
- Upstream tar1090 ADS-B interface: **[wiedehopf/tar1090](https://github.com/wiedehopf/tar1090)**.
- This fork adds selectable Carto base maps and switches flight links from FlightRadar24 to FlightAware.

Base map tiles are © OpenStreetMap contributors and © CARTO; satellite imagery © Esri. This add-on is distributed under the same **MIT License** as the upstream project; see the original repository for license terms.
