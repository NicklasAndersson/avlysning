# FM Avlysning — Projektstatus

> Senast uppdaterad: 2026-04-15

## Översikt

Lokal MVP som visar aktiva avlysningar för svenska skjut- och övningsfält på en interaktiv karta. Appen hämtar data genom scraping av Försvarsmaktens PDFer och andra källor, och visar dem med MapLibre GL JS.

## Vad som fungerar ✅

### Scraper
- **FM JSON API** — Hämtar alla 75 skjutfält via `forsvarsmakten.se/api/searchapi/get-firing-ranges`
- **PDF-parsning** — 19 formatspecifika parsers + 5 snabbkontroller, 100% täckning av alla FM-PDFer
- **Bofors-scraper** — Hämtar 7 dagars sektorstatus från `skjutfalten.se`
- **Kommun-scraper** — Stödjer Falun, Strängnäs (Härads), Vårgårda (Remmene)
- **Diskcache** — SHA-256-baserad cache i `tmp/cache/`, default TTL 24h
- **CLI** — `--source {fm|bofors|kommun|all}`, `--no-cache`, `--cache-ttl`
- **Deduplicering** — Identiska restriktioner från flera PDFer filtreras bort
- **PDF-länk per restriktion** — Varje restriktion har `source_url` till käll-PDFen

### Frontend
- **Karta** — MapLibre GL JS med självhostade vektortiles (PMTiles), militära polygoner från GeoJSON
- **Färgkodning** — Röd (aktivt nu), gul (idag men ej just nu), grön (inga restriktioner), svart (permanent tillträdesförbud), grå (okänt)
- **Datum/tid-väljare** — Välj annan tid, auto-tick varje 60s i live-läge
- **Fältlista** — Scrollbar lista med alla avlysta fält och tidsbadges
- **Infopanel** — Klicka för att se detaljer, typ, tider och PDF-källlänkar. Permanent tillträdesförbud visas för garnisoner
- **GPS** — GeolocateControl för att hitta närmaste fält
- **Disclaimer** — Tydlig varning att tjänsten inte är officiell
- **PWA** — Manifest, service worker (vite-plugin-pwa), offline-cache med NetworkFirst för statusdata, CacheFirst för GeoJSON/PMTiles
- **Mobilanpassning** — Responsiv header, InfoPanel som bottom sheet, touch-vänliga knappar, safe-area-insets

### Data
- **GeoJSON** — 313 OSM-polygoner (161 namngivna) från Geofabrik-extrakt
- **Status-JSON** — 79 fält, 858 restriktioner (2026-04-15)
- **PMTiles** — Självhostade vektortiles (911 MB) genererade med Tilemaker från sweden-latest.osm.pbf
- **Permanenta tillträdesförbud** — 16 garnisoner/örlogsbaser definierade i field_config.json

## Kända begränsningar ⚠️

### Namnmatchning GeoJSON ↔ Status (64/79 = 81%)
19 manuella mappningar i `nameMapping.ts`. 15 fält saknar GeoJSON-polygon i OSM-datat — dessa behöver manuella polygoner.

Omatchade (saknar polygon): Askö, Eksjö, Gisslingö, Husie, Korsö, Kråk, Mellsten, Norra Åsum, Nytorp, Romeleklint, Roten, Sisjön, Stabbo, Söderarm, Önnarp.

### Omatchade PDFer — LÖST ✅
Alla FM-PDFer (163 st) parsas nu korrekt. 19 parsers + 5 snabbkontroller (statisk info, ingen farlig verksamhet, alla NEJ, inget tillträdesförbud, övningsinformation).

### Ej testat / verifierat
- Kommun-scrapern har inte verifierats mot live-sidor nyligen

### Ej implementerat
- **Cloudflare-deploy** — Pages, R2, Workers (plan finns i docs/pmtiles.md)
- **Automatisk uppdatering** — Schemalagd scraping (cron / Cloudflare Worker)
- **Synkstatus** — Visa om ny PDF upptäcks men inte parsats
- **Kustlinje/hav** — PMTiles saknar coastline-data (Tilemaker behöver get-coastline.sh)
- **PMTiles-generering** — Separat arbetsflöde, behöver inte dagliga uppdateringar. Kartdata (PMTiles, GeoJSON) ändras sällan och byggs/laddas upp manuellt vid behov

## Siffror

| Mätvärde | Värde |
|----------|-------|
| FM-fält via API | 75 |
| Bofors-fält | 1 |
| Kommun-fält | 3 (Falun, Strängnäs, Vårgårda) |
| **Totalt fält** | **79** |
| PDF-parsers | 19 |
| Snabbkontroller (pre-checks) | 5 |
| Omatchade PDFer | **0** |
| GeoJSON-polygoner | 313 (161 namngivna) |
| Namnmatchningar (exakt + case) | 45/79 |
| Namnmatchningar (med mappning) | 64/79 |
| Restriktioner (dedupade) | 858 |
| Fält med aktiva restriktioner | 62 |
| Frontend-komponenter | 4 (Map, InfoPanel, FieldList, Disclaimer) |
| PMTiles storlek | 911 MB |
| Cachade filer | ~170 (API + PDFer + HTML) |
