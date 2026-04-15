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
- **Karta** — MapLibre GL JS med OSM-tiles, militära polygoner från GeoJSON
- **Färgkodning** — Röd (aktivt idag), grön (inga restriktioner), grå (okänt)
- **Fältlista** — Scrollbar lista med alla avlysta fält och tidsbadges
- **Infopanel** — Klicka för att se detaljer, typ, tider och PDF-källlänkar
- **GPS** — GeolocateControl för att hitta närmaste fält
- **Disclaimer** — Tydlig varning att tjänsten inte är officiell

### Data
- **GeoJSON** — 313 OSM-polygoner (161 namngivna) från Geofabrik-extrakt
- **Status-JSON** — 79 fält, 858 restriktioner (2026-04-15)

## Kända begränsningar ⚠️

### Namnmatchning GeoJSON ↔ Status (43/75 = 57%)
FM använder långa officiella namn (t.ex. "Bodens södra och Kusträsks övnings- och skjutfält") medan OSM har kortare namn ("Bodens skjutfält"). 32 fält saknar koppling till kartpolygon. Behöver fuzzy matching eller en manuell mappningstabell.

Omatchade fält inkluderar bl.a.: Askö, Bollö, Bråt, Eksjö, Grebbegården, Husie, Kalixfors, Karlskrona inre öar, Kungsängen, Lombens/Orrträsk, Norra Åsum, Sisjön, Skillingaryd, Tåme, Villingsberg, Vällinge, m.fl.

### Omatchade PDFer — LÖST ✅
Alla FM-PDFer (163 st) parsas nu korrekt. 19 parsers + 5 snabbkontroller (statisk info, ingen farlig verksamhet, alla NEJ, inget tillträdesförbud, övningsinformation).

### Ej testat i kombination
- `--source all` (FM + Bofors + Kommun samtidigt) har inte körts end-to-end
- Kommun-scrapern har inte verifierats mot live-sidor

### Ej implementerat
- **PWA / offline-stöd** — Service worker, manifest
- **Cloudflare-deploy** — Pages, R2, Workers
- **Automatisk uppdatering** — Schemalagd scraping (cron / Cloudflare Worker)
- **Mobilanpassning** — Grundläggande responsivitet finns men ej optimerad
- **Synkstatus** — Visa om ny PDF upptäcks men inte parsats

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
| Namnmatchningar (exakt) | 43/79 |
| Namnmatchningar (med mappning) | 59/79 |
| Restriktioner (dedupade) | 858 |
| Fält med aktiva restriktioner | 62 |
| Frontend-komponenter | 4 (Map, InfoPanel, FieldList, Disclaimer) |
| Cachade filer | ~170 (API + PDFer + HTML) |
