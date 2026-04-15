# PMTiles — Steg-för-steg-plan

Mål: Ersätta externa OSM raster-tiles med en självhostad vektorbaserad karta via PMTiles på Cloudflare R2.

Källa: https://dev.to/aaronblondeau/self-hosted-maps-for-practically-free-1i3n

## Översikt

| Komponent | Uppgift |
|-----------|---------|
| Tile-data | Sverige OSM PBF → Tilemaker → `sweden.pmtiles` |
| Frontend | `pmtiles` + `@protomaps/basemaps` npm-paket, uppdatera MapLibre-stilen |
| Hosting | Cloudflare R2 bucket + Worker (range requests, CORS, caching) |
| Assets | Fonter + sprites (Protomaps CDN eller self-hosted på R2) |

> **OBS:** `tmp/sweden-latest-free.shp.zip` är ett Shapefile-extrakt (enbart tematiska lager).
> Det räcker INTE för att bygga en basemap — vi behöver `sweden-latest.osm.pbf` (~1.5 GB) från Geofabrik.

---

## Steg 1 — Ladda ner Sverige OSM-data

```bash
cd tmp
wget https://download.geofabrik.de/europe/sweden-latest.osm.pbf
# ~1.5 GB, tar några minuter
```

---

## Steg 2 — Installera Tilemaker

```bash
brew install tilemaker
```

Eller med Docker:
```bash
docker pull ghcr.io/systemed/tilemaker:latest
```

Tilemaker konverterar `.osm.pbf` → `.pmtiles` med hjälp av konfigfiler (`.json` + `.lua`) som styr vilka lager och features som inkluderas.

---

## Steg 3 — Generera PMTiles med Tilemaker

Tilemaker har inbyggda konfigfiler (`resources/config-openmaptiles.json` + `resources/process-openmaptiles.lua`) som producerar OpenMapTiles-kompatibla lager.

```bash
# Hämta kustlinjer och landcover (krävs för openmaptiles-profilen)
cd /opt/homebrew/share/tilemaker  # eller tilemaker repo dir
./resources/get-coastline.sh
./resources/get-landcover.sh

# Kör tilemaker
tilemaker \
  --input tmp/sweden-latest.osm.pbf \
  --output tmp/sweden.pmtiles \
  --config /opt/homebrew/share/tilemaker/resources/config-openmaptiles.json \
  --process /opt/homebrew/share/tilemaker/resources/process-openmaptiles.lua
```

Alternativt med Docker:
```bash
docker run -v $(pwd)/tmp:/data ghcr.io/systemed/tilemaker:latest \
  --input /data/sweden-latest.osm.pbf \
  --output /data/sweden.pmtiles
```

Uppskattad tid: 5–15 min för Sverige. Uppskattad storlek: **200–500 MB**.

---

## Steg 4 — Förhandsvisa

Öppna https://pmtiles.io/ och dra in `sweden.pmtiles` (eller peka på en lokal URL).
Bocka i "Background" för att se basen. Zooma till Sverige.

---

## Steg 5 — Frontend: Installera npm-paket

```bash
cd frontend
npm install pmtiles
```

> **OBS:** Tilemaker med openmaptiles-profilen producerar OpenMapTiles-schema.
> För styling kan vi använda en färdig OpenMapTiles-stil (t.ex. OSM Bright)
> eller bygga egen i Maputnik (https://maplibre.org/maputnik).

---

## Steg 6 — Frontend: Uppdatera Map.tsx

### 6a. Registrera PMTiles-protokollet

```ts
import { Protocol } from "pmtiles"

// I useEffect (en gång vid mount):
const protocol = new Protocol()
maplibregl.addProtocol("pmtiles", protocol.tile)
// Cleanup:
return () => maplibregl.removeProtocol("pmtiles")
```

### 6b. Byt ut map style

Nuvarande (raster):
```ts
style: {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
    }
  },
  layers: [{ id: "osm-tiles", type: "raster", source: "osm" }]
}
```

Nytt (vektor PMTiles med OpenMapTiles-schema):
```ts
style: {
  version: 8,
  glyphs: "https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf",
  sprite: "https://protomaps.github.io/basemaps-assets/sprites/v4/light",
  sources: {
    openmaptiles: {
      type: "vector",
      url: `pmtiles://${PMTILES_URL}`,
      attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a>'
    }
  },
  layers: [/* OpenMapTiles-stil, se steg 7 */]
}
```

### 6c. Miljövariabler (Vite)

Styr tiles-URL via env så lokal dev kan använda en lokal fil:
```ts
const PMTILES_URL = import.meta.env.VITE_PMTILES_URL
  ?? "http://localhost:5173/data/sweden.pmtiles"
```

`.env.production`:
```
VITE_PMTILES_URL=https://tiles.avlysning.se/sweden.pmtiles
```

---

## Steg 7 — Kartstil (Map Style)

Tilemaker med openmaptiles-profilen producerar standardlager som `water`, `landuse`,
`transportation`, `building`, `place`, etc.

### Alternativ A: Använd färdig stil
Ladda ner en OpenMapTiles-kompatibel stil (t.ex. OSM Bright, Positron):
- https://openmaptiles.org/styles/
- Byt `sources`-URL:en i stil-JSON:en till din PMTiles-URL

### Alternativ B: Bygg stil i Maputnik
1. Öppna https://maplibre.org/maputnik
2. Lägg till källa: Vector (PMTiles) → peka på din `.pmtiles`
3. Experimentera med lager och färger
4. Exportera stil-JSON → spara i projektet

---

## Steg 8 — Lokal utveckling

Placera `sweden.pmtiles` i `tmp/` och skapa symlink:
```bash
ln -s ../../tmp/sweden.pmtiles frontend/public/data/sweden.pmtiles
```
MapLibre + pmtiles-protokollet hanterar range requests mot Vite dev-server.

---

## Steg 9 — Cloudflare R2 + Worker

### 9a. Skapa R2 bucket

```bash
npx wrangler r2 bucket create fm-avlysning-tiles
```

### 9b. Ladda upp PMTiles till R2

```bash
# rclone rekommenderas för filer > 300 MB
rclone copyto sweden.pmtiles r2:fm-avlysning-tiles/sweden.pmtiles \
  --progress --s3-chunk-size=256M
```

### 9c. Deploy PMTiles Worker

Workern hanterar range requests, CORS och CDN-caching.

1. Klona worker-koden från https://github.com/protomaps/PMTiles/tree/main/serverless/cloudflare
2. Konfigurera `wrangler.toml`:
   ```toml
   name = "fm-tiles"
   main = "index.ts"
   compatibility_date = "2024-01-01"

   [[r2_buckets]]
   binding = "BUCKET"
   bucket_name = "fm-avlysning-tiles"

   [vars]
   ALLOWED_ORIGINS = "https://avlysning.se,http://localhost:5173"
   CACHE_CONTROL = "public, max-age=86400"
   ```
3. Deploya: `npx wrangler deploy`
4. **Tilldela en custom domain** (t.ex. `tiles.avlysning.se`) — workers.dev-domäner cachar inte.

---

## Steg 10 — Verifiera

- [ ] Kartan renderas med vektortiles (labels på svenska)
- [ ] Skjutfälts-polygoner ritas ovanpå baskartan med korrekt färgkodning
- [ ] Range requests fungerar (kolla Network-fliken — inga 200 på hela filen, bara 206 Partial Content)
- [ ] CORS fungerar från frontend-domänen
- [ ] Fonter och sprites laddas korrekt

---

## Kostnad (uppskattning)

| Resurs | Uppskattning |
|--------|-------------|
| R2 lagring | ~500 MB = ~$0.01/mån |
| R2 läsningar | Class A: $0.36/M, Class B: $4.50/M (cache minskar) |
| Worker | $5/mån (inkl 10M req) |
| **Totalt** | **~$5–6/mån** vid låg trafik |

---

## Tidsordning

1. **Ladda ner .osm.pbf + installera Tilemaker** (steg 1–2) — kan göras nu
2. **Generera sweden.pmtiles** (steg 3) — ~15 min
3. **Förhandsvisa på pmtiles.io** (steg 4) — verifiera att datan ser bra ut
4. **Frontend-integration** (steg 5–6) — testa lokalt med filen
5. **Kartstil** (steg 7) — välj/bygg stil
6. **R2 + Worker** (steg 9) — behövs först vid deploy
