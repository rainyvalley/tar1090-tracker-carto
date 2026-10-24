# Tar1090 Aircraft Tracker (Carto) — Home Assistant Add-on

This add-on shows the aircraft from your [tar1090](https://github.com/wiedehopf/tar1090) server on a map in Home Assistant.

It is a fork of [`random-robbie/tar1090-tracker`](https://github.com/random-robbie/tar1090-tracker). See [Credits & License](#credits--license).

## What you get

- **Live map.** Aircraft move on a Leaflet map. Click one to see callsign, altitude, speed and track.
- **FlightAware link.** The popup has a **View on FlightAware** link. It uses the registration if known, else the callsign.
- **Trails.** The **Trails** button draws the path each aircraft has flown. The add-on records up to an hour per aircraft. Your choice is remembered in the browser.
- **Base maps.** Carto Light, Carto Dark (default), Carto Voyager and Esri Satellite. Pick the default with `map_provider`, or switch in the map's dropdown.
- **Sidebar panel.** The add-on opens inside Home Assistant through ingress.

## Install

1. In Home Assistant, go to **Settings → Add-ons → Add-on Store → ⋮ → Repositories** and add:

   ```
   https://github.com/rainyvalley/tar1090-tracker-carto
   ```

2. Install **Tar1090 Aircraft Tracker**.
3. Open the **Configuration** tab and set:

   | Option | What to enter |
   |---|---|
   | **Tar1090 Host** | The IP address or name of your tar1090 server. |
   | **Tar1090 Port** | Usually `8080`. |
   | **Update Interval** | Seconds between updates (1 to 60). |
   | **Show History** | Shows trails when the map opens, and keeps `/api/history`. The **Trails: On/Off** button overrides it in your browser. |
   | **Map Center** | Your latitude and longitude. |
   | **Map Zoom** | 1 is the whole world, 18 is street level. |
   | **Auto Center** | Keeps the map fitted to the aircraft. Panning or zooming pauses it. **Center Map** turns it back on. |
   | **Map Provider** | `carto_light`, `carto_dark`, `carto_voyager` or `esri_satellite`. |
   | **Carto API Key** | Optional. See below. |

4. Click **Save**, then **Start**. The add-on appears in the sidebar with an airplane icon.

**Carto API key.** The Carto maps load without a key today. A free key from [carto.com/basemaps](https://carto.com/basemaps) is a fallback if Carto starts to require one. It also lets browsers without WebGL use Carto's flat tiles. Your browser uses the key, so anyone who can open the page can read it. Restrict it to your domain in the Carto dashboard.

**Local add-on.** To run it as a local add-on, put the `tar1090/` folder in `/addons/tar1090-carto/` on your Home Assistant host. Then use **Settings → Add-ons → Add-on Store → ⋮ → Check for updates**. It appears under **Local add-ons**. After you edit files there, use **Rebuild**, not just Restart.

**Direct port (optional).** By default you reach the add-on through the sidebar only. To also get a plain web address, set a host port for `5000/tcp` under the add-on's **Network** settings, for example `8099`. That port has **no authentication**. Leave it empty unless you need it, and never forward it to the internet.

## Run without Home Assistant

You need Python 3 with Flask and Requests. Waitress is recommended.

1. Install the packages. On Alpine: `apk add --no-cache python3 py3-flask py3-requests py3-waitress`. Elsewhere: `pip install flask requests waitress`.
2. Start it:
   ```bash
   git clone https://github.com/rainyvalley/tar1090-tracker-carto.git
   cd tar1090-tracker-carto
   TAR1090_HOST=192.0.2.100 ./simple-start.sh
   ```
3. Open `http://localhost:8099`. Set `WEB_PORT` to change the port.

Every option in [Configuration](#configuration) can be set as an upper-case environment variable, for example `MAP_CENTER_LAT=51.5`.

**Who can connect.** `simple-start.sh` listens on `127.0.0.1`, so only this machine can open the page. This default changed: older versions listened on all interfaces. To reach it from other devices on a network you trust, start it with `BIND_HOST=0.0.0.0 ./simple-start.sh`. The server has **no authentication**, so never forward the port to the internet.

**Embedding.** To stop other sites from putting the page in a frame, set `FRAME_ANCESTORS="'self'"`. If you embed the page in a Home Assistant dashboard, add your Home Assistant address instead, for example `FRAME_ANCESTORS="'self' http://homeassistant.local:8123"`. Unset by default.

## FlightAware links

Open an aircraft's popup and click **View on FlightAware**. Ctrl+click or right-click on the marker opens the same page.

- With a **registration** (tail number): `https://www.flightaware.com/live/flight/<registration>`
- Otherwise with a **callsign**: `https://www.flightaware.com/live/flight/<callsign>`

## Show it on a Home Assistant dashboard

Use the direct port (`http://<host>:8099`) or a standalone install for these. The sidebar address needs a Home Assistant login, so cards cannot use it.

If Home Assistant is opened over `https://`, the browser blocks a card that loads an `http://` page (mixed content). Open Home Assistant over `http://`, or put the tracker behind your own HTTPS reverse proxy.

### Option 1: Webpage Card
1. **Edit your dashboard.**
2. **Add Card → Webpage Card.**
3. Set **URL** to `http://<host>:8099`, **Title** to `Aircraft Tracker`, **Aspect Ratio** to `16:9`.

### Option 2: Panel Dashboard
1. **Settings → Dashboards → Add Dashboard.**
2. Create a new dashboard of type **Panel (iframe)**.
3. Set **URL** to `http://<host>:8099`, **Title** to `Aircraft Tracker`, **Icon** to `mdi:airplane`.

### Option 3: Aircraft count as a sensor
Home Assistant has no built-in way to turn this feed into map-card entities. You can show the number of aircraft with a position as a sensor. Add this to `configuration.yaml` and restart Home Assistant:

```yaml
rest:
  - resource: http://<host>:8099/api/stats
    scan_interval: 10
    sensor:
      - name: "Aircraft in range"
        value_template: "{{ value_json.aircraft_with_position }}"
        unit_of_measurement: "aircraft"
```

For the map itself, use Option 1 or 2.

## Configuration

These are the add-on options. The values shown are examples.

```yaml
tar1090_host: "192.0.2.100"  # IP address or name of your tar1090 server
tar1090_port: 8080           # Port of your tar1090 server
update_interval: 1           # Seconds between updates (1-60)
show_history: true           # Trails on when the map opens; keep /api/history
map_center_lat: 40.7128      # Map center latitude
map_center_lon: -74.0060     # Map center longitude
map_zoom: 8                  # Initial zoom (1-18)
auto_center: false           # Keep the map fitted to the aircraft
map_provider: "carto_dark"   # carto_light | carto_dark | carto_voyager | esri_satellite
carto_api_key: ""            # Optional Carto key
```

## API Endpoints

| Path | Returns |
|---|---|
| `/api/aircraft` | Current aircraft. `"stale": true` and no aircraft when tar1090 has not answered for a while. |
| `/api/trails` | Recorded path of each current aircraft: `{"trails": {"<hex>": [[lat, lon], ...]}}`. |
| `/api/history` (also `/api/aircraft/history`) | Up to the last 12 snapshots, at most one every 5 seconds, when `show_history` is on. `?limit=N` returns the newest N. A `limit` that is not a whole number of 0 or more gives HTTP 400. |
| `/api/config` | The map settings, including `carto_api_key`, which the browser needs. |
| `/api/health` | `"healthy"`, or `"degraded"` when tar1090 data is stale. |
| `/api/stats` | Counts. `total_aircraft` counts all aircraft. `aircraft_with_position` counts only those with a valid position. |

Records with an invalid ICAO hex are dropped. A latitude outside -90 to 90 or a longitude outside -180 to 180 is removed from its record.

## Requirements

- A running tar1090 server.
- Network access from Home Assistant (or the standalone machine) to that server.
- For the add-on: Home Assistant OS or Supervised.
- A browser with WebGL for the Carto maps.

## Troubleshooting

### Map tiles won't load
Check that the device with the browser can reach `basemaps.cartocdn.com`, `tiles.basemaps.cartocdn.com` and `server.arcgisonline.com`.

| You see | It means | Do this |
|---|---|---|
| **API KEY REQUIRED** on the map | The browser has no WebGL, so it uses Carto flat tiles, which need a key. | Set `carto_api_key`, or use a browser with WebGL. |
| Only **Satellite** in the dropdown | No WebGL and no `carto_api_key`. The browser console says so. | Same as above. |
| The map switched to satellite by itself | Carto rejected its vector style (HTTP 401 or 403). | Set `carto_api_key`. |

### No aircraft
The header shows **tar1090 unreachable** when the add-on runs but cannot get data from tar1090. The add-on log says why.

- Check that tar1090 is running.
- Check `tar1090_host` and `tar1090_port`.
- Check the network between Home Assistant and the tar1090 server.
- A tar1090 address that answers with a redirect is treated as an error. Use the final address.

### Add-on not in the store
- Check the Home Assistant log for errors.
- Check the repository address.
- Try [Run without Home Assistant](#run-without-home-assistant).

### Dashboard card is blank
- Use `http://<host>:8099`, not the sidebar address.
- Match `http` or `https` to how you open Home Assistant. See [Show it on a Home Assistant dashboard](#show-it-on-a-home-assistant-dashboard).

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed history of changes in each release.

## Credits & License

- Original project: **[random-robbie/tar1090-tracker](https://github.com/random-robbie/tar1090-tracker)** by [random-robbie](https://github.com/random-robbie). Full credit for the original add-on goes to the upstream author.
- Upstream tar1090 ADS-B interface: **[wiedehopf/tar1090](https://github.com/wiedehopf/tar1090)**.
- This fork adds selectable Carto base maps and switches flight links from FlightRadar24 to FlightAware.

Base map tiles are © OpenStreetMap contributors and © CARTO; satellite imagery © Esri. This add-on is distributed under the same **MIT License** as the upstream project; see [LICENSE](LICENSE).

## A note on AI assistance

Parts of this project — code, configuration, and documentation — were written with the help of generative AI. Everything in here was reviewed, tested, and corrected by a human before being committed; nothing was accepted on the model's say-so.
