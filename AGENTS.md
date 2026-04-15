# FM Avlysning — Copilot Instructions

## Project Overview

A service that shows active restrictions (avlysningar) for Swedish Armed Forces (Försvarsmakten) training and shooting ranges on an interactive map. Built as a PWA with offline-first approach, targeting deployment on Cloudflare (Pages + R2 + Workers). Currently in local MVP phase.

## Architecture

```
fm-avlysning/
├── frontend/           # React + Vite + TypeScript + MapLibre GL JS
│   └── public/data/    # Symlink → ../../data/ (Vite serves directly)
├── scraper/            # Python scraper (requests, beautifulsoup4, pdfplumber)
│   └── scrapers/
│       ├── fm.py       # Försvarsmakten JSON API + PDF-parsning
│       ├── bofors.py   # skjutfalten.se HTML-scraper
│       ├── kommun.py   # Kommunsidor (Falun, Strängnäs, Vårgårda)
│       └── fm_parsers/ # 19 formatspecifika PDF-parsers
├── data/               # Genererade datafiler (källa för frontend via symlink)
│   ├── skjutfalt.geojson      # Militära polygoner (313 st, från OSM/Geofabrik)
│   ├── skjutfalt_status.json  # Scrapad restriktionsdata (genererad av scraper)
│   └── field_config.json      # Mappning: FM-fältnamn → OSM polygon-ID:n
├── docs/               # Projektdokumentation
│   ├── Idea.md         # Ursprunglig vision / systemarkitektur
│   ├── STATUS.md       # Projektstatus — vad som är gjort och kvarstår
│   ├── DECISIONS.md    # Tekniska beslut och designval
│   ├── MAPPING.md      # Namnmappningstabell (autogenererad)
│   └── URL-källor för Scraping av Skjutfält.md
├── AGENTS.md           # This file
└── RESEARCH.md         # Scraping-forskning, geodata-källor
```

## Tech Stack

- **Frontend:** React 19 with TypeScript, Vite 6, MapLibre GL JS
- **Map tiles:** OpenStreetMap raster tiles (local dev), PMTiles on R2 (production)
- **Scraper:** Python 3.11+, requests, beautifulsoup4, pdfplumber, lxml
- **Containerization:** Docker (scraper only)
- **Deploy target:** Cloudflare Pages (frontend), R2 (data + tiles), Workers (watchdog)

## Coding Conventions

### General
- Swedish for user-facing text, comments, and documentation
- English for code (variable names, function names, class names)
- All dates in ISO 8601 format (YYYY-MM-DD)
- All times in 24h format (HH:MM)
- UTC timestamps for `last_updated` fields

### Frontend (TypeScript/React)
- Functional components only, hooks for state
- No class components
- Strict TypeScript — no `any` types
- CSS Modules or inline styles (no CSS frameworks needed for MVP)
- Keep components small and focused

### Scraper (Python)
- Type hints on all functions
- Docstrings in Swedish
- Use `logging` module (not print)
- Rate limiting: minimum 2 second delay between requests
- Always set a descriptive User-Agent header
- Respect robots.txt
- Handle errors gracefully — log and continue, don't crash on a single field failing

## Data Format

### skjutfalt_status.json
```json
{
  "last_updated": "2026-04-15T06:02:24Z",
  "fields": [
    {
      "id": "arvidsjaur",
      "name": "Arvidsjaurs skjutfält",
      "source": "forsvarsmakten.se",
      "source_url": "https://...",
      "restrictions": [
        {
          "date": "2026-04-15",
          "start": "08:00",
          "end": "17:00",
          "type": "skjutvarning",
          "sectors": ["all"],
          "source_url": "https://...pdf"
        }
      ]
    }
  ]
}
```

### field_config.json
Maps FM field names to OSM polygon IDs. Used by frontend to connect restriction data to map polygons.
```json
{
  "fields": {
    "Arvidsjaurs skjutfält": {
      "osm_ids": ["44827950"],
      "geo_name": "Arvidsjaurs skjutfält"
    }
  }
}
```

### skjutfalt.geojson
Standard GeoJSON FeatureCollection extracted from OSM via Geofabrik + ogr2ogr. Each Feature has:
- `geometry`: Polygon or MultiPolygon
- `properties.osm_id`: OpenStreetMap way/relation ID
- `properties.name`: OSM name (may differ from FM name, or be null)
- `properties.fclass`: Always `"military"`
- `properties.code`: OSM landuse code (`7213`)

## Scraping Sources

| Source | Type | URL / API |
|--------|------|-------------|
| FM JSON API (primär) | Paginerat JSON → PDF-nedladdning → parsning | `forsvarsmakten.se/api/searchapi/get-firing-ranges?lang=sv` |
| skjutfalten.se | HTML med sektorbilder (7 dagar framåt) | `skjutfalten.se/avlysningar/DD/MM/YYYY` |
| Falun kommun | HTML-tabell | `falun.se/.../skjutvarningar-pa-militaromradet.html` |
| Strängnäs kommun | HTML-tabell | `strangnas.se/.../harads-skjutfalt` |
| Vårgårda kommun | HTML-lista | `vargarda.se/.../remmene-skjutfalt.html` |

## Important UX Requirements

1. **Timestamp**: Always show when data was last scraped
2. **Offline indicator**: Yellow theme when offline, inform user data may be stale
3. **Disclaimer**: This is NOT an official FM service. Physical signage (gates, red lights, warning signs) at the field always takes legal precedence
4. **Sync status**: Show warning when new PDF detected but not yet processed

## Geodata Pipeline

GeoJSON for shooting range polygons is extracted from OpenStreetMap data:
1. Download Sweden extract from Geofabrik: https://download.geofabrik.de/europe/sweden.html
2. Filter military features with `ogr2ogr` (GDAL) — available on this machine
3. Convert to GeoJSON → `data/skjutfalt.geojson`

Alternative: Overpass API (can be slow/unreliable for large queries).

## Commands

```bash
# Frontend
cd frontend && npm run dev        # Start dev server (port 5173)
cd frontend && npm run build      # Production build

# Scraper (kräver aktiverad venv)
cd scraper && pip install -r requirements.txt
cd scraper && python main.py --source all    # Kör alla scrapers (FM + Bofors + Kommun)
cd scraper && python main.py --source fm     # Enbart Försvarsmakten
cd scraper && python main.py --source bofors # Enbart skjutfalten.se
cd scraper && python main.py --source kommun # Enbart kommunsidor
cd scraper && python main.py --no-cache      # Utan diskcache
cd scraper && python main.py --cache-ttl 3600  # Cache-TTL i sekunder (default: 86400)
cd scraper && python main.py --output ../data/skjutfalt_status.json  # Custom output path

# Docker (scraper)
docker build -t fm-scraper ./scraper
docker run fm-scraper

# Geodata
# Download Sweden shapefile from Geofabrik, filter military features
ogr2ogr -f GeoJSON data/skjutfalt.geojson \
  tmp/gis_osm_landuse_a_free_1.shp \
  -where "fclass = 'military'"
```

## Agent Notes

- **Terminal commands can be slow.** Always use adequate timeouts (30s+ for network, 90s+ for downloads). Read the actual output before proceeding — do not assume success or failure from timing alone.
 Never assume a command failed just because the terminal output appears empty.
- **Overpass API** may timeout for large area queries. Prefer Geofabrik extracts + local processing with ogr2ogr.
- **ogr2ogr (GDAL)** is installed on this machine.
- **Temp dirs** should be in subdirectory of this project (e.g. `tmp/`) to avoid cluttering home directory. Always clean up temp files after processing.
- **Create scripts** instead of running commands manually to ensure consistency and reproducibility.
- **Python venv** finns i `scraper/.venv/`. Aktivera med `source scraper/.venv/bin/activate` innan scraper-kommandon.
- **Data-symlink**: `frontend/public/data/` → `../../data/`. Frontend ser alltid senaste scraperresultat.