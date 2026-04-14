# FM Avlysning — Copilot Instructions

## Project Overview

A service that shows active restrictions (avlysningar) for Swedish Armed Forces (Försvarsmakten) training and shooting ranges on an interactive map. Built as a PWA with offline-first approach, targeting deployment on Cloudflare (Pages + R2 + Workers). Currently in local MVP phase.

## Architecture

```
fm-avlysning/
├── frontend/           # React + Vite + TypeScript + MapLibre GL JS
├── scraper/            # Python scraper (requests, beautifulsoup4, pdfplumber)
├── data/               # GeoJSON polygons, generated status JSON, sample data
│   ├── skjutfalt.geojson          # Shooting range polygons (from OSM)
│   └── skjutfalt_status.json      # Scraped restriction data (generated)
├── docs/               # Project documentation
│   ├── Idea.md
│   └── URL-källor för Scraping av Skjutfält.md
├── AGENTS.md           # This file
└── RESEARCH.md         # Scraping research, HTML structure analysis, geodata sources
```

## Tech Stack

- **Frontend:** React 18+ with TypeScript, Vite, MapLibre GL JS
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
  "last_updated": "2026-04-14T12:00:00Z",
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
          "sectors": ["all"]
        }
      ]
    }
  ]
}
```

### skjutfalt.geojson
Standard GeoJSON FeatureCollection. Each Feature has:
- `geometry`: Polygon or MultiPolygon
- `properties.id`: Matches the `id` in skjutfalt_status.json
- `properties.name`: Human-readable name
- `properties.source`: "osm" | "manual" | "lantmateriet"

## Scraping Sources

| Source | Type | URL Pattern |
|--------|------|-------------|
| FM samlingssida | Paginated HTML → individual pages → PDF | `forsvarsmakten.se/regler-och-tillstand/skjutfalt-och-forbud/` |
| FM Älvdalen | Direct | `forsvarsmakten.se/.../alvdalens-skjutfalt/` |
| FM Tåme | Direct | `forsvarsmakten.se/.../tame-skjutfalt/` |
| FM Amf1 | Direct | `forsvarsmakten.se/.../stockholms-amfibieregemente-amf-1/...` |
| skjutfalten.se | HTML sectors | `skjutfalten.se/avlysningar/DD/MM/YYYY` |
| Falun kommun | HTML | `falun.se/.../skjutvarningar-pa-militaromradet.html` |
| Strängnäs kommun | HTML | `strangnas.se/.../harads-skjutfalt` |
| Vårgårda kommun | HTML | `vargarda.se/.../remmene-skjutfalt.html` |

## Important UX Requirements

1. **Timestamp**: Always show when data was last scraped
2. **Offline indicator**: Yellow theme when offline, inform user data may be stale
3. **Disclaimer**: This is NOT an official FM service. Physical signage (gates, red lights, warning signs) at the field always takes legal precedence
4. **Sync status**: Show warning when new PDF detected but not yet processed

## Commands

```bash
# Frontend
cd frontend && npm run dev        # Start dev server
cd frontend && npm run build      # Production build

# Scraper
cd scraper && pip install -r requirements.txt
cd scraper && python main.py      # Run full scrape
cd scraper && python main.py --source fm    # Scrape only FM
cd scraper && python main.py --source bofors # Scrape only skjutfalten.se

# Docker (scraper)
docker build -t fm-scraper ./scraper
docker run fm-scraper
```
