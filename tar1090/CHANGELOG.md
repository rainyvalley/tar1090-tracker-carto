# Changelog

All notable changes to the Tar1090 Aircraft Tracker will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Trails** toggle in the toolbar draws where each aircraft has flown. The
  add-on records every aircraft's path (a point every 5 s, up to an hour), so
  turning trails on, or opening the map, shows the whole path rather than
  only what was seen since the page loaded. The choice is remembered per
  browser; `show_history` sets the default. New endpoint `/api/trails`

## [1.2.1] - 2026-10-09

Fix add-on start-up after 1.2.0 (Supervisor API forbidden)

### Fixed
- Add-on failed to start after updating to 1.2.0 ("Unable to access the API,
  forbidden" in a restart loop): options are now read from
  `/data/options.json` instead of through the Supervisor API

## [1.2.0] - 2026-10-09

Audit release: stale-data detection, Alpine 3.22, optional direct port, UI and release fixes

### Added
- Optional direct port (`5000/tcp`), off by default; enable it under the
  add-on's Network settings for REST sensors or a plain iframe

### Fixed
- The map no longer shows frozen aircraft as live when tar1090 stops answering:
  the API serves no aircraft once data is stale, `/api/health` reports
  `degraded`, and the header says "tar1090 unreachable"
- `auto_center` now works, and `show_history` sets whether trails are on at start
- Aircraft on the ground are coloured as low altitude and shown as "Ground";
  zero values (heading north, stationary, lat/lon 0) are no longer "N/A"
- Icon colour and size follow altitude and type changes; trails use the
  aircraft's colour; hovering no longer resets the heading
- Markers are removed when an aircraft loses its position
- Malformed tar1090 data no longer causes HTTP 500s or stops the map updating
- `tar1090_host` values with a scheme or port (`http://host`, `host:8080`) work
- `/api/history` (as documented) now exists, as an alias of `/api/aircraft/history`
- Standalone `simple-start.sh` works from a checkout and serves the UI
- Release script and release workflow fixes

### Changed
- `/api/history` keeps the last 12 snapshots instead of 100
- Repository, maintainer and image labels point at rainyvalley/tar1090-tracker-carto
- Base image moved from Alpine 3.18 (end of life) to 3.22
- Served by Waitress instead of Flask's development server; quieter logs
- Supervisor watchdog on `/ping`
- Bounded memory: aircraft.json responses over 10 MB are rejected

## [1.1.0] - 2026-10-08

### Changed
- Carto Light, Dark and Voyager now render from Carto's **vector** styles (Positron,
  Dark Matter, Voyager GL) through MapLibre GL, bridged into the existing Leaflet map.
  Since 2026-09-25 Carto's raster tiles show "API KEY REQUIRED" without a key; the
  vector styles load without one, so the map works out of the box again.
  Existing `map_provider` values are unchanged.
- `carto_api_key` is now optional but recommended: when set, it is added to every
  Carto request so the map keeps working if Carto extends the key requirement to vector
- Leaflet, MapLibre GL (5.24.0) and maplibre-gl-leaflet (0.1.4) are bundled with the
  add-on instead of loaded from unpkg
- Python dependencies are installed from Alpine packages instead of unpinned pip

### Added
- Fallback for browsers without WebGL: Carto raster tiles when a key is set,
  otherwise Esri satellite (unavailable providers are removed from the dropdown)
- Console error, and switch to satellite, if Carto rejects the vector style (401/403)
- Content-Security-Policy, `X-Content-Type-Options` and `Referrer-Policy` headers

### Security
- Escape aircraft data (callsign, registration, etc.) in popups and the aircraft list;
  previously crafted values were injected as HTML
- FlightAware links URL-encode the ident
- `carto_api_key` is no longer written to the add-on log (startup no longer dumps
  `options.json`, and config logging redacts it)

### Removed
- Unused `nginx`, `curl`, `jq`, `py3-pip` and `schedule` from the image

## [1.0.15] - 2026-09-13

### Changed
- Aircraft list is now **closed by default**; open it with the "Show Aircraft List" button
- Aircraft list is anchored inside the map area instead of the page, so it no longer
  overlaps the header or the control buttons

### Added
- Close (×) button on the aircraft list panel itself
- Mobile layout (<= 768px): header and controls stack and wrap, buttons get a 40px
  touch target, and the aircraft list docks as a bottom sheet capped at 45vh
  instead of a fixed 300px panel covering the screen

### Fixed
- List toggle now uses a CSS class instead of an inline `display` style, so the
  first tap no longer behaves backwards when the list starts hidden

## [1.0.14]

## [1.0.13] - 2025-07-30

### Fixed
- Replaced star-shaped aircraft icons with proper Material Design airplane icons
- Used clean, recognizable aircraft SVG from Material Design icon set
- Optimized icon sizes (20-32px) for better visibility and performance
- Enhanced aircraft icon styling with proper outline and fill

## [1.0.12] - 2025-07-30

### Added
- FlightRadar24 integration - click aircraft icons to view on FR24
- Registration display in aircraft popup details
- Enhanced aircraft SVG icons with cockpit and wing highlights
- Right-click and Ctrl+click support for direct FR24 links

### Changed  
- Improved aircraft icon design with larger, more visible airplane shapes
- Increased default icon sizes for better visibility (24-36px range)
- Enhanced SVG with 32x32 viewBox for better scaling

### Fixed
- Replaced pin-style markers with proper airplane-shaped icons
- Better aircraft icon visibility and contrast on map

## [1.0.11] - 2025-07-30

### Added
- Improved aircraft icon visibility and rendering
- Better SVG aircraft icons with enhanced styling

### Changed
- Changed default map center from New York to UK (54.7023, -3.2765)
- Enhanced aircraft icon CSS with stronger drop shadows and better contrast
- Improved aircraft icon rotation handling for smoother updates

### Fixed
- Fixed missing aircraft icons on map display
- Resolved SVG rendering issues in Leaflet markers
- Enhanced icon visibility with better styling and positioning

## [1.0.10] - 2025-07-30

### Fixed
- Fixed API routing issues in Home Assistant ingress mode
- Resolved all 404 errors for aircraft, stats, and config endpoints
- Simplified JavaScript API URL patterns for better ingress compatibility

### Technical
- Added dual route decorators to Flask app (with and without /api/ prefix)
- Optimized fetchAPI() function to use simple relative paths first
- Enhanced URL fallback strategy for different deployment scenarios

## [1.0.9] - 2025-07-30

### Fixed
- Fixed missing changelog issue in Home Assistant addon interface
- Added CHANGELOG.md file to addon directory for HA compatibility

### Technical
- Copied changelog to /tar1090/CHANGELOG.md for proper HA addon store integration
- Ensured changelog is accessible through HA addon interface

## [1.0.8] - 2025-07-30

### Fixed
- Fixed web interface API connection issues in Home Assistant ingress mode
- Resolved "disconnected" status showing despite successful tar1090 connection
- Added intelligent API URL detection for different deployment scenarios

### Technical
- Enhanced JavaScript fetchAPI() function with multiple URL fallback strategies
- Improved error handling for API requests in ingress environments
- Added comprehensive URL pattern matching for HA integration

## [1.0.7] - 2025-07-30

### Fixed
- Resolved 502 gateway errors caused by null configuration values
- Fixed environment variable handling when values come as 'null' strings
- Improved configuration reading with proper JSON fallback

### Technical
- Enhanced get_config_value() function with null value detection
- Added proper error handling for configuration file reading
- Improved logging for configuration debugging

## [1.0.6] - 2025-07-30

### Fixed
- Fixed configuration validation errors in Home Assistant
- Corrected float schema format in config.yaml
- Added required arch field for multi-architecture support

### Technical
- Updated config.yaml with proper YAML schema validation
- Fixed addon structure for Home Assistant compatibility

## [1.0.5] - 2025-07-30

### Added
- Professional repository structure for Home Assistant addon store
- Automated release management with version tagging
- Repository metadata and addon store integration

### Technical
- Added repository.json for HA addon store compatibility
- Created release.sh script for automated version management
- Structured addon files in proper subdirectory

## [1.0.4] - 2025-07-29

### Added
- Git repository initialization and version control
- Main branch as default (removed master branch)
- Comprehensive commit history and changelog integration

### Technical
- Initialized git repository with proper branching
- Added .gitignore for Python and Node.js projects
- Linked commits to changelog documentation

## [1.0.3] - 2025-07-29

### Added
- Comprehensive Home Assistant configuration interface
- New `auto_center` option to automatically center map on aircraft
- User-configurable tar1090 server IP and port through HA UI
- Input validation and default values for all configuration options
- Step-by-step configuration guide in README

### Changed
- Enhanced config.yaml with proper schema validation
- Updated Python app to read all configuration variables from HA
- Default tar1090_host changed from hardcoded IP to user-configurable
- Improved README with detailed configuration instructions

### Technical
- Modified run.sh to pass all configuration variables to Python app
- Added AUTO_CENTER environment variable support
- Enhanced configuration API endpoint with new options

## [1.0.2] - 2025-07-29

### Added
- Enhanced aircraft icons with proper airplane shapes instead of circles
- Aircraft icons now rotate based on flight heading/track direction
- Dynamic icon sizing based on aircraft type (A380/B747 larger, regional smaller)
- Altitude-based color coding (red=low, orange=medium, blue=high, green=very high)
- Hideable aircraft list panel with toggle button
- Hover effects with scaling and drop shadows on aircraft icons
- Red center dot on aircraft icons for better visibility

### Changed
- Replaced simple circular markers with detailed aircraft SVG icons
- Improved aircraft marker CSS with proper transparency and effects

### Technical
- Added `getAircraftIconSize()` function for dynamic sizing
- Enhanced `aircraft-marker` CSS classes with animation support
- Added toggle functionality for aircraft list visibility

## [1.0.1] - 2025-07-29

### Added
- Home Assistant ingress support for seamless dashboard integration
- Aircraft tracker now appears directly in HA sidebar with airplane icon
- Panel icon configuration for better HA integration

### Changed
- Simplified Flask app to serve static files directly for ingress mode
- Removed nginx dependency when running in ingress mode
- Updated configuration for better HA compatibility

### Technical
- Modified config.yaml to enable ingress mode
- Updated Flask app routes to serve static content
- Fixed config validation issues with float schema

## [1.0.0] - 2025-07-29

### Added
- Initial release of Tar1090 Aircraft Tracker
- Real-time aircraft tracking from tar1090 servers
- Interactive Leaflet-based map with OpenStreetMap and satellite layers
- Aircraft position display with clickable details (callsign, altitude, speed, track)
- Optional flight history trails showing aircraft movement
- Dark theme interface optimized for Home Assistant
- REST API with multiple endpoints (/aircraft, /health, /stats, /config, /history)
- Home Assistant add-on structure with proper Docker configuration
- Standalone installation option for systems without add-on support
- Multi-architecture support (aarch64, amd64, armhf, armv7, i386)

### Features
- Configurable update intervals (1-60 seconds)
- Customizable map center coordinates and zoom levels
- Aircraft statistics and health monitoring
- Connection status indicator
- Responsive web interface
- Multiple dashboard integration methods (Webpage Card, Panel, Map integration)

### Technical
- Python Flask backend for API and data processing
- Nginx reverse proxy for web serving
- Background threading for continuous data updates
- Docker containerization with Home Assistant base images
- bashio integration for Home Assistant configuration management

## [Initial Development] - 2025-07-29

### Development Milestones
- Created interactive web interface with Leaflet maps
- Implemented aircraft data fetching from tar1090 API
- Added CSS styling with dark theme
- Developed JavaScript for real-time map updates
- Built Docker containerization
- Created Home Assistant add-on structure
- Implemented repository structure for HA add-on store

---

## Release Notes

### Upgrade Instructions
- For Home Assistant add-on users: Update through the add-on store
- For standalone users: Download the latest release and restart the service

### Breaking Changes
- None in current releases

### Security Updates
- All releases include security best practices
- No known vulnerabilities in current versions

### Support
- Report issues: [GitHub Issues](https://github.com/rainyvalley/tar1090-tracker-carto/issues)
- Documentation: [README.md](README.md)
- Discussions: [GitHub Discussions](https://github.com/rainyvalley/tar1090-tracker-carto/discussions)

[Unreleased]: https://github.com/rainyvalley/tar1090-tracker-carto/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/rainyvalley/tar1090-tracker-carto/compare/v1.2.1...v1.3.0
[1.2.1]: https://github.com/rainyvalley/tar1090-tracker-carto/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/rainyvalley/tar1090-tracker-carto/compare/7b11673...v1.2.0
