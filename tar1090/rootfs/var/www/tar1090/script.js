class AircraftTracker {
    constructor() {
        this.map = null;
        // Maps keyed by aircraft hex (plain objects would resolve keys
        // such as "__proto__" to Object.prototype).
        this.aircraftMarkers = new Map();
        this.trailPoints = new Map();
        this.trailLines = new Map();
        this.config = {};
        this.showHistory = false;
        this.maxTrailPoints = 720;  // matches the add-on's TRAIL_MAX_POINTS
        this.lastAircraft = [];
        this.userMovedMap = false;
        this.autoFitting = false;

        this.init();
    }

    async init() {
        try {
            await this.loadConfig();
            this.initMap();
            this.setupEventListeners();
            this.startDataUpdates();
        } catch (error) {
            console.error('Failed to initialize:', error);
            this.updateConnectionStatus('disconnected');
        }
    }

    async loadConfig() {
        try {
            this.config = await this.fetchAPI('config');
        } catch (error) {
            console.warn('Using default configuration:', error);
            this.config = {
                map_center_lat: 54.7023,
                map_center_lon: -3.2765,
                map_zoom: 8,
                update_interval: 1,
                show_history: true,
                auto_center: false,
                map_provider: 'carto_dark',
                carto_api_key: ''
            };
        }
        this.showHistory = this.config.show_history === true;
        // The viewer's own choice from the Trails button wins over the default
        try {
            const saved = localStorage.getItem('tar1090-trails');
            if (saved === 'on' || saved === 'off') this.showHistory = saved === 'on';
        } catch (e) { /* storage unavailable: keep the configured default */ }
    }

    initMap() {
        // Initialize map with configured center and zoom
        this.map = L.map('map').setView(
            [this.config.map_center_lat, this.config.map_center_lon], 
            this.config.map_zoom
        );

        // Available base map providers. Carto is used by default because
        // OpenStreetMap's public tile servers reject (HTTP 403) traffic from
        // self-hosted apps under their tile usage policy.
        //
        // Carto layers are drawn from Carto's vector GL styles through
        // MapLibre (bridged into Leaflet by maplibre-gl-leaflet). Since
        // 2026-09-25 Carto's raster PNG tiles render "API KEY REQUIRED"
        // without a key, while the vector styles still load keyless. An
        // optional carto_api_key is appended to every Carto request so the
        // map keeps working if Carto extends the key requirement to vector.
        // Browsers without WebGL fall back to Carto raster (only usable with
        // a key) or, failing that, to Esri satellite.
        const cartoAttr = '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors '
            + '&copy; <a href="https://carto.com/attributions" target="_blank" rel="noopener">CARTO</a>';
        const cartoKey = String(this.config.carto_api_key || '').trim();
        const webgl = this.supportsWebGL();
        if (!webgl) {
            console.warn('WebGL unavailable: Carto vector maps disabled'
                + (cartoKey ? ', using Carto raster tiles' : ' (set carto_api_key for Carto raster tiles)'));
        }

        const withCartoKey = (url) => {
            if (!cartoKey) return url;
            try {
                const u = new URL(url);
                if (!/(^|\.)cartocdn\.com$/.test(u.hostname)) return url;
                u.searchParams.set('key', cartoKey);
                return u.toString();
            } catch (e) {
                return url;
            }
        };

        const cartoLayer = (glStyle, rasterPath) => {
            if (webgl) {
                return L.maplibreGL({
                    style: withCartoKey('https://basemaps.cartocdn.com/gl/' + glStyle + '/style.json'),
                    attribution: cartoAttr,
                    transformRequest: (url) => ({ url: withCartoKey(url) })
                });
            }
            if (cartoKey) {
                return L.tileLayer('https://{s}.basemaps.cartocdn.com/' + rasterPath + '/{z}/{x}/{y}{r}.png?key='
                    + encodeURIComponent(cartoKey), {
                    maxZoom: 20,
                    subdomains: 'abcd',
                    attribution: cartoAttr
                });
            }
            return null;
        };

        const layers = {
            carto_light: cartoLayer('positron-gl-style', 'light_all'),
            carto_dark: cartoLayer('dark-matter-gl-style', 'dark_all'),
            carto_voyager: cartoLayer('voyager-gl-style', 'rastertiles/voyager'),
            esri_satellite: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
                maxZoom: 19,
                attribution: 'Tiles &copy; Esri'
            })
        };
        this.baseLayers = {};
        Object.keys(layers).forEach((id) => {
            if (layers[id]) this.baseLayers[id] = layers[id];
        });
        this.fallbackProvider = this.baseLayers.carto_dark ? 'carto_dark' : 'esri_satellite';

        // Hide selector entries for providers this browser can't show
        const selector = document.getElementById('map-layer');
        if (selector) {
            Array.from(selector.options).forEach((opt) => {
                if (!this.baseLayers[opt.value]) opt.remove();
            });
        }

        const provider = this.setMapProvider(this.config.map_provider);
        console.log('Map initialized with provider:', provider);
    }

    supportsWebGL() {
        try {
            if (typeof maplibregl === 'undefined' || typeof L.maplibreGL !== 'function') return false;
            const canvas = document.createElement('canvas');
            return !!(canvas.getContext('webgl2') || canvas.getContext('webgl'));
        } catch (e) {
            return false;
        }
    }

    setMapProvider(id) {
        if (!this.baseLayers[id]) id = this.fallbackProvider;
        const next = this.baseLayers[id];
        if (this.currentBaseLayer && this.currentBaseLayer !== next) {
            this.map.removeLayer(this.currentBaseLayer);
        }
        try {
            if (!this.map.hasLayer(next)) {
                next.addTo(this.map);
            }
        } catch (error) {
            // MapLibre throws if the WebGL context can't be created
            console.error('Failed to show map provider ' + id + ':', error);
            if (this.map.hasLayer(next)) this.map.removeLayer(next);
            if (id !== 'esri_satellite') return this.setMapProvider('esri_satellite');
            this.currentBaseLayer = null;
            return null;
        }
        if (typeof next.getMaplibreMap === 'function') this.watchVectorLayer(id, next);
        this.currentBaseLayer = next;

        const selector = document.getElementById('map-layer');
        if (selector) selector.value = id;
        return id;
    }

    watchVectorLayer(id, layer) {
        // If Carto starts rejecting the style (e.g. a key becomes required
        // for vector too), say so in the console instead of failing silently.
        const glMap = layer.getMaplibreMap();
        if (!glMap || glMap._tar1090Watched) return;
        glMap._tar1090Watched = true;
        glMap.on('error', (e) => {
            const status = e && e.error && e.error.status;
            console.error('Map provider ' + id + ' error' + (status ? ' (HTTP ' + status + ')' : '') + ':',
                e && e.error ? e.error.message || e.error : e);
            if ((status === 401 || status === 403) && this.currentBaseLayer === layer) {
                console.warn('Carto rejected the request; check carto_api_key. Switching to satellite.');
                this.setMapProvider('esri_satellite');
            }
        });
    }

    setupEventListeners() {
        // Toggle history button (initial state comes from show_history)
        const historyBtn = document.getElementById('toggle-history');
        const setHistoryLabel = () => {
            historyBtn.textContent = this.showHistory ? 'Trails: On' : 'Trails: Off';
            historyBtn.setAttribute('aria-pressed', String(this.showHistory));
            historyBtn.classList.toggle('active', this.showHistory);
        };
        setHistoryLabel();
        historyBtn.addEventListener('click', () => {
            this.showHistory = !this.showHistory;
            setHistoryLabel();
            try {
                localStorage.setItem('tar1090-trails', this.showHistory ? 'on' : 'off');
            } catch (e) { /* not remembered; fine */ }
            this.clearTrails();
            if (this.showHistory) this.loadTrails();
        });

        // Center map button; also resumes auto-centering after a manual pan
        document.getElementById('center-map').addEventListener('click', () => {
            this.map.setView(
                [this.config.map_center_lat, this.config.map_center_lon], 
                this.config.map_zoom
            );
            this.userMovedMap = false;
        });

        // auto_center follows the aircraft until the user pans or zooms
        this.map.on('dragstart zoomstart', () => {
            if (!this.autoFitting) this.userMovedMap = true;
        });

        // Toggle aircraft list button (list starts hidden, see index.html)
        document.getElementById('toggle-list').addEventListener('click', () => {
            const aircraftList = document.getElementById('aircraft-list');
            this.setAircraftListVisible(aircraftList.classList.contains('is-hidden'));
        });

        // Explicit close button on the list itself
        document.getElementById('close-list').addEventListener('click', () => {
            this.setAircraftListVisible(false);
        });

        // Map layer selector
        document.getElementById('map-layer').addEventListener('change', (e) => {
            this.setMapProvider(e.target.value);
        });
    }

    setAircraftListVisible(visible) {
        const aircraftList = document.getElementById('aircraft-list');
        const toggleBtn = document.getElementById('toggle-list');

        aircraftList.classList.toggle('is-hidden', !visible);
        aircraftList.setAttribute('aria-hidden', visible ? 'false' : 'true');
        toggleBtn.setAttribute('aria-expanded', visible ? 'true' : 'false');
        toggleBtn.textContent = visible ? 'Hide Aircraft List' : 'Show Aircraft List';
        if (visible) this.updateAircraftList(this.lastAircraft);
    }

    async fetchAPI(endpoint) {
        // Relative URL only: under HA ingress the page lives below
        // /api/hassio_ingress/<token>/, so absolute paths would hit HA itself.
        const options = { cache: 'no-store' };
        if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
            options.signal = AbortSignal.timeout(10000);
        }
        const response = await fetch(endpoint, options);
        if (!response.ok) {
            throw new Error(`Failed to fetch ${endpoint}: HTTP ${response.status}`);
        }
        return response.json();
    }

    async startDataUpdates() {
        const interval = Math.max(1, Number(this.config.update_interval) || 1) * 1000;
        const updateData = async () => {
            try {
                const aircraftData = await this.fetchAPI('aircraft');

                this.updateAircraft(aircraftData);
                // total_aircraft and last_update both come straight from the
                // aircraft response, so a second /stats round trip per poll
                // is redundant (the /stats endpoint itself stays available).
                this.updateStats(aircraftData);
                this.updateConnectionStatus(aircraftData.stale ? 'stale' : 'connected');
            } catch (error) {
                console.error('Failed to fetch data:', error);
                this.updateConnectionStatus('disconnected');
            }
            // Schedule the next poll only after this one finished, so slow
            // responses can't pile up or arrive out of order.
            setTimeout(updateData, interval);
        };

        await updateData();
        if (this.showHistory) this.loadTrails();
    }

    // Draw each aircraft's path so far, as recorded by the add-on, so trails
    // show where aircraft have been rather than only since the page opened.
    async loadTrails() {
        let data;
        try {
            data = await this.fetchAPI('trails');
        } catch (error) {
            console.warn('Could not load trails:', error);
            return;
        }
        if (!this.showHistory || !data || typeof data.trails !== 'object' || data.trails === null) return;
        Object.entries(data.trails).forEach(([hex, path]) => {
            const marker = this.aircraftMarkers.get(hex);
            if (!marker || !Array.isArray(path)) return;
            const points = path.filter(p => Array.isArray(p) && p.length === 2
                && Number.isFinite(p[0]) && Number.isFinite(p[1]));
            if (points.length < 2) return;
            // Keep any live points newer than the recorded path's end
            const current = marker.getLatLng();
            const last = points[points.length - 1];
            if (last[0] !== current.lat || last[1] !== current.lng) points.push([current.lat, current.lng]);
            this.trailPoints.set(hex, points.slice(-this.maxTrailPoints));
            const old = this.trailLines.get(hex);
            if (old) this.map.removeLayer(old);
            this.trailLines.delete(hex);
            this.updateTrail(hex, [current.lat, current.lng], this.getAircraftColor(marker.aircraft));
        });
    }

    // Normalise one aircraft.json record. Returns null for records without
    // a usable ICAO hex so one malformed entry can't break the whole update.
    normalizeAircraft(raw) {
        if (!raw || typeof raw !== 'object') return null;
        const hex = String(raw.hex ?? '').trim().toLowerCase();
        if (!/^~?[0-9a-f]{6}$/.test(hex)) return null;
        const num = (v) => {
            if (v === null || v === undefined || v === '' || typeof v === 'boolean') return null;
            const n = Number(v);
            return Number.isFinite(n) ? n : null;
        };
        const str = (v) => String(v ?? '').trim();
        const onGround = raw.alt_baro === 'ground';
        const lat = num(raw.lat);
        const lon = num(raw.lon);
        return {
            hex,
            flight: str(raw.flight),
            registration: str(raw.r ?? raw.reg),
            type: str(raw.t),
            category: str(raw.category),
            squawk: str(raw.squawk),
            lat: lat !== null && Math.abs(lat) <= 90 ? lat : null,
            lon: lon !== null && Math.abs(lon) <= 180 ? lon : null,
            onGround,
            altitude: onGround ? 0 : (num(raw.alt_baro) ?? num(raw.alt_geom)),
            gs: num(raw.gs),
            track: num(raw.track)
        };
    }

    updateAircraft(data) {
        const records = data && Array.isArray(data.aircraft) ? data.aircraft : [];
        const currentAircraft = [];
        const seen = new Set();
        records.forEach((raw) => {
            const ac = this.normalizeAircraft(raw);
            if (ac && !seen.has(ac.hex)) {
                seen.add(ac.hex);
                currentAircraft.push(ac);
            }
        });

        // Remove aircraft that are no longer present
        Array.from(this.aircraftMarkers.keys()).forEach(hex => {
            if (!seen.has(hex)) {
                this.removeAircraft(hex);
            }
        });

        // Update or add aircraft
        currentAircraft.forEach(aircraft => {
            try {
                this.updateAircraftMarker(aircraft);
            } catch (error) {
                console.error('Failed to update aircraft ' + aircraft.hex + ':', error);
            }
        });

        this.autoCenterOnAircraft(currentAircraft);
        this.updateAircraftList(currentAircraft);
    }

    autoCenterOnAircraft(aircraft) {
        if (!this.config.auto_center || this.userMovedMap) return;
        const points = aircraft.filter(a => a.lat !== null && a.lon !== null).map(a => [a.lat, a.lon]);
        if (points.length === 0) return;
        this.autoFitting = true;
        try {
            this.map.fitBounds(L.latLngBounds(points), {
                padding: [40, 40],
                maxZoom: Number(this.config.map_zoom) || 12,
                animate: false
            });
        } finally {
            this.autoFitting = false;
        }
    }

    createAircraftIcon(size, color) {
        return L.divIcon({
            html: `<div class="aircraft-icon-container" style="width: ${size}px; height: ${size}px;">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="${size}" height="${size}" style="display: block;">
                    <path fill="${color}" stroke="#000" stroke-width="1.5" d="M21,16V14L13,9V3.5A1.5,1.5 0 0,0 11.5,2A1.5,1.5 0 0,0 10,3.5V9L2,14V16L10,13.5V19L8,20.5V22L11.5,21L15,22V20.5L13,19V13.5L21,16Z"/>
                    <path fill="#ffffff" stroke="none" d="M19,15V14L12.5,10V4A1,1 0 0,0 11.5,3A1,1 0 0,0 10.5,4V10L4,14V15L10.5,13V18L9,19V20L11.5,19.5L14,20V19L12.5,18V13L19,15Z"/>
                </svg>
            </div>`,
            className: 'aircraft-marker',
            iconSize: [size, size],
            iconAnchor: [size / 2, size / 2]
        });
    }

    applyRotation(marker, track) {
        if (track !== null) {
            // Turn the shortest way (e.g. 359 -> 1 degrees) so the CSS
            // transition doesn't spin the icon all the way round.
            const prev = marker.rotation ?? track;
            marker.rotation = prev + ((((track - prev) % 360) + 540) % 360) - 180;
        }
        const container = marker.getElement()?.querySelector('.aircraft-icon-container');
        if (container) container.style.setProperty('--rot', `${marker.rotation ?? 0}deg`);
    }

    updateAircraftMarker(aircraft) {
        const hex = aircraft.hex;
        let marker = this.aircraftMarkers.get(hex);

        // No position (any more): don't leave a frozen marker behind
        if (aircraft.lat === null || aircraft.lon === null) {
            if (marker) this.removeAircraft(hex);
            return;
        }

        const position = [aircraft.lat, aircraft.lon];
        const iconSize = this.getAircraftIconSize(aircraft);
        const color = this.getAircraftColor(aircraft);
        const iconKey = iconSize + '|' + color;

        if (marker) {
            marker.setLatLng(position);
            // Colour follows altitude and size may change once the type is known
            if (marker.iconKey !== iconKey) {
                marker.setIcon(this.createAircraftIcon(iconSize, color));
                marker.iconKey = iconKey;
            }
            marker.setPopupContent(this.createPopupContent(aircraft));
        } else {
            marker = L.marker(position, { icon: this.createAircraftIcon(iconSize, color) });
            marker.iconKey = iconKey;
            marker.bindPopup(this.createPopupContent(aircraft));

            // Ctrl+click opens FlightAware directly
            marker.on('click', (e) => {
                if (e.originalEvent.ctrlKey) {
                    e.originalEvent.preventDefault();
                    const url = this.flightAwareUrl(marker.aircraft);
                    if (url) window.open(url, '_blank', 'noopener,noreferrer');
                }
            });

            // Right-click opens FlightAware directly
            marker.on('contextmenu', (e) => {
                e.originalEvent.preventDefault();
                const url = this.flightAwareUrl(marker.aircraft);
                if (url) window.open(url, '_blank', 'noopener,noreferrer');
            });

            marker.addTo(this.map);
            this.aircraftMarkers.set(hex, marker);
        }

        // Handlers read the latest data (callsign/registration arrive late)
        marker.aircraft = aircraft;
        this.applyRotation(marker, aircraft.track);

        if (this.showHistory) {
            this.updateTrail(hex, position, color);
        }
    }

    updateTrail(hex, position, color) {
        let points = this.trailPoints.get(hex);
        if (!points) {
            points = [];
            this.trailPoints.set(hex, points);
        }

        // Only record actual movement
        const last = points[points.length - 1];
        if (!last || last[0] !== position[0] || last[1] !== position[1]) {
            points.push(position);
            if (points.length > this.maxTrailPoints) points.shift();
        }

        const line = this.trailLines.get(hex);
        if (line) {
            line.setLatLngs(points);
            line.setStyle({ color });
        } else if (points.length > 1) {
            const trail = L.polyline(points, { color, weight: 2, opacity: 0.6 });
            trail.addTo(this.map);
            this.trailLines.set(hex, trail);
        }
    }

    removeAircraft(hex) {
        const marker = this.aircraftMarkers.get(hex);
        if (marker) {
            this.map.removeLayer(marker);
            this.aircraftMarkers.delete(hex);
        }

        const line = this.trailLines.get(hex);
        if (line) {
            this.map.removeLayer(line);
            this.trailLines.delete(hex);
        }
        this.trailPoints.delete(hex);
    }

    clearTrails() {
        this.trailLines.forEach(line => this.map.removeLayer(line));
        this.trailLines.clear();
        this.trailPoints.clear();
    }

    getAircraftColor(aircraft) {
        // Color based on altitude
        const altitude = aircraft.altitude ?? 0;  // on ground counts as 0

        if (altitude < 5000) return '#ff4444';      // Red - Low altitude
        if (altitude < 15000) return '#ffaa00';     // Orange - Medium altitude  
        if (altitude < 25000) return '#00aaff';     // Blue - High altitude
        return '#00ff88';                           // Green - Very high altitude
    }

    getAircraftIconSize(aircraft) {
        // Size based on aircraft category or type - optimized for Material Design icon
        const category = aircraft.category;
        const type = aircraft.type;
        
        // Large aircraft (A380, B747, etc.)
        if (type.includes('A38') || type.includes('B74') || category === 'A7') return 32;
        
        // Wide-body aircraft (B777, A330, etc.)
        if (type.includes('B77') || type.includes('A33') || type.includes('A34') || category === 'A5') return 28;
        
        // Narrow-body aircraft (A320, B737, etc.)  
        if (type.includes('A32') || type.includes('B73') || category === 'A3') return 24;
        
        // Regional/Small aircraft
        if (category === 'A1' || category === 'A2') return 20;
        
        // Default size - good balance of visibility and performance
        return 24;
    }

    // Aircraft fields come from over-the-air ADS-B data and tar1090's
    // database, so escape them before building HTML.
    escapeHtml(value) {
        return String(value ?? '').replace(/[&<>"']/g, (c) => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        })[c]);
    }

    flightAwareUrl(aircraft) {
        const ident = aircraft && (aircraft.registration || aircraft.flight);
        return ident ? 'https://www.flightaware.com/live/flight/' + encodeURIComponent(ident) : null;
    }

    formatAltitude(aircraft) {
        if (aircraft.onGround) return 'Ground';
        return aircraft.altitude !== null ? `${aircraft.altitude} ft` : 'N/A';
    }

    createPopupContent(aircraft) {
        const esc = (v) => this.escapeHtml(v);
        const callsign = aircraft.flight || 'N/A';
        const speed = aircraft.gs !== null ? `${aircraft.gs} kts` : 'N/A';
        const track = aircraft.track !== null ? `${aircraft.track}°` : 'N/A';
        const squawk = aircraft.squawk || 'N/A';

        // Create FlightAware link if we have registration or callsign
        const faUrl = this.flightAwareUrl(aircraft);
        const fr24Link = faUrl
            ? `<div style="margin-top: 8px;"><a href="${esc(faUrl)}" target="_blank" rel="noopener noreferrer" style="color: #00aaff; text-decoration: none; font-weight: bold;">📡 View on FlightAware</a></div>`
            : '';

        return `
            <div class="popup-callsign">${esc(callsign)}</div>
            <div class="popup-details">
                <div><strong>Hex:</strong> ${esc(aircraft.hex)}</div>
                ${aircraft.registration ? `<div><strong>Registration:</strong> ${esc(aircraft.registration)}</div>` : ''}
                <div><strong>Altitude:</strong> ${esc(this.formatAltitude(aircraft))}</div>
                <div><strong>Speed:</strong> ${esc(speed)}</div>
                <div><strong>Track:</strong> ${esc(track)}</div>
                <div><strong>Squawk:</strong> ${esc(squawk)}</div>
                ${aircraft.category ? `<div><strong>Category:</strong> ${esc(aircraft.category)}</div>` : ''}
                ${fr24Link}
            </div>
        `;
    }

    updateAircraftList(aircraft) {
        this.lastAircraft = aircraft;
        // Nothing to draw while the list is hidden
        const list = document.getElementById('aircraft-list');
        if (list.classList.contains('is-hidden')) return;

        const listContainer = document.getElementById('aircraft-items');
        listContainer.innerHTML = '';

        // Sort by callsign, then by hex
        const label = (ac) => ac.flight || ac.hex;
        const sorted = aircraft.slice().sort((a, b) => label(a).localeCompare(label(b)));

        sorted.forEach(ac => {
            const item = document.createElement('div');
            item.className = 'aircraft-item';
            item.tabIndex = 0;
            item.setAttribute('role', 'button');

            const speed = ac.gs !== null ? `${ac.gs} kts` : 'N/A';

            item.innerHTML = `
                <div class="aircraft-callsign">${this.escapeHtml(label(ac))}</div>
                <div class="aircraft-details">
                    <span class="aircraft-altitude">${this.escapeHtml(this.formatAltitude(ac))}</span> | 
                    <span class="aircraft-speed">${this.escapeHtml(speed)}</span>
                </div>
            `;

            // Click (or Enter/Space) to center on aircraft
            const focusAircraft = () => {
                const marker = this.aircraftMarkers.get(ac.hex);
                if (marker) {
                    this.userMovedMap = true;
                    this.map.setView(marker.getLatLng(), 12);
                    marker.openPopup();
                }
            };
            item.addEventListener('click', focusAircraft);
            item.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    focusAircraft();
                }
            });

            listContainer.appendChild(item);
        });
    }

    updateStats(data) {
        document.getElementById('aircraft-count').textContent =
            `${(data.aircraft || []).length} aircraft`;

        const lastUpdate = data.now ?
            new Date(data.now * 1000).toLocaleTimeString() : '--';
        document.getElementById('last-update').textContent =
            `Last update: ${lastUpdate}`;
    }

    // state: 'connected', 'stale' (add-on up, tar1090 unreachable) or
    // 'disconnected' (add-on unreachable)
    updateConnectionStatus(state) {
        const statusElement = document.getElementById('connection-status');
        const labels = { connected: 'Connected', stale: 'tar1090 unreachable', disconnected: 'Disconnected' };
        statusElement.textContent = labels[state] || labels.disconnected;
        statusElement.className = state === 'connected' ? 'status-connected' : 'status-disconnected';
    }
}

// Initialize the tracker when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new AircraftTracker();
});