# FM Avlysning — Beslut och designval

> Dokumentation av tekniska och arkitektoniska val.

## Datakällor

### FM:s interna JSON-API istället för HTML-scraping
**Beslut:** Använd `forsvarsmakten.se/api/searchapi/get-firing-ranges?lang=sv` direkt.
**Motivering:** Returnerar alla 75+ fält med dokument-URLer i ett strukturerat JSON-svar. Paginering via `&skip=N` (12 per sida). Mycket mer tillförlitligt och snabbare än att scrapa HTML-sidor.
**Alternativ som övervägdes:** Scrapa den paginerade HTML-listan → klicka in på varje fält → hitta PDF-länk. Övergavs pga komplexitet.

### PDF-parsning med formatdetektering
**Beslut:** Abstrakt `PDFParser`-basklass med `can_parse()` + `parse()`. Registry testar parsers i prioritetsordning.
**Motivering:** FM:s PDFer har minst 10+ olika format beroende på förband/region. Inget enhetligt format. Automatisk detect-and-parse med fallback till "unmatched" är mer robust än ett enda regex.
**Prioritetsordning:** Specifika parsers (Tåme, Marma, Härnösand) → regionala (Blekinge, Amf1) → generella (standard_weekly, generic_iso, yy_mm_dd, date_slash).

### Deduplicering i scraper, inte frontend
**Beslut:** FM-scrapern tar bort identiska restriktioner (samma datum+tid+typ+sektorer) innan data sparas.
**Motivering:** Flera PDFer för samma fält kan överlappa i tid, t.ex. v15+v16-PDF båda innehåller måndag v16. Utan dedup fick Boden 3 identiska rader. 779→623 restriktioner totalt.

## Geodata

### Geofabrik-extrakt + ogr2ogr istället för Overpass API
**Beslut:** Ladda ner `sweden-latest-free.shp.zip` från Geofabrik, filtrera med `ogr2ogr -where "fclass = 'military'"`.
**Motivering:** Overpass API timear ut för stora area-queries. Geofabrik-filen ger komplett data, ogr2ogr finns installerat. Resulterar i 313 features (161 namngivna).
**Nackdel:** Namnen i OSM matchar inte alltid FM:s officiella namn (57% match-rate). Kräver fuzzy matching eller manuell mappning.

### Namnmatchning via `name`-property
**Beslut:** Matcha GeoJSON-features mot status-data via `properties.name === field.name`.
**Motivering:** Enklaste lösningen. Fungerar för 43/75 fält direkt.
**Känt problem:** 32 fält omatchade. FM-namn som "Bodens södra och Kusträsks övnings- och skjutfält" finns inte i OSM. Planerad lösning: mappningstabell eller fuzzy matching.

## Frontend

### MapLibre GL JS istället för Leaflet
**Beslut:** MapLibre GL JS (WebGL-baserat).
**Motivering:** Bättre prestanda för stora GeoJSON-dataset (313 polygoner). Stöd för PMTiles i produktion. Modernt API.

### OSM raster-tiles för lokal utveckling
**Beslut:** `tile.openstreetmap.org` som tile-source under utveckling.
**Motivering:** Gratis, kräver ingen API-nyckel. I produktion byts mot PMTiles på Cloudflare R2.

### Datadriven färgkodning med `case`-expression
**Beslut:** MapLibre `case`-expression som jämför `['get', 'name']` mot Sets av aktiva/kända namn.
**Motivering:** Ger O(n) expression-byggning istället för nested if/else. Uppdateras när statusdata laddas.

### source_url per restriktion istället för per fält
**Beslut:** Varje restriktion-objekt har en `source_url` som pekar på käll-PDFen.
**Motivering:** Användaren behöver kunna verifiera datan mot originalkällan. Olika PDFer kan ge restriktioner för samma fält.

## Infrastruktur

### Diskcache med SHA-256
**Beslut:** Cacha HTTP-svar (text + binär/PDF) på disk i `tmp/cache/` med SHA-256 av URL som nyckel.
**Motivering:** FM-scraping tar 10+ minuter (75 fält × ~2 PDFer × 2s delay). Med cache tar det 14 sekunder. Krävs för snabb iteration under utveckling.
**TTL:** Default 24 timmar (`--cache-ttl 86400`). Kan stängas av med `--no-cache`.

### Venv per komponent
**Beslut:** Python venv i `scraper/.venv/`, frontend i `frontend/node_modules/`.
**Motivering:** Separata beroenden, ingen konflikt. Möjliggör Docker-isering av scraper separat.

### Data-symlink i frontend
**Beslut:** `frontend/public/data/` → `../../data/` (symlink).
**Motivering:** Vite servar filer i `public/` direkt. Symlink gör att frontend alltid ser senaste scraperresultat utan kopiering.
