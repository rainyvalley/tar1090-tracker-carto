class AircraftTracker {
    constructor() {
        this.map = null;
        this.aircraftMarkers = {};
        this.aircraftTrails = {};
        this.config = {};
        this.showHistory = false;
        
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
            this.updateConnectionStatus(false);
        }
    }

    async loadConfig() {
        // Simplified URL handling for ingress mode
        const apiUrls = [
            'config',                // Simple relative path (works best in ingress)
            './config',              // Explicit relative path
            '/config',               // Absolute path (fallback)
            'api/config'             // With api prefix (fallback)
        ];
        
        for (const url of apiUrls) {
            try {
                const response = await fetch(url);
                if (response.ok) {
                    this.config = await response.json();
                    console.log('Config loaded from:', url);
                    return;
                }
            } catch (error) {
                console.warn(`Failed to load config from ${url}:`, error);
            }
        }
        
        // If all fail, use defaults
        console.warn('Using default configuration');
        this.config = {
            map_center_lat: 54.7023,
            map_center_lon: -3.2765,
            map_zoom: 8,
            update_interval: 1,
            map_provider: 'carto_dark',
            carto_api_key: ''
        };
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
        // Toggle history button
        document.getElementById('toggle-history').addEventListener('click', () => {
            this.showHistory = !this.showHistory;
            document.getElementById('toggle-history').textContent = 
                this.showHistory ? 'Hide History' : 'Show History';
            this.clearTrails();
        });

        // Center map button
        document.getElementById('center-map').addEventListener('click', () => {
            this.map.setView(
                [this.config.map_center_lat, this.config.map_center_lon], 
                this.config.map_zoom
            );
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
    }

    async fetchAPI(endpoint) {
        // Simplified URL handling for ingress mode
        const apiUrls = [
            endpoint,                // Simple relative path (works best in ingress)
            `./${endpoint}`,         // Explicit relative path
            `/${endpoint}`,          // Absolute path (fallback)
            `api/${endpoint}`        // With api prefix (fallback)
        ];
        
        for (const url of apiUrls) {
            try {
                const response = await fetch(url);
                if (response.ok) {
                    return await response.json();
                }
            } catch (error) {
                console.warn(`Failed to fetch from ${url}:`, error);
            }
        }
        
        throw new Error(`Failed to fetch ${endpoint} from all URLs`);
    }

    async startDataUpdates() {
        const updateData = async () => {
            try {
                const [aircraftData, statsData] = await Promise.all([
                    this.fetchAPI('aircraft'),
                    this.fetchAPI('stats')
                ]);

                this.updateAircraft(aircraftData);
                this.updateStats(statsData);
                this.updateConnectionStatus(true);
            } catch (error) {
                console.error('Failed to fetch data:', error);
                this.updateConnectionStatus(false);
            }
        };

        // Initial update
        await updateData();
        
        // Set up periodic updates
        setInterval(updateData, this.config.update_interval * 1000);
    }

    updateAircraft(data) {
        const currentAircraft = data.aircraft || [];
        const currentHexIds = new Set(currentAircraft.map(a => a.hex));

        // Remove aircraft that are no longer present
        Object.keys(this.aircraftMarkers).forEach(hex => {
            if (!currentHexIds.has(hex)) {
                this.removeAircraft(hex);
            }
        });

        // Update or add aircraft
        currentAircraft.forEach(aircraft => {
            this.updateAircraftMarker(aircraft);
        });

        this.updateAircraftList(currentAircraft);
    }

    updateAircraftMarker(aircraft) {
        const hex = aircraft.hex;
        
        // Skip aircraft without position
        if (!aircraft.lat || !aircraft.lon) return;

        const position = [aircraft.lat, aircraft.lon];
        
        if (this.aircraftMarkers[hex]) {
            // Update existing marker
            const marker = this.aircraftMarkers[hex];
            const oldPos = marker.getLatLng();
            marker.setLatLng(position);
            
            // Update rotation if track is available
            if (aircraft.track !== undefined) {
                const iconContainer = marker.getElement()?.querySelector('.aircraft-icon-container');
                if (iconContainer) {
                    iconContainer.style.transform = `rotate(${Number(aircraft.track) || 0}deg)`;
                }
            }
            
            // Update trail if history is enabled
            if (this.showHistory) {
                this.updateTrail(hex, [oldPos.lat, oldPos.lng], position);
            }
            
            // Update popup content
            marker.setPopupContent(this.createPopupContent(aircraft));
        } else {
            // Create aircraft icon with proper rotation and size based on aircraft type
            const iconSize = this.getAircraftIconSize(aircraft);
            const rotation = Number(aircraft.track) || 0;
            const color = this.getAircraftColor(aircraft);
            
            const aircraftIcon = L.divIcon({
                html: `<div class="aircraft-icon-container" style="transform: rotate(${rotation}deg); width: ${iconSize}px; height: ${iconSize}px;">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="${iconSize}" height="${iconSize}" style="display: block;">
                        <path fill="${color}" stroke="#000" stroke-width="1.5" d="M21,16V14L13,9V3.5A1.5,1.5 0 0,0 11.5,2A1.5,1.5 0 0,0 10,3.5V9L2,14V16L10,13.5V19L8,20.5V22L11.5,21L15,22V20.5L13,19V13.5L21,16Z"/>
                        <path fill="#ffffff" stroke="none" d="M19,15V14L12.5,10V4A1,1 0 0,0 11.5,3A1,1 0 0,0 10.5,4V10L4,14V15L10.5,13V18L9,19V20L11.5,19.5L14,20V19L12.5,18V13L19,15Z"/>
                    </svg>
                </div>`,
                className: 'aircraft-marker',
                iconSize: [iconSize, iconSize],
                iconAnchor: [iconSize/2, iconSize/2]
            });

            // Create new marker
            const marker = L.marker(position, { icon: aircraftIcon });
            marker.bindPopup(this.createPopupContent(aircraft));
            
            // Add click handler for FlightAware 
            marker.on('click', (e) => {
                // Right-click or Ctrl+click to open FlightAware directly
                if (e.originalEvent.ctrlKey || e.originalEvent.button === 2) {
                    e.originalEvent.preventDefault();
                    const url = this.flightAwareUrl(aircraft);
                    if (url) window.open(url, '_blank', 'noopener,noreferrer');
                }
            });
            
            // Add context menu (right-click) handler
            marker.on('contextmenu', (e) => {
                e.originalEvent.preventDefault();
                const url = this.flightAwareUrl(aircraft);
                if (url) window.open(url, '_blank', 'noopener,noreferrer');
            });
            
            marker.addTo(this.map);
            this.aircraftMarkers[hex] = marker;
            
            // Initialize trail
            if (this.showHistory) {
                this.aircraftTrails[hex] = [position];
            }
        }
    }

    updateTrail(hex, oldPos, newPos) {
        if (!this.aircraftTrails[hex]) {
            this.aircraftTrails[hex] = [];
        }
        
        this.aircraftTrails[hex].push(newPos);
        
        // Keep only last 50 positions to prevent performance issues
        if (this.aircraftTrails[hex].length > 50) {
            this.aircraftTrails[hex].shift();
        }
        
        // Remove existing trail polyline
        if (this.aircraftTrails[hex + '_line']) {
            this.map.removeLayer(this.aircraftTrails[hex + '_line']);
        }
        
        // Draw new trail
        if (this.aircraftTrails[hex].length > 1) {
            const trail = L.polyline(this.aircraftTrails[hex], {
                color: this.getAircraftColor({ hex }),
                weight: 2,
                opacity: 0.6
            });
            trail.addTo(this.map);
            this.aircraftTrails[hex + '_line'] = trail;
        }
    }

    removeAircraft(hex) {
        // Remove marker
        if (this.aircraftMarkers[hex]) {
            this.map.removeLayer(this.aircraftMarkers[hex]);
            delete this.aircraftMarkers[hex];
        }
        
        // Remove trail
        if (this.aircraftTrails[hex + '_line']) {
            this.map.removeLayer(this.aircraftTrails[hex + '_line']);
            delete this.aircraftTrails[hex + '_line'];
        }
        
        delete this.aircraftTrails[hex];
    }

    clearTrails() {
        Object.keys(this.aircraftTrails).forEach(key => {
            if (key.endsWith('_line')) {
                this.map.removeLayer(this.aircraftTrails[key]);
                delete this.aircraftTrails[key];
            }
        });
        
        if (!this.showHistory) {
            Object.keys(this.aircraftTrails).forEach(hex => {
                if (!hex.endsWith('_line')) {
                    delete this.aircraftTrails[hex];
                }
            });
        }
    }

    getAircraftColor(aircraft) {
        // Color based on altitude
        const altitude = aircraft.alt_baro || aircraft.alt_geom || 0;
        
        if (altitude < 5000) return '#ff4444';      // Red - Low altitude
        if (altitude < 15000) return '#ffaa00';     // Orange - Medium altitude  
        if (altitude < 25000) return '#00aaff';     // Blue - High altitude
        return '#00ff88';                           // Green - Very high altitude
    }

    getAircraftIconSize(aircraft) {
        // Size based on aircraft category or type - optimized for Material Design icon
        const category = aircraft.category || '';
        const type = aircraft.t || '';
        
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
        const registration = aircraft.r || aircraft.reg;
        const callsign = aircraft.flight ? aircraft.flight.trim() : null;
        const ident = registration || callsign;
        return ident ? 'https://www.flightaware.com/live/flight/' + encodeURIComponent(ident) : null;
    }

    createPopupContent(aircraft) {
        const esc = (v) => this.escapeHtml(v);
        const callsign = aircraft.flight ? aircraft.flight.trim() : 'N/A';
        const altitude = aircraft.alt_baro || aircraft.alt_geom || 'N/A';
        const speed = aircraft.gs || 'N/A';
        const track = aircraft.track || 'N/A';
        const squawk = aircraft.squawk || 'N/A';
        const registration = aircraft.r || aircraft.reg || 'N/A';
        
        // Create FlightAware link if we have registration or callsign
        const faUrl = this.flightAwareUrl(aircraft);
        const fr24Link = faUrl
            ? `<div style="margin-top: 8px;"><a href="${esc(faUrl)}" target="_blank" rel="noopener noreferrer" style="color: #00aaff; text-decoration: none; font-weight: bold;">📡 View on FlightAware</a></div>`
            : '';
        
        return `
            <div class="popup-callsign">${esc(callsign)}</div>
            <div class="popup-details">
                <div><strong>Hex:</strong> ${esc(aircraft.hex)}</div>
                ${registration !== 'N/A' ? `<div><strong>Registration:</strong> ${esc(registration)}</div>` : ''}
                <div><strong>Altitude:</strong> ${esc(altitude)} ft</div>
                <div><strong>Speed:</strong> ${esc(speed)} kts</div>
                <div><strong>Track:</strong> ${esc(track)}°</div>
                <div><strong>Squawk:</strong> ${esc(squawk)}</div>
                ${aircraft.category ? `<div><strong>Category:</strong> ${esc(aircraft.category)}</div>` : ''}
                ${fr24Link}
            </div>
        `;
    }

    updateAircraftList(aircraft) {
        const listContainer = document.getElementById('aircraft-items');
        listContainer.innerHTML = '';
        
        // Sort by callsign, then by hex
        aircraft.sort((a, b) => {
            const aCall = a.flight ? a.flight.trim() : a.hex;
            const bCall = b.flight ? b.flight.trim() : b.hex;
            return aCall.localeCompare(bCall);
        });
        
        aircraft.forEach(ac => {
            const item = document.createElement('div');
            item.className = 'aircraft-item';
            
            const callsign = ac.flight ? ac.flight.trim() : ac.hex;
            const altitude = ac.alt_baro || ac.alt_geom || 'N/A';
            const speed = ac.gs || 'N/A';
            
            item.innerHTML = `
                <div class="aircraft-callsign">${this.escapeHtml(callsign)}</div>
                <div class="aircraft-details">
                    <span class="aircraft-altitude">${this.escapeHtml(altitude)} ft</span> | 
                    <span class="aircraft-speed">${this.escapeHtml(speed)} kts</span>
                </div>
            `;
            
            // Click to center on aircraft
            item.addEventListener('click', () => {
                if (ac.lat && ac.lon && this.aircraftMarkers[ac.hex]) {
                    this.map.setView([ac.lat, ac.lon], 12);
                    this.aircraftMarkers[ac.hex].openPopup();
                }
            });
            
            listContainer.appendChild(item);
        });
    }

    updateStats(stats) {
        document.getElementById('aircraft-count').textContent = 
            `${stats.total_aircraft} aircraft`;
        
        const lastUpdate = stats.last_update ? 
            new Date(stats.last_update * 1000).toLocaleTimeString() : '--';
        document.getElementById('last-update').textContent = 
            `Last update: ${lastUpdate}`;
    }

    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('connection-status');
        statusElement.textContent = connected ? 'Connected' : 'Disconnected';
        statusElement.className = connected ? 'status-connected' : 'status-disconnected';
    }
}

// Initialize the tracker when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new AircraftTracker();
});