# Research — FM Avlysning

> Forskning utförd innan implementation. Markerade med ✅ = löst/implementerat, se `docs/DECISIONS.md` för motiveringarna.

## Scraping-analys per källa

### 1. Försvarsmakten — Samlingssida ✅

**URL:** https://www.forsvarsmakten.se/regler-och-tillstand/skjutfalt-och-forbud/

> **Löst:** HTML-scraping övergavs till förmån för FM:s interna JSON-API (`forsvarsmakten.se/api/searchapi/get-firing-ranges?lang=sv`). Paginerat JSON med `&skip=N` (12 per sida). Returnerar alla 75 fält med dokument-URLer direkt. Se `docs/DECISIONS.md` → "FM:s interna JSON-API".

**Sidstruktur (historisk referens):**
- Paginerad lista med 79 skjutfält, 12 per sida
- Server-side rendering (ingen JS krävs för paginering)
- Varje fält visar: Namn | Arrangör (regiment) | Plats

**Kända regementen:**
- Norrlands dragonregemente (K 4)
- Stockholms amfibieregemente
- Södra skånska regementet
- Norrbottens regemente
- Älvsborgs amfibieregemente
- Västernorrlands regemente
- Göta ingenjörregemente
- Ledningsregementet
- Marinbasen

**Scraping-strategi (ersatt av JSON API):**
1. ~~Hämta alla paginerade sidor (7 sidor à 12 fält)~~
2. ~~Extrahera länk till varje fälts individuella sida~~
3. ~~På individuella sidor: hitta `<a>`-taggar med `href` som slutar på `.pdf`~~
4. ~~Filtrera PDF-länkar som innehåller "skjutvarning" eller "tilltradesforbud"~~
5. Ladda ner PDF → extrahera text med pdfplumber → parsa datum/tider ✅

**Anti-scraping:** Inget observerat. Standard statlig webbplats.

**Paginerings-URL-mönster:** ✅ Löst via JSON API (`&skip=N`, 12 per sida).

---

### 2. FM Undersidor (separata) ✅

> **Löst:** Dessa sidor behöver inte scrapas separat — JSON API:et returnerar alla fält inklusive dem som har egna undersidor.

| Fält | URL |
|------|-----|
| Älvdalen | https://www.forsvarsmakten.se/regler-och-tillstand/skjutfalt-och-forbud/alvdalens-skjutfalt/ |
| Tåme | https://www.forsvarsmakten.se/regler-och-tillstand/skjutfalt-och-forbud/tame-skjutfalt/ |
| Amf1 (Stockholms skärgård) | https://www.forsvarsmakten.se/sv/organisation/stockholms-amfibieregemente-amf-1/stockholms-amfibieregementes-skjutfalt-och-tilltradesforbud/ |

Samma strategi som samlingssidan — hitta PDF-länkar, ladda ner, parsa. ✅ Hanteras nu via JSON API.

---

### 3. skjutfalten.se (Bofors / Villingsberg) ✅

**URL:** https://skjutfalten.se/  
**Avlysningar:** https://skjutfalten.se/avlysningar/DD/MM/YYYY

**Plattform:** WordPress

**Fält:**
- Bofors Skjutfält (Saab Bofors Test Center, Karlskoga)
- Villingsbergs Skjutfält (A9 Bergslagens Artilleriregemente, Kristinehamn)

**Sektorsystem:**
- Bokstavssektorer: A, B, C, D, E (5 st)
- Nummersektorer: 1–10 + varianter (5A, 6A etc.)

**Färgkoder:**
| Färg | Betydelse |
|------|-----------|
| RÖD | TILLTRÄDESFÖRBUD — Livsfara |
| GRÖN | TILLTRÄDE — Fritt att beträda |
| GUL | EJ ANGIVET — Inget beslut fattat |

**Data i HTML:**
- Statusbilder: `map_area_a_red.png`, `map_area_1_green.png` etc.
- Referenskarta: `/files/2021/05/stor-karta-2.jpg`
- Extrahera status från bildfilnamn (röd/grön/gul)

**Datumnavigering:** URL-baserad (`/avlysningar/13/04/2026`, `/avlysningar/15/04/2026`)

**Blind-information:** Blindröjning 07:00–16:00 dagligen

**Kontakt:**
- Sektor 1-10: 0730-67 21 17
- Sektor A-E: 0586-68 001

**Copyright:** Text får citeras med källhänvisning. Bilder kräver tillstånd.

---

### 4. Kommunsidor ✅

> **Löst:** Implementerad scraper i `scraper/scrapers/kommun.py`.

| Kommun | Fält | URL |
|--------|------|-----|
| Falun | Falun Skjutfält | https://www.falun.se/stod--omsorg/trygg-och-saker/skjutvarningar-pa-militaromradet.html |
| Strängnäs | Härads skjutfält | https://www.strangnas.se/bygga-bo-och-miljo/naturomraden-och-parker/harads-skjutfalt |
| Vårgårda | Remmene skjutfält | https://www.vargarda.se/bo-bygga-och-miljo/remmene-skjutfalt.html |

**Format:** HTML-tabeller med datum och tider. Varierar per kommun.
**Anti-scraping:** Cookie-consent banners. Standard CMS-plattformar.

---

## Geodata — Skjutfältspolygoner ✅

### Status
✅ **Löst.** 313 polygoner (161 namngivna) extraherade från Geofabrik + ogr2ogr. Sparade i `data/skjutfalt.geojson`. Namnmatchning mot FM-fält: 64/79 (81%) via `field_config.json` + `nameMapping.ts`. Se `docs/DECISIONS.md` och `docs/MAPPING.md`.

### Primär källa: Geofabrik Sweden Extract + ogr2ogr

**Nedladdning:** https://download.geofabrik.de/europe/sweden.html
- `sweden-latest-free.shp.zip` (1.5 GB) — ESRI Shapefile, innehåller `gis_osm_landuse_a_free_1.shp` med `fclass='military'`
- Uppdateras dagligen
- Licens: ODbL (Open Database License)

**Extrahering med ogr2ogr:**
```bash
# Ladda ner och packa upp
wget https://download.geofabrik.de/europe/sweden-latest-free.shp.zip
unzip sweden-latest-free.shp.zip -d sweden_shp/

# Filtrera militära områden → GeoJSON
ogr2ogr -f GeoJSON data/skjutfalt.geojson \
  sweden_shp/gis_osm_landuse_a_free_1.shp \
  -where "fclass = 'military'"
```

### Alternativ: Overpass API (backup)

**Relevanta OSM-tags:**
```
landuse=military
military=range
military=training_area
military=danger_area
```

**Overpass-query:**
```
[out:json][timeout:60];
area["ISO3166-1"="SE"]->.sweden;
(
  way["landuse"="military"](area.sweden);
  relation["landuse"="military"](area.sweden);
  way["military"="range"](area.sweden);
  relation["military"="range"](area.sweden);
  way["military"="training_area"](area.sweden);
  relation["military"="training_area"](area.sweden);
  way["military"="danger_area"](area.sweden);
  relation["military"="danger_area"](area.sweden);
);
out geom;
```

**OBS:** Overpass kan timeouta vid stora queries. Geofabrik + ogr2ogr är mer tillförlitligt.

**Licens:** ODbL (Open Database License) — öppen, kräver attribution  
**Resultat:** 313 features (`fclass='military'`), varav 161 namngivna. 64 av 79 FM-fält matchade.  
**Endpoint:** https://overpass-api.de/api/interpreter

### Alternativa källor

| Källa | Format | Licens | Anmärkning |
|-------|--------|--------|------------|
| Lantmäteriet ortofoto | Raster (CC0) | Fri | För manuell digitisering i QGIS |
| Lantmäteriet NMK50 | Raster | Varierar | Militär topografisk karta |
| FM direkt (exp-hkv@mil.se) | Okänt | Okänt | Kan nekas av säkerhetsskäl |

### ID-mappning ✅
✅ **Löst.** Använder `field_config.json` som mappar FM-fältnamn → OSM polygon-ID:n (`osm_ids`). Frontend bygger omvänd lookup (`osm_id` → FM-namn) vid laddning. Se `docs/DECISIONS.md` → "Namnmatchning via field_config.json".
