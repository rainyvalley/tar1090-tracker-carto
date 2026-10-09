Vendored third-party front-end libraries, served locally so the map does not
depend on a CDN being reachable from the viewer's browser.

| Library | Version | Source |
|---|---|---|
| Leaflet | 1.9.4 | https://unpkg.com/leaflet@1.9.4/dist/ |
| MapLibre GL JS | 5.24.0 | https://unpkg.com/maplibre-gl@5.24.0/dist/ |
| @maplibre/maplibre-gl-leaflet | 0.1.4 | https://unpkg.com/@maplibre/maplibre-gl-leaflet@0.1.4/ |

MapLibre is pinned to 5.x because 6.x ships ES modules only, while the
Leaflet bridge expects the global `maplibregl` from the UMD build.
Checksums are in SHA256SUMS (`sha256sum -c SHA256SUMS`).
